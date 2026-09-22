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


def _catalog_header(catalog_name, extra_note=None, pack="hrldas-noahmp"):
    """Rebuild a catalog file's own generated-file header (see each pack's
    write_yaml/extractor module) plus one extra note describing this validation pass.
    Delegates the pack-specific header TEXT to that pack's own extractor module
    (tools/extractors/<pack>.py) rather than hand-duplicating it here, so a change to a
    module's header format never has to be echoed in two places.

    `catalog_name` may be either the subcommand key (e.g. "global-parameters") or the
    catalog's own filename stem (e.g. "global_parameters") -- they are NOT always the
    same string (vic's subcommand names use dashes; its filenames use underscores). The
    real subcommand key is recovered from the pack module's own FILENAME map so the
    regenerated header always names the command that actually produces this file,
    never a guessed/typo'd variant -- a mismatch here previously produced a stored
    header that did not match what `extract_pack.py` itself would write."""
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from extractors import hrldas_noahmp, vic  # local import: avoids argparse side effects at module load
    mod = {"hrldas-noahmp": hrldas_noahmp, "vic": vic}[pack]
    filename = catalog_name if catalog_name.endswith(".yaml") else f"{catalog_name}.yaml"
    command_name = next((k for k, v in mod.FILENAME.items() if v == filename), catalog_name)
    if pack == "hrldas-noahmp":
        header = [
            f"Generated by tools/extract_pack.py {command_name} -- do not hand-edit.",
            f"Regenerate: python3 tools/extract_pack.py {command_name} --source-root <pinned-checkout> --out {filename}",
            f"Source commits: hrldas@{mod.HRLDAS_COMMIT}, noahmp@{mod.NOAHMP_COMMIT}.",
        ]
    else:
        header = [
            f"Generated by tools/extract_pack.py --pack vic {command_name} -- do not hand-edit.",
            f"Regenerate: python3 tools/extract_pack.py --pack vic {command_name} "
            f"--source-root <pinned-VIC-checkout> --out {filename}",
            f"Source commit: vic@{mod.VIC_COMMIT} (tag {mod.VIC_TAG}); sample data {mod.SAMPLE_DATA_COMMIT}.",
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


def apply_evidence_upgrades_confirmed(catalog, clean_names, list_key, name_fn):
    """Same as apply_evidence_upgrades, but upgrades to `evidence: confirmed_in_sample_input`
    instead of `both` -- the vic pack's own vocabulary (SCHEMA.md) for an input-format
    fact the public VIC sample data (Stehekin) confirms. Never used for `both`, since no
    VIC pack fact may claim it was observed in model OUTPUT (none exists here).

    `clean_names` is a set of (driver, NAME) tuples, and `name_fn` must return the same
    shape for an entry -- matching by name alone previously upgraded BOTH drivers'
    catalog entries for a key whenever EITHER driver's sample file happened to use it
    (independent review C7/C8: classic-only WIND_H and image-only CALENDAR each wrongly marked
    confirmed for the other driver too). A key genuinely present in both samples still
    gets both entries upgraded, since both tuples are then in `clean_names`."""
    n = 0
    for entry in catalog.get(list_key, []):
        if name_fn(entry) in clean_names and entry.get("evidence") == "source_read":
            entry["evidence"] = "confirmed_in_sample_input"
            n += 1
    return n


# --------------------------------------------------------------------------------------
# vic pack: validation against the public VIC sample inputs (Stehekin), read-only,
# input-FORMAT facts only -- no VIC model output exists anywhere reachable by this pack,
# so nothing here may upgrade a fact to `both`/`observed_in_output`; the only upgrade this
# path performs is `source_read` -> `confirmed_in_sample_input` (see SCHEMA.md's evidence
# vocabulary note). Pure stdlib for the classic (text) checks; the image (NetCDF) checks
# lazy-import netCDF4 exactly like the rest of this file does for HRLDAS.
# --------------------------------------------------------------------------------------

def _parse_global_param_file_keys(path):
    """Every first-token key actually present in a VIC global parameter file (classic or
    image), case-preserved as written, skipping comments/blank lines. A key may repeat
    (e.g. FORCE_TYPE, OUTVAR) -- returned as a list, not deduplicated, since the count of
    repeats is itself informative for a directive key."""
    keys = []
    for line in Path(path).read_text(encoding="utf-8", errors="replace").splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        keys.append(s.split()[0])
    return keys


def validate_vic_global_parameters(catalog, sample_global_path, driver, report):
    """Every key token in one real sample global parameter file: is it recognized by
    this driver's catalogued key list? (Case-insensitive, matching get_global_param.c's
    own strcasecmp.) A key in the file but not the catalog is a real gap (either a
    directive this extractor did not parse, or a driver mismatch); a key in the catalog
    but not exercised by this one sample file is expected (most keys are optional)."""
    file_keys = _parse_global_param_file_keys(sample_global_path)
    cat_keys = {k["key"].upper() for k in catalog["keys"] if k["where"]["driver"] == driver}
    file_keys_upper = {k.upper() for k in file_keys}
    matched = sorted(file_keys_upper & cat_keys)
    unmatched = sorted(file_keys_upper - cat_keys)
    report[driver] = {
        "sample_file": Path(sample_global_path).name,
        "n_distinct_keys_in_sample_file": len(file_keys_upper),
        "n_matched_in_catalog": len(matched),
        "keys_in_sample_not_in_catalog": unmatched,
    }
    return matched


def validate_vic_classic_soil_columns(catalog, sample_global_path, sample_soil_path, report):
    """Column COUNT check: the catalogued classic_soil_columns layout (with per_layer
    columns multiplied by NLAYER from the sample global file, and each column's own
    `gate` consulted only informally -- this mechanical pass checks the unconditional +
    always-present-at-this-sample's-options column count, not every option combination)
    against the actual whitespace-separated field count of the sample soil file's first
    data line."""
    nlayer = None
    for line in Path(sample_global_path).read_text(encoding="utf-8", errors="replace").splitlines():
        if line.strip().upper().startswith("NLAYER"):
            parts = line.split()
            if len(parts) > 1:
                nlayer = int(parts[1])
            break
    cols = catalog.get("classic_soil_columns", [])
    n_flat = sum(1 for c in cols if not c.get("per_layer"))
    n_per_layer_groups = sum(1 for c in cols if c.get("per_layer"))
    expected = n_flat + (n_per_layer_groups * nlayer if nlayer else 0)
    first_line = None
    for line in Path(sample_soil_path).read_text(encoding="utf-8", errors="replace").splitlines():
        if line.strip():
            first_line = line
            break
    actual = len(first_line.split()) if first_line else None
    report["classic_soil_columns"] = {
        "sample_soil_file": Path(sample_soil_path).name,
        "nlayer_from_sample_global_file": nlayer,
        "catalogued_flat_columns": n_flat,
        "catalogued_per_layer_column_groups": n_per_layer_groups,
        "expected_column_count_if_all_catalogued_columns_present": expected,
        "actual_column_count_in_sample_file_first_line": actual,
        "note": "This is an upper-bound expectation (every catalogued column present, "
                "including ones gated by an option not set in this sample's global "
                "file) confronted with the actual count; a match is not guaranteed and "
                "a mismatch is reported as a fact, not resolved by guessing which "
                "gated columns this particular sample enables.",
    }


def validate_vic_image_netcdf(catalog, params_nc_path, domain_nc_path, forcing_nc_path, report):
    """Every image_netcdf_parameters entry's `nc_variable`: present in the sample image
    parameter file? Every forcing.yaml image-driver entry's expected NetCDF variable
    name (best-effort: lower-cased enum/role name): present in the sample forcing file?
    Domain file: which of its own variables exist, listed for cross-reference (this
    pack's domain-field catalog coverage is a known_gap, not asserted complete)."""
    import netCDF4
    sub = {}
    if params_nc_path:
        with netCDF4.Dataset(params_nc_path) as ds:
            file_vars = set(ds.variables)
            cat_vars = {e["nc_variable"] for e in catalog.get("image_netcdf_parameters", [])}
            matched = sorted(cat_vars & file_vars)
            sub["image_params"] = {
                "sample_file": Path(params_nc_path).name,
                "n_catalogued": len(cat_vars),
                "n_matched_in_sample_file": len(matched),
                "catalogued_not_in_sample_file": sorted(cat_vars - file_vars),
            }
    if domain_nc_path:
        with netCDF4.Dataset(domain_nc_path) as ds:
            sub["domain_file_variables"] = {
                "sample_file": Path(domain_nc_path).name,
                "variables": sorted(ds.variables),
                "note": "Listed for reference; this pack's domain-field catalog "
                        "coverage is a known_gap (not cross-checked name-by-name).",
            }
    if forcing_nc_path:
        with netCDF4.Dataset(forcing_nc_path) as ds:
            sub["forcing_file_variables"] = {
                "sample_file": Path(forcing_nc_path).name,
                "variables": sorted(ds.variables),
            }
    report["image_netcdf"] = sub


def validate_vic_sample_inputs(pack_dir, sample_root, apply_upgrades, report_out):
    """Entry point for `--pack vic`. Confronts global_parameters.yaml, parameters.yaml
    (classic soil columns + image NetCDF parameter names) against the public VIC sample
    data (Stehekin; see version_scope). Read-only besides the optional --apply rewrite.
    Every check here is a FACT about input-format agreement, never a claim about
    scientific correctness, and never upgrades evidence beyond `confirmed_in_sample_input`
    (see SCHEMA.md)."""
    sample_root = Path(sample_root)
    classic_global = sample_root / "classic/Stehekin/parameters/global_param.STEHE.txt"
    classic_soil = sample_root / "classic/Stehekin/parameters/Stehekin_soil.txt"
    image_global = sample_root / "image/Stehekin/parameters/Stehekin_image_test.global.txt"
    image_params_nc = sample_root / "image/Stehekin/parameters/Stehekin_test_params_20160327.nc"
    image_domain_nc = sample_root / "image/Stehekin/parameters/domain.stehekin.20151028.nc"
    image_forcing_nc = sample_root / "image/Stehekin/forcings/Stehekin_image_test.forcings_10days.1949.nc"

    gp_catalog = load_catalog(pack_dir / "catalogs" / "global_parameters.yaml")
    params_catalog = load_catalog(pack_dir / "catalogs" / "parameters.yaml")

    gp_report = {}
    matched_classic = validate_vic_global_parameters(gp_catalog, classic_global, "classic", gp_report)
    matched_image = validate_vic_global_parameters(gp_catalog, image_global, "image", gp_report)
    report_out["global_parameters"] = gp_report

    soil_report = {}
    validate_vic_classic_soil_columns(params_catalog, classic_global, classic_soil, soil_report)
    report_out.update(soil_report)

    try:
        import netCDF4  # noqa: F401
        nc_available = True
    except ImportError:
        nc_available = False
    if nc_available:
        image_report = {}
        validate_vic_image_netcdf(params_catalog, image_params_nc, image_domain_nc,
                                   image_forcing_nc, image_report)
        report_out.update(image_report)
    else:
        report_out["image_netcdf"] = {"note": "netCDF4 not available in this interpreter; "
                                               "image NetCDF checks skipped -- re-run with "
                                               "a numpy+netCDF4-capable python3 (see "
                                               "tools/README.md)."}

    if apply_upgrades:
        clean_pairs = ({("classic", k.upper()) for k in matched_classic}
                        | {("image", k.upper()) for k in matched_image})
        n1 = apply_evidence_upgrades_confirmed(
            gp_catalog, clean_pairs, "keys",
            lambda e: (e["where"]["driver"], e["key"].upper()))
        _miniyaml.write_file(gp_catalog, pack_dir / "catalogs" / "global_parameters.yaml",
                              header_lines=_catalog_header("global_parameters",
                                  "Evidence upgraded in place by tools/validate_catalogs.py "
                                  "--pack vic --apply against the public VIC sample inputs "
                                  "(Stehekin); see catalogs/MANIFEST.json's validation field.",
                                  pack="vic"))
        report_out["global_parameters_evidence_upgraded"] = n1
        manifest_path = pack_dir / "catalogs" / "MANIFEST.json"
        if manifest_path.is_file():
            manifest = json.loads(manifest_path.read_text())
            manifest["validation"] = {
                "note": "confronted against the public VIC sample data (Stehekin, commit "
                        "3f2dcb4) -- input-format facts only; no model output exists "
                        "anywhere reachable by this pack, so nothing here is or can be "
                        "`observed_in_output`/`both`.",
                **{k: v for k, v in report_out.items() if not k.endswith("_upgraded")},
            }
            manifest_path.write_text(json.dumps(manifest, indent=2, default=str) + "\n")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--pack", default="hrldas-noahmp", choices=["hrldas-noahmp", "vic"],
                    help="Which pack to validate (default: hrldas-noahmp)")
    p.add_argument("--pack-dir", required=True, help="Path to the pack directory (holds catalogs/)")
    p.add_argument("--ldasout", help="A real LDASOUT_DOMAIN1 file (hrldas-noahmp only)")
    p.add_argument("--restart", help="A real RESTART_DOMAIN1 file (hrldas-noahmp only)")
    p.add_argument("--ldasin", help="A real LDASIN_DOMAIN1 file (hrldas-noahmp only)")
    p.add_argument("--sample-data-root", help="Root of the public VIC sample data (vic only), "
                                          "e.g. <VIC-checkout>/samples/data")
    p.add_argument("--check-kind-sample", action="store_true",
                    help="Also run the <=12-file empirical kind check next to --ldasout")
    p.add_argument("--apply", action="store_true",
                    help="Upgrade evidence in place for matched, non-conflicting facts "
                         "(source_read -> both for hrldas-noahmp, source_read -> "
                         "confirmed_in_sample_input for vic) and rewrite the catalog YAML "
                         "files (deterministic; see module docstring)")
    p.add_argument("--json", action="store_true")
    args = p.parse_args()

    pack_dir = Path(args.pack_dir)

    if args.pack == "vic":
        if not args.sample_data_root:
            sys.exit("ERROR: --pack vic requires --sample-data-root <VIC-checkout>/samples/data")
        report = {}
        validate_vic_sample_inputs(pack_dir, args.sample_data_root, args.apply, report)
        print(json.dumps(report, indent=2, default=str))
        return 0

    need_stack()
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
