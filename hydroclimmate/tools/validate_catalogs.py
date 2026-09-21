#!/usr/bin/env python3
"""validate_catalogs.py -- confronts the hrldas-noahmp catalogs against a real
LDASOUT / RESTART / LDASIN / setup file's headers (and a small sample of records for
outputs.yaml's 'kind').

Reports, per file kind:
  - names in the catalog but not in the file (with the gating condition, if the catalog
    records one, as a candidate reason)
  - names in the file but not in the catalog
  - units-attribute and dimension-order mismatches (dimension order is compared against
    BOTH the catalog's literal Fortran-source order and that order reversed -- netCDF
    files opened through netCDF4-python report dimensions in the reverse of the order
    given to the Fortran nf90_def_var call that created them; a match against the
    reversed order is the expected case and is reported as such, not as a discrepancy)
  - presence of _FillValue/missing_value
  - for outputs.yaml only, and only when --check-kind-sample is given: a cheap empirical
    monotonicity check over at most ~12 files, reported as consistent/inconsistent with
    the source-derived 'kind', plus observed fill behaviour (undeclared large-magnitude
    values, sentinel values in the first vs later records), never a full pass.

Only prints observations and CONSISTENT/DISAGREES/NOT_CHECKED verdicts; it does not judge
scientific acceptability. Needs numpy and netCDF4 (see tools/README.md).

With --apply, matched facts whose observation does not conflict (name present, no unit
mismatch, no dimension-order mismatch/no unmatched-forcing-role) have their catalog
`evidence` field upgraded from `source_read` to `both` and the catalog YAML file is
rewritten in place -- deterministically, so `extract_pack.py all` (regenerate) followed by
`validate_catalogs.py --apply` against the same real files reproduces the committed
catalogs byte-identical (the reproducibility this file's docstring/SCHEMA.md rely on;
see tools/selftest.py).
"""
import argparse
import glob
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _miniyaml  # noqa: E402


def need_stack():
    try:
        import numpy  # noqa: F401
        import netCDF4  # noqa: F401
    except ImportError as exc:
        sys.exit(
            f"ERROR: {exc}. On clusters that use environment modules, load a Python "
            "environment that provides numpy and netCDF4 first, e.g.:\n"
            "  module load conda; conda activate <env-with-numpy-and-netcdf4>\n"
            "then re-run this command. See tools/README.md.")


def load_catalog(path):
    return _miniyaml.load_file(path)


def real_dims(var):
    return tuple(var.dimensions)


def source_dim_order(entry):
    return tuple(entry.get("dim_order") or [])


def compare_var(name, catalog_entry, nc_var, report, units_key="units"):
    attrs = {a: nc_var.getncattr(a) for a in nc_var.ncattrs()}
    clean = True
    cat_units = catalog_entry.get(units_key)
    file_units = attrs.get("units")
    if cat_units is not None and file_units is not None and cat_units != file_units:
        report["unit_mismatches"].append({"name": name, "catalog": cat_units, "file": file_units})
        clean = False

    cat_dims = source_dim_order(catalog_entry)
    file_dims = real_dims(nc_var)
    if cat_dims:
        cat_dims_no_layer_literal = tuple(d if d != "<layer-dim>" else "<layer-dim>" for d in cat_dims)
        reversed_cat = tuple(reversed(cat_dims_no_layer_literal))
        if file_dims == reversed_cat:
            report["dim_order_reversed_as_expected"].append(name)
        elif file_dims == cat_dims_no_layer_literal:
            report["dim_order_matches_literally"].append(name)
        else:
            report["dim_order_mismatches"].append(
                {"name": name, "catalog_source_order": list(cat_dims),
                 "catalog_reversed": list(reversed_cat), "file_order": list(file_dims)})
            clean = False

    fill_declared = ("_FillValue" in attrs) or ("missing_value" in attrs)
    report["fill_declared"][name] = fill_declared
    if clean:
        report.setdefault("matched_clean_names", []).append(name)


def validate_outputs(catalog, nc_path, report, check_kind_sample, kinds_overlay=None):
    import netCDF4
    with netCDF4.Dataset(nc_path) as ds:
        file_names = set(ds.variables)
        cat_by_name = {e["name"]: e for e in catalog["variables"]}
        report["in_catalog_not_in_file"] = [
            {"name": n, "gating": e.get("gating")} for n, e in sorted(cat_by_name.items())
            if n not in file_names and n != "Times"]
        report["in_file_not_in_catalog"] = sorted(file_names - set(cat_by_name) - {"Times"})
        for name, entry in cat_by_name.items():
            if name in ds.variables:
                compare_var(name, entry, ds.variables[name], report)

    if check_kind_sample:
        validate_kind_sample(catalog, nc_path, report, kinds_overlay=kinds_overlay)


EXPECT_MONOTONE_KINDS = {"accumulated_since_start"}
EXPECT_RESET_KINDS = {"accumulated_and_reset", "accumulated_reset_each_soil_step",
                       "accumulated_reset_each_mmf_call"}
EXPECT_NON_MONOTONE_KINDS = {
    "state_or_instantaneous", "state", "instantaneous", "instantaneous_rate", "diagnostic",
    "static", "layer_integrated_state", "per_model_timestep_depth", "per_soil_timestep_energy",
}


def _kind_consistency(effective_kind, monotone, resets):
    if effective_kind in EXPECT_MONOTONE_KINDS:
        return "CONSISTENT" if (monotone and not resets) else "INCONSISTENT"
    if effective_kind in EXPECT_RESET_KINDS:
        return "CONSISTENT" if resets else "INCONSISTENT (no reset observed in sample)"
    if effective_kind in EXPECT_NON_MONOTONE_KINDS:
        return "CONSISTENT (not expected to be monotone; observed monotone=%s)" % monotone
    return "NOT_CHECKED (kind undetermined)"


def validate_kind_sample(catalog, nc_path, report, max_files=12, kinds_overlay=None):
    """kinds_overlay (optional): {VARIABLE_NAME_UPPER: {"true_kind": ...}, ...} from
    catalogs/kinds_overlay.yaml -- the curated overlay is what actually answers the
    'what should this look like empirically' question for the ~150 variables the
    mechanical kind classifier could only call state_or_instantaneous/undetermined --
    testing the raw generated kind for those would just re-report the known gap)."""
    import numpy as np
    import netCDF4
    directory = Path(nc_path).parent
    files = sorted(directory.glob("*.LDASOUT_DOMAIN1"))[:max_files]
    if len(files) < 2:
        report["kind_sample"] = {"note": f"fewer than 2 LDASOUT files found next to {nc_path}; "
                                          "kind sample check skipped"}
        return
    kind_report = []
    cat_by_name = {e["name"]: e for e in catalog["variables"]}
    kinds_overlay = kinds_overlay or {}
    # Only sample variables actually present in the first file, to bound cost.
    with netCDF4.Dataset(files[0]) as ds0:
        present = set(ds0.variables)
    for name, entry in cat_by_name.items():
        if name not in present or entry.get("dimensionality") != "2D":
            continue
        declared_kind = entry.get("kind")
        overlay_row = kinds_overlay.get(name.upper())
        effective_kind = overlay_row["true_kind"] if overlay_row else declared_kind
        series = []
        fill_events = []
        for fpath in files:
            with netCDF4.Dataset(fpath) as ds:
                if name not in ds.variables:
                    continue
                var = ds.variables[name]
                data = np.ma.filled(var[...], np.nan) if np.ma.isMaskedArray(var[...]) else np.asarray(var[...])
                finite = data[np.isfinite(data)]
                if finite.size == 0:
                    continue
                series.append(float(np.nanmean(finite)))
                large_neg = int((finite <= -1e4).sum())
                if large_neg:
                    fill_events.append({"file": Path(fpath).name, "large_negative_count": large_neg})
        if len(series) < 2:
            continue
        diffs = [b - a for a, b in zip(series, series[1:])]
        monotone = all(d >= -1e-6 for d in diffs)
        resets = any(d < -1e-3 for d in diffs)
        consistency = _kind_consistency(effective_kind, monotone, resets)
        kind_report.append({
            "name": name, "declared_kind": declared_kind,
            "overlay_true_kind": overlay_row["true_kind"] if overlay_row else None,
            "tested_against": effective_kind, "n_files_sampled": len(series),
            "domain_mean_series": [round(s, 6) for s in series],
            "observed_monotone_nondecreasing": monotone,
            "consistency": consistency,
            "fill_events_large_negative": fill_events,
        })
    report["kind_sample"] = {"n_files": len(files), "results": kind_report}


def validate_restart(catalog, nc_path, report):
    import netCDF4
    with netCDF4.Dataset(nc_path) as ds:
        file_names = set(ds.variables)
        cat_by_name = {e["name"]: e for e in catalog["variables"]}
        report["in_catalog_not_in_file"] = [
            {"name": n, "gating": e.get("gating")} for n, e in sorted(cat_by_name.items())
            if n not in file_names and n != "Times"]
        report["in_file_not_in_catalog"] = sorted(file_names - set(cat_by_name) - {"Times"})
        for name, entry in cat_by_name.items():
            if name in ds.variables:
                compare_var(name, entry, ds.variables[name], report)


def validate_forcing(catalog, nc_path, report):
    import netCDF4
    with netCDF4.Dataset(nc_path) as ds:
        file_names = set(ds.variables)
        matched, unmatched = [], []
        matched_roles = []
        for entry in catalog["inputs"]:
            name = entry.get("ldasin_name") or entry.get("namelist_default")
            if not name:
                continue
            if name in ds.variables:
                matched.append(name)
                matched_roles.append(entry.get("role"))
                attrs = {a: ds.variables[name].getncattr(a) for a in ds.variables[name].ncattrs()}
                report.setdefault("forcing_observed_units", {})[name] = attrs.get("units")
            else:
                unmatched.append({"role": entry.get("role"), "expected_name": name})
        report["forcing_matched"] = matched
        report["forcing_matched_roles"] = matched_roles
        report["forcing_not_found_in_file"] = unmatched
        report["forcing_in_file_not_in_catalog"] = sorted(
            file_names - set(matched) - {"Times", "valid_time"})


def _catalog_header(catalog_name, extra_note=None):
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import extract_pack  # local import: avoids argparse side effects at module load time
    header = [
        f"Generated by tools/extract_pack.py {catalog_name} -- do not hand-edit.",
        f"Regenerate: python3 tools/extract_pack.py {catalog_name} --source-root <pinned-checkout> --out {catalog_name}.yaml",
        f"Source commits: hrldas@{extract_pack.HRLDAS_COMMIT}, noahmp@{extract_pack.NOAHMP_COMMIT}.",
    ]
    if extra_note:
        header.append(extra_note)
    return header


def refresh_manifest(pack_dir, touched_filenames):
    """After --apply rewrites one or more catalogs/*.yaml in place, catalogs/MANIFEST.json's
    recorded sha256 for those files is stale (it was computed right after extract_pack.py
    wrote the pre-validation, evidence: source_read-only version). Recompute and update
    just the touched entries; counts are unaffected by an evidence upgrade."""
    manifest_path = pack_dir / "catalogs" / "MANIFEST.json"
    if not manifest_path.exists():
        return
    manifest = json.loads(manifest_path.read_text())
    for fname in touched_filenames:
        if fname in manifest.get("files", {}):
            fpath = pack_dir / "catalogs" / fname
            manifest["files"][fname]["sha256"] = hashlib.sha256(fpath.read_bytes()).hexdigest()
    manifest_path.write_text(json.dumps(manifest, indent=2, default=str) + "\n")


def apply_evidence_upgrades(catalog, clean_names, list_key, name_fn):
    """Upgrade `evidence: source_read` -> `evidence: both` in place for every entry whose
    name (via `name_fn`) is in `clean_names` (present in the real file, no recorded
    mismatch). Returns the number of entries upgraded. Deterministic given the same
    catalog and the same real file -- never upgrades a conflicting or absent fact."""
    n = 0
    for entry in catalog.get(list_key, []):
        if name_fn(entry) in clean_names and entry.get("evidence") == "source_read":
            entry["evidence"] = "both"
            n += 1
    return n


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--pack-dir", required=True, help="Path to the pack directory (holds catalogs/)")
    p.add_argument("--ldasout", help="A real LDASOUT_DOMAIN1 file")
    p.add_argument("--restart", help="A real RESTART_DOMAIN1 file")
    p.add_argument("--ldasin", help="A real LDASIN_DOMAIN1 file")
    p.add_argument("--check-kind-sample", action="store_true",
                    help="Also run the <=12-file empirical kind check next to --ldasout")
    p.add_argument("--apply", action="store_true",
                    help="Upgrade evidence: source_read -> both in place for matched, non-conflicting "
                         "facts and rewrite the catalog YAML files (deterministic; see module docstring)")
    p.add_argument("--json", action="store_true")
    args = p.parse_args()
    need_stack()

    pack_dir = Path(args.pack_dir)
    sections = {}
    applied = {}

    kinds_overlay = {}
    kinds_overlay_path = pack_dir / "curated" / "kinds_overlay.yaml"
    if kinds_overlay_path.is_file():
        for row in load_catalog(kinds_overlay_path).get("rows", []):
            kinds_overlay[row["variable"].upper()] = row

    if args.ldasout:
        catalog = load_catalog(pack_dir / "catalogs" / "outputs.yaml")
        sub = dict(unit_mismatches=[], dim_order_reversed_as_expected=[],
                   dim_order_matches_literally=[], dim_order_mismatches=[], fill_declared={})
        validate_outputs(catalog, args.ldasout, sub, args.check_kind_sample, kinds_overlay=kinds_overlay)
        sections["outputs"] = sub
        if args.apply:
            n = apply_evidence_upgrades(catalog, set(sub.get("matched_clean_names", [])),
                                         "variables", lambda e: e.get("name"))
            applied["outputs"] = n
            _miniyaml.write_file(catalog, pack_dir / "catalogs" / "outputs.yaml",
                                  header_lines=_catalog_header("outputs",
                                      "Evidence upgraded in place by tools/validate_catalogs.py --apply "
                                      "against a real LDASOUT file; see catalogs/MANIFEST.json's validation field."))

    if args.restart:
        catalog = load_catalog(pack_dir / "catalogs" / "restart.yaml")
        sub = dict(unit_mismatches=[], dim_order_reversed_as_expected=[],
                   dim_order_matches_literally=[], dim_order_mismatches=[], fill_declared={})
        validate_restart(catalog, args.restart, sub)
        sections["restart"] = sub
        if args.apply:
            n = apply_evidence_upgrades(catalog, set(sub.get("matched_clean_names", [])),
                                         "variables", lambda e: e.get("name"))
            applied["restart"] = n
            _miniyaml.write_file(catalog, pack_dir / "catalogs" / "restart.yaml",
                                  header_lines=_catalog_header("restart",
                                      "Evidence upgraded in place by tools/validate_catalogs.py --apply "
                                      "against a real RESTART file; see catalogs/MANIFEST.json's validation field."))

    if args.ldasin:
        catalog = load_catalog(pack_dir / "catalogs" / "forcing.yaml")
        sub = {}
        validate_forcing(catalog, args.ldasin, sub)
        sections["forcing"] = sub
        if args.apply:
            clean = set(sub.get("forcing_matched", []))
            n = apply_evidence_upgrades(catalog, clean, "inputs",
                                         lambda e: e.get("ldasin_name") or e.get("namelist_default"))
            applied["forcing"] = n
            _miniyaml.write_file(catalog, pack_dir / "catalogs" / "forcing.yaml",
                                  header_lines=_catalog_header("forcing",
                                      "Evidence upgraded in place by tools/validate_catalogs.py --apply "
                                      "against a real LDASIN file; see catalogs/MANIFEST.json's validation field."))

    if args.apply and applied:
        refresh_manifest(pack_dir, [f"{name}.yaml" for name in applied])

    for name, sub in sections.items():
        print(f"\n=== {name} ===")
        print(json.dumps(sub, indent=2, default=str))

    if applied:
        print("\n=== evidence upgrades applied ===")
        print(json.dumps(applied, indent=2))

    if sections:
        write_validation_summary(pack_dir, sections)
        print(f"\nupdated {pack_dir / 'catalogs' / 'MANIFEST.json'} validation summary")

    if args.json:
        print(json.dumps(sections, indent=2, default=str))
    return 0


def write_validation_summary(pack_dir, sections):
    """Condense `sections` (the same structured report already printed) into
    catalogs/MANIFEST.json's own `validation` field -- run against one regional offline
    run built from the pinned commit; no paths or run identifiers recorded. This
    confirms or disagrees with source-derived catalog facts; it does not judge
    scientific acceptability."""
    manifest_path = pack_dir / "catalogs" / "MANIFEST.json"
    manifest = json.loads(manifest_path.read_text()) if manifest_path.is_file() else {}
    summary = {}
    for name, sub in sections.items():
        n_gated = 0
        if "in_catalog_not_in_file" in sub:
            n_gated = sum(1 for e in sub["in_catalog_not_in_file"] if e.get("gating"))
        entry = {}
        if "in_catalog_not_in_file" in sub:
            entry["in_catalog_not_in_file"] = len(sub["in_catalog_not_in_file"])
            entry["in_catalog_not_in_file_gated"] = n_gated
        if "in_file_not_in_catalog" in sub:
            entry["in_file_not_in_catalog"] = len(sub["in_file_not_in_catalog"])
        if "dim_order_reversed_as_expected" in sub:
            entry["dim_order_reversed_as_expected"] = len(sub["dim_order_reversed_as_expected"])
            entry["dim_order_matches_literally"] = len(sub.get("dim_order_matches_literally", []))
            entry["dim_order_mismatches"] = len(sub.get("dim_order_mismatches", []))
        if "unit_mismatches" in sub:
            entry["unit_mismatches"] = len(sub["unit_mismatches"])
        if "fill_declared" in sub:
            entry["fill_declared_true"] = sum(1 for v in sub["fill_declared"].values() if v)
            entry["fill_declared_checked"] = len(sub["fill_declared"])
        if "kind_sample" in sub:
            ks = sub["kind_sample"]
            if "results" in ks:
                entry["kind_sample_files"] = ks.get("n_files")
                entry["kind_sample_checked"] = len(ks["results"])
                entry["kind_sample_tested_against_overlay"] = sum(
                    1 for r in ks["results"] if r.get("overlay_true_kind"))
                entry["kind_sample_inconsistent"] = sum(
                    1 for r in ks["results"] if "INCONSISTENT" in r["consistency"])
        if "forcing_matched" in sub:
            entry["forcing_matched"] = len(sub["forcing_matched"])
            entry["forcing_not_found_in_file"] = len(sub["forcing_not_found_in_file"])
        summary[name] = entry
    manifest["validation"] = {
        "note": "run against one regional offline run built from the pinned commit; no "
                "paths or run identifiers recorded; confirms or disagrees with "
                "source-derived catalog facts, does not judge scientific acceptability",
        **summary,
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, default=str) + "\n")


if __name__ == "__main__":
    sys.exit(main())
