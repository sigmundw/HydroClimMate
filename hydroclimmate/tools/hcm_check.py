#!/usr/bin/env python3
"""hcm_check.py — deterministic, evidence-first checks on NetCDF model output.

Two checks, chosen for two observed failure modes: a paired run where a
declared response did not actually scale with its controlling variable, and
an accumulator variable whose reset or undeclared fill values were missed.

Both checks print observations (numbers, locations) before any verdict, and
both print a verdict of VERIFIED / VIOLATED / UNVERIFIED against expectations
you declare. With no expectations, the verdict is UNVERIFIED and the
observations are still printed in full — a missing or wrong threshold never
hides the evidence.

This tool does not decide whether a result is scientifically acceptable;
acceptance criteria and their owner belong in the project's experiment
record (see templates/EXPERIMENT.md). It does not establish causality, only
association and exact-match/monotonicity properties on the arrays given.

Requires numpy and netCDF4, imported lazily (only when a subcommand needs
them) so --help works with no environment at all. See tools/README.md for
the environment note.
"""
import argparse
import glob
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
MODELS_DIR = HERE.parent / "references/models"
sys.path.insert(0, str(HERE))
import _miniyaml  # noqa: E402

VALID_BASIS = ("source_read", "observed_in_output", "both", "unverified")


def _load_structured(path):
    """Load a pack layer file: YAML (PyYAML, else _miniyaml) for .yaml, plain json for
    .json (only catalogs/index.json and catalogs/MANIFEST.json stay JSON; see
    SCHEMA.md)."""
    if path.suffix == ".yaml":
        return _miniyaml.load_file(path)
    return json.loads(path.read_text())


# Curated (hand-authored) layers live under curated/, at these fixed filenames; the one
# generated, machine-only lookup index lives at catalogs/index.json. Only a depth:
# reference pack carries any of these -- a depth: outline pack is prose only. See
# references/models/SCHEMA.md.
_CURATED_LAYERS = ("interface", "switches", "checks", "workflows")


def load_pack(name):
    """Load a pack's manifest and, for a depth: reference pack, its optional curated
    layers and generated index -- resolved relative to this tool's own location (not the
    current working directory). A depth: outline pack, or a missing layer file, simply
    comes back with that layer as None -- this tool never invents a declaration. See
    references/models/SCHEMA.md."""
    pack_dir = MODELS_DIR / name
    if not pack_dir.is_dir():
        sys.exit(f"ERROR: no such pack directory: {pack_dir}")
    manifest_path = pack_dir / "pack.yaml"
    manifest = {}
    if manifest_path.is_file():
        manifest = _load_structured(manifest_path)
    depth = manifest.get("depth", "outline")
    layers = {name: None for name in _CURATED_LAYERS}
    layers["index"] = None
    if depth == "reference":
        for layer_name in _CURATED_LAYERS:
            path = pack_dir / "curated" / f"{layer_name}.yaml"
            if path.is_file():
                layers[layer_name] = _load_structured(path)
        index_path = pack_dir / "catalogs" / "index.json"
        if index_path.is_file():
            layers["index"] = _load_structured(index_path)
    return {"dir": pack_dir, "manifest": manifest, "layers": layers, "depth": depth}


def _is_outline(pack):
    return pack["depth"] != "reference"


OUTLINE_NOTE = "outline pack: no machine-readable declarations"


def _fact_is_unverified(fact):
    return isinstance(fact, dict) and fact.get("basis") == "unverified"


def _scope_of(fact):
    if not isinstance(fact, dict):
        return "unspecified in the pack"
    return fact.get("scope", "unspecified in the pack")


# Generic words that appear in many descriptive pack names but say nothing distinctive
# about identity; excluding them cuts obviously-wrong keyword matches (e.g. "field(s)").
_KEYWORD_STOPWORDS = {"field", "fields", "data", "state", "value", "values", "name",
                       "exact", "given", "pack", "not", "the", "and", "for"}


def _keyword_match(text, var_name):
    keywords = [w for w in re.findall(r"[a-zA-Z]+", var_name.lower())
                if len(w) >= 3 and w not in _KEYWORD_STOPWORDS]
    return bool(keywords) and any(kw in text.lower() for kw in keywords)


def find_output_facts(pack, var_name):
    """Facts in the pack's curated/interface.yaml 'outputs' section whose 'variable' text
    plausibly concerns var_name. The pack often names a variable descriptively rather
    than by its exact NetCDF name (the pack's own prose does not give one) -- this is a
    keyword match, not proof of identity, and is reported as such."""
    doc = pack["layers"]["interface"]
    if not doc:
        return []
    return [f for f in doc.get("outputs", []) if _keyword_match(f.get("variable", ""), var_name)]


def find_input_facts(pack, var_name):
    """Same keyword match as find_output_facts, over curated/interface.yaml's 'inputs' section."""
    doc = pack["layers"]["interface"]
    if not doc:
        return []
    return [f for f in doc.get("inputs", []) if _keyword_match(f.get("variable", ""), var_name)]


def _need_scientific_stack():
    try:
        import numpy as np
    except ImportError:
        sys.exit(
            "ERROR: numpy is required for this command but is not importable.\n"
            "On clusters that use environment modules, load a Python environment "
            "that provides numpy and netCDF4 first, e.g.:\n"
            "  module load conda; conda activate <env-with-numpy-and-netcdf4>\n"
            "then re-run this command."
        )
    try:
        import netCDF4  # noqa: F401
    except ImportError:
        sys.exit(
            "ERROR: netCDF4 is required for this command but is not importable.\n"
            "On clusters that use environment modules, load a Python environment "
            "that provides numpy and netCDF4 first, e.g.:\n"
            "  module load conda; conda activate <env-with-numpy-and-netcdf4>\n"
            "then re-run this command."
        )
    return np


def resolve_files(pattern):
    files = sorted(glob.glob(pattern))
    if not files:
        # A literal path with no glob characters that simply doesn't exist.
        import os
        if os.path.exists(pattern):
            files = [pattern]
    if not files:
        sys.exit(f"ERROR: no files matched '{pattern}'")
    return files


def load_concat(np, files, varname, record=None):
    import netCDF4
    arrays = []
    attrs = None
    for path in files:
        with netCDF4.Dataset(path) as ds:
            if varname not in ds.variables:
                sys.exit(f"ERROR: variable '{varname}' not found in {path}")
            var = ds.variables[varname]
            data = np.ma.filled(var[...], np.nan) if np.ma.isMaskedArray(var[...]) else np.asarray(var[...])
            if attrs is None:
                attrs = {name: var.getncattr(name) for name in var.ncattrs()}
            if record is not None and record != "all":
                idx = int(record)
                data = data[idx]
            arrays.append(data)
    if len(arrays) == 1:
        combined = arrays[0]
    else:
        combined = np.stack(arrays, axis=0) if arrays[0].ndim == arrays[-1].ndim and \
            all(a.shape == arrays[0].shape for a in arrays) else np.concatenate(
            [a if a.ndim > 0 else a.reshape(1) for a in arrays], axis=0)
    return combined, attrs


def load_single(np, path, varname):
    import netCDF4
    with netCDF4.Dataset(path) as ds:
        if varname not in ds.variables:
            sys.exit(f"ERROR: variable '{varname}' not found in {path}")
        var = ds.variables[varname]
        data = var[...]
        data = np.ma.filled(data, np.nan) if np.ma.isMaskedArray(data) else np.asarray(data)
        return data


def rankdata(np, a):
    """Average ranks, ties split evenly. No scipy dependency."""
    a = np.asarray(a, dtype=float)
    order = np.argsort(a, kind="mergesort")
    ranks = np.empty(len(a), dtype=float)
    sorted_a = a[order]
    i = 0
    n = len(a)
    while i < n:
        j = i
        while j + 1 < n and sorted_a[j + 1] == sorted_a[i]:
            j += 1
        avg_rank = (i + j) / 2.0 + 1.0
        ranks[order[i:j + 1]] = avg_rank
        i = j + 1
    return ranks


def spearman(np, x, y):
    if len(x) < 2:
        return None
    rx = rankdata(np, x)
    ry = rankdata(np, y)
    rx = rx - rx.mean()
    ry = ry - ry.mean()
    denom = float(np.sqrt((rx ** 2).sum() * (ry ** 2).sum()))
    if denom == 0:
        return 0.0
    return float((rx * ry).sum() / denom)


def parse_thresholds(path):
    """Read expectations as key: value pairs, from a JSON file or from any
    plain-text/Markdown file (e.g. the project's experiment record) that
    contains lines shaped 'key: value' or 'key = value'. Unrecognized keys
    are ignored. Booleans are parsed from true/false/yes/no (case-insensitive);
    anything else is parsed as a float when possible, else kept as a string.
    """
    if path is None:
        return {}
    text = open(path, "r", encoding="utf-8", errors="replace").read()
    if path.endswith(".json"):
        return json.loads(text)
    values = {}
    for line in text.splitlines():
        m = re.match(r"\s*([A-Za-z_][A-Za-z0-9_]*)\s*[:=]\s*(.+?)\s*$", line)
        if not m:
            continue
        key, raw = m.group(1), m.group(2)
        low = raw.strip().lower()
        if low in ("true", "yes"):
            values[key] = True
        elif low in ("false", "no"):
            values[key] = False
        else:
            try:
                values[key] = float(raw)
            except ValueError:
                values[key] = raw
    return values


def verdict_line(name, expected_key, thresholds, actual_ok, detail):
    if expected_key not in thresholds:
        return f"VERDICT {name}: UNVERIFIED — no expectation for '{expected_key}' was supplied ({detail})"
    return f"VERDICT {name}: {'VERIFIED' if actual_ok else 'VIOLATED'} — {detail}"


def cmd_paired_response(args):
    np = _need_scientific_stack()
    a_files = resolve_files(args.a)
    b_files = resolve_files(args.b)
    a, _ = load_concat(np, a_files, args.var, args.record)
    b, _ = load_concat(np, b_files, args.var, args.record)
    if a.shape != b.shape:
        sys.exit(f"ERROR: shape mismatch between A {a.shape} and B {b.shape} for '{args.var}'")

    diff = b.astype(float) - a.astype(float)
    finite = np.isfinite(diff)
    nonzero = finite & (diff != 0)

    thresholds = parse_thresholds(args.thresholds)
    out = {"variable": args.var, "shape": list(a.shape)}

    print(f"# paired-response: {args.var}  A={a_files}  B={b_files}")
    print(f"Total cells: {diff.size}  finite: {int(finite.sum())}  non-finite: {int((~finite).sum())}")
    print(f"Non-zero difference: {int(nonzero.sum())} of {int(finite.sum())} finite cells "
          f"({0 if finite.sum() == 0 else 100 * nonzero.sum() / finite.sum():.2f}%)")
    out["nonzero_count"] = int(nonzero.sum())
    out["finite_count"] = int(finite.sum())

    if nonzero.any():
        vals = diff[nonzero]
        stats = dict(min=float(vals.min()), max=float(vals.max()),
                     mean=float(vals.mean()), std=float(vals.std()))
        print(f"Difference stats over non-zero cells: min={stats['min']:.6g} max={stats['max']:.6g} "
              f"mean={stats['mean']:.6g} std={stats['std']:.6g}")
        out["diff_stats_nonzero"] = stats
    else:
        print("Difference stats over non-zero cells: none (A and B are identical everywhere finite)")
        out["diff_stats_nonzero"] = None

    # Mask classes
    mask_report = None
    if args.mask_file:
        mask = load_single(np, args.mask_file, args.mask_var)
        if mask.shape != diff.shape:
            print(f"NOTE: mask shape {mask.shape} does not match data shape {diff.shape}; "
                  "attempting broadcast, results may be unreliable")
        mask_report = {}
        classes = [args.mask_value] if args.mask_value is not None else sorted(set(np.unique(mask).tolist()))[:20]
        for cls in classes:
            try:
                cls_val = float(cls)
            except (TypeError, ValueError):
                cls_val = cls
            sel = (mask == cls_val)
            sel = sel & finite if sel.shape == finite.shape else sel
            n_sel = int(sel.sum()) if hasattr(sel, "sum") else 0
            n_nonzero_sel = int((sel & nonzero).sum()) if sel.shape == nonzero.shape else 0
            print(f"Mask class {cls_val!r}: {n_sel} cells, {n_nonzero_sel} with non-zero difference")
            mask_report[str(cls_val)] = {"cells": n_sel, "nonzero": n_nonzero_sel}
    out["mask_classes"] = mask_report

    # Invariants
    invariant_report = {}
    if args.invariants:
        for name in [s.strip() for s in args.invariants.split(",") if s.strip()]:
            ia = load_concat(np, a_files, name, args.record)[0]
            ib = load_concat(np, b_files, name, args.record)[0]
            identical = bool(ia.shape == ib.shape and np.array_equal(ia, ib, equal_nan=True))
            print(f"Invariant '{name}': {'bit-identical' if identical else 'DIFFERS between A and B'}")
            invariant_report[name] = identical
    out["invariants"] = invariant_report

    # Pack-declared switch effects: annotate, never silently apply.
    pack_report = None
    if args.pack:
        pack = load_pack(args.pack)
        pack_report = {"pack": args.pack, "switch": args.switch}
        if _is_outline(pack):
            print(f"\nNOTE: pack '{args.pack}': {OUTLINE_NOTE} to confront.")
        elif args.switch:
            switches_doc = pack["layers"]["switches"]
            switch_info = None
            if switches_doc:
                for sw in switches_doc.get("switches", []):
                    if sw.get("name", "").lower() == args.switch.lower():
                        switch_info = sw
                        break
            print(f"\n# Pack-declared switch effects: pack={args.pack} switch={args.switch}")
            if switch_info is None:
                print(f"NOTE: pack '{args.pack}' declares no effects for switch '{args.switch}'; "
                      "nothing to annotate.")
            else:
                exchanged = switch_info.get("exchanged_fields", {})
                untouched = switch_info.get("untouched_fields", {})
                exchanged_fields = [f.lower() for f in exchanged.get("fields", [])]
                # Untouched fields are sometimes named descriptively (e.g. "snow state")
                # rather than as exact NetCDF names; match on shared keywords, same
                # approach as find_output_facts, and say so rather than claiming identity.
                untouched_keywords = [w for f in untouched.get("fields", [])
                                       for w in re.findall(r"[a-zA-Z]+", f.lower()) if len(w) >= 3]
                compared = [args.var] + ([s.strip() for s in args.invariants.split(",") if s.strip()]
                                          if args.invariants else [])
                for name in compared:
                    low = name.lower()
                    if low in exchanged_fields:
                        print(f"  '{name}': in the routine's exchanged list "
                              f"(scope: {_scope_of(exchanged)}).")
                    elif untouched_keywords and any(kw in low for kw in untouched_keywords):
                        print(f"  '{name}': keyword-matches a field the pack declares UNTOUCHED by this "
                              f"routine (scope: {_scope_of(untouched)}); this is a name match, not proof of identity.")
                        if name == args.var and nonzero.any():
                            print(f"    -> a non-zero difference in '{name}' is NOT ATTRIBUTABLE to the "
                                  f"switched routine according to the pack (scope: {_scope_of(untouched)}).")
                    else:
                        print(f"  '{name}': not mentioned by this switch's declared effects in the pack.")
                scaling = switch_info.get("expected_scaling_variable")
                if scaling:
                    hint = scaling.get("variable")
                    note = " [basis: unverified — the pack states this expectation but has not confirmed it]" \
                        if _fact_is_unverified(scaling) else ""
                    print(f"  Expected scaling variable per pack: {hint}{note} "
                          f"(scope: {_scope_of(scaling)}).")
                    if not args.control_var:
                        print(f"  Hint only, not applied: rerun with --control-var {hint} "
                              "to test this expectation; it is never assumed automatically.")
        else:
            print(f"\nNOTE: --pack given without --switch; no switch effects to annotate.")

    # Control-variable relationship
    control_report = None
    if args.control_file:
        control = load_single(np, args.control_file, args.control_var)
        if control.shape != diff.shape:
            # Try broadcasting a lower-rank control field (e.g. static 2-D) across
            # a leading time/record axis.
            try:
                control_b = np.broadcast_to(control, diff.shape)
            except ValueError:
                sys.exit(f"ERROR: control field shape {control.shape} cannot be broadcast to "
                         f"data shape {diff.shape}")
        else:
            control_b = control
        sel = finite
        cvals = control_b[sel].astype(float)
        dvals = diff[sel]
        n_bins = min(5, max(1, len(np.unique(cvals))))
        if n_bins > 1 and len(cvals) > 0:
            edges = np.quantile(cvals, np.linspace(0, 1, n_bins + 1))
            edges[-1] = edges[-1] + 1e-12
            bin_idx = np.clip(np.digitize(cvals, edges[1:-1]), 0, n_bins - 1)
            print(f"Binned mean difference across {n_bins} quantiles of '{args.control_var}':")
            bin_means = []
            for b_i in range(n_bins):
                sel_bin = bin_idx == b_i
                if sel_bin.any():
                    m = float(dvals[sel_bin].mean())
                    lo, hi = edges[b_i], edges[b_i + 1]
                    print(f"  bin {b_i}: control in [{lo:.6g}, {hi:.6g}) -> mean diff {m:.6g} "
                          f"(n={int(sel_bin.sum())})")
                    bin_means.append(m)
                else:
                    bin_means.append(None)
            rho = spearman(np, cvals, dvals)
            print(f"Spearman rank correlation(control, difference): "
                  f"{'n/a' if rho is None else f'{rho:.4f}'}")
            control_report = {"bin_means": bin_means, "spearman": rho}
        else:
            print("Control field has too little variation to bin.")
            control_report = {"bin_means": None, "spearman": None}
    out["control"] = control_report

    print()
    verdicts = []
    if invariant_report:
        all_identical = all(invariant_report.values())
        verdicts.append(verdict_line(
            "invariants_identical", "invariants_identical", thresholds, all_identical,
            f"declared invariants identical={all_identical}"))
    if control_report and control_report.get("spearman") is not None:
        rho = control_report["spearman"]
        min_expected = thresholds.get("spearman_min")
        ok = min_expected is not None and abs(rho) >= float(min_expected)
        verdicts.append(verdict_line(
            "scales_with_control", "spearman_min", thresholds, ok,
            f"|spearman|={abs(rho):.4f}" + (f" vs required >= {min_expected}" if min_expected is not None else "")))
    if "nonzero_expected" in thresholds:
        expected = bool(thresholds["nonzero_expected"])
        actual = bool(nonzero.any())
        verdicts.append(verdict_line(
            "nonzero_expected", "nonzero_expected", thresholds, actual == expected,
            f"expected non-zero difference={expected}, observed={actual}"))
    if not verdicts:
        verdicts.append("VERDICT: UNVERIFIED — no expectations supplied "
                         "(pass --thresholds with spearman_min / invariants_identical / nonzero_expected)")
    for v in verdicts:
        print(v)

    if args.json:
        out["verdicts"] = verdicts
        print(json.dumps(out, indent=2, default=str))
    return 0


def declared_vs_observed(pack_name, var_name, monotone, fill_declared, n_large_neg):
    """Print and return the declared-vs-observed block for accumulation-and-fill: what the
    pack's curated/interface.yaml says about this variable (keyword-matched, see
    find_output_facts), set against what was actually observed in the files. Returns
    (verdict, detail) where verdict is DISAGREES / CONSISTENT / NO DECLARATION /
    UNVERIFIED. A fact with basis: unverified can never produce a positive (CONSISTENT)
    reading -- it is downgraded to UNVERIFIED, with the reason printed."""
    pack = load_pack(pack_name)
    print(f"\n# Declared vs observed (pack: {pack_name}, variable: {var_name})")
    if _is_outline(pack):
        print(f"  NO DECLARATION: {OUTLINE_NOTE}.")
        return "NO DECLARATION", {"matched_facts": 0}
    facts = find_output_facts(pack, var_name)
    if not facts:
        print("  NO DECLARATION: curated/interface.yaml states nothing that keyword-matches "
              "this variable name.")
        return "NO DECLARATION", {"matched_facts": 0}

    disagreements = []
    unverified_facts = []
    detail = {"matched_facts": len(facts), "aspects": []}
    for fact in facts:
        aspect = fact.get("aspect")
        detail["aspects"].append(aspect)
        if _fact_is_unverified(fact):
            unverified_facts.append(fact)
        if aspect == "kind":
            declared_kind = fact.get("value")
            print(f"  declared kind: {declared_kind!r}  (scope: {_scope_of(fact)}) "
                  f"vs observed monotone={monotone}")
            if declared_kind == "accumulated_since_start" and not monotone:
                disagreements.append(("kind", fact))
        elif aspect == "fill":
            declared_attr = fact.get("attribute_declared")
            declared_raw = fact.get("known_raw_value_order")
            print(f"  declared fill: attribute_declared={declared_attr!r} "
                  f"known_raw_value_order={declared_raw!r}  (scope: {_scope_of(fact)}) "
                  f"vs observed: attribute_declared={fill_declared}, "
                  f"large_negative_count={n_large_neg}")
            if declared_attr is not None and bool(declared_attr) != bool(fill_declared):
                disagreements.append(("fill_attribute", fact))
        else:
            print(f"  declared ({aspect}): {fact.get('statement')}  (scope: {_scope_of(fact)}) "
                  "-- informational; no automated comparison for this aspect")

    if unverified_facts:
        verdict = "UNVERIFIED"
        print(f"  VERDICT: UNVERIFIED -- a matched declaration has basis: unverified, so it "
              "cannot be used to confirm CONSISTENT even though no disagreement was found.")
    elif disagreements:
        verdict = "DISAGREES"
        print(f"  VERDICT: DISAGREES -- {len(disagreements)} matched declaration(s) conflict "
              "with what was observed.")
    else:
        verdict = "CONSISTENT"
        print("  VERDICT: CONSISTENT -- matched declarations do not conflict with what was observed.")
    detail["verdict"] = verdict
    return verdict, detail


def cmd_pack_info(args):
    pack = load_pack(args.pack)
    manifest = pack["manifest"]
    print(f"# pack-info: {args.pack}")
    if not manifest:
        print("  No pack.yaml found for this pack.")
        return 0
    print(f"  title: {manifest.get('title', '<none>')}")
    print(f"  depth: {manifest.get('depth', '<none>')}")
    print(f"  version_scope: {manifest.get('version_scope', '<none>')}")
    for entry in manifest.get("prose", []):
        print(f"  prose: {entry.get('file')} -- {entry.get('purpose')}")
    if _is_outline(pack):
        print(f"  {OUTLINE_NOTE}.")
        if args.json:
            print(json.dumps({"pack": args.pack, "depth": pack["depth"],
                               "version_scope": manifest.get("version_scope")}, indent=2))
        return 0

    counts = {b: 0 for b in VALID_BASIS}
    counts_by_evidence = {}
    curated_lines = []
    for entry in manifest.get("curated", []):
        filename = entry.get("file")
        path = pack["dir"] / filename if filename else None
        doc = _load_structured(path) if path and path.is_file() else None
        n_facts = 0
        if doc:
            for _, fact in _iter_facts_local(doc):
                n_facts += 1
                if fact.get("basis") in counts:
                    counts[fact["basis"]] += 1
            # A curated layer that uses the generated-catalog citation shape
            # (where/evidence/scope -- e.g. vic's options_overlay.yaml) instead of the
            # source/basis/from shape carries no `basis` field at all, so the walk
            # above finds it but the by-basis tally above never sees it; counted here
            # separately by `evidence` instead, so this pack does not report facts=0
            # just because its curated layer uses the other of the two shapes every
            # depth: reference pack's layers can legally use (SCHEMA.md).
            for _, fact in _iter_facts_local_evidence_shape(doc):
                n_facts += 1
                counts_by_evidence[fact.get("evidence")] = counts_by_evidence.get(fact.get("evidence"), 0) + 1
        curated_lines.append((filename, entry.get("purpose"), n_facts))
        print(f"  curated: {filename} -- {entry.get('purpose')} (facts={n_facts})")
    for gap in manifest.get("known_gaps", []):
        print(f"  known gap: {gap}")
    # Print the by-basis tally only when this pack actually has a basis-shaped curated
    # layer. A pack whose layers use the other shape SCHEMA.md allows carries no `basis`
    # field anywhere, and printing an all-zero tally above the real counts told a reader
    # of the pack's own validation command that nothing had been verified.
    if any(counts.values()):
        print(f"  fact counts by basis: {counts}")
    else:
        print("  fact counts by basis: n/a (this pack's curated layer is "
              "where/evidence/scope-shaped -- see the evidence counts below)")
    if counts_by_evidence:
        print(f"  fact counts by evidence (where/evidence/scope-shaped curated layers): {counts_by_evidence}")
    if args.json:
        print(json.dumps({
            "pack": args.pack, "depth": pack["depth"], "version_scope": manifest.get("version_scope"),
            "curated": [{"file": f, "purpose": p, "facts": k} for f, p, k in curated_lines],
            "known_gaps": manifest.get("known_gaps", []),
            "counts_by_basis": counts if any(counts.values()) else None,
            "counts_by_evidence": counts_by_evidence or None,
        }, indent=2))
    return 0


def _iter_facts_local(node, path=""):
    """Same walk as evals/check_knowledge.py's _iter_facts, duplicated here so this tool
    has no import dependency on the eval script. Matches the source/scope/basis/from
    curated-layer shape (interface.yaml/switches.yaml/checks.yaml/workflows.yaml)."""
    if isinstance(node, dict):
        if {"source", "scope", "basis", "from"} <= node.keys():
            yield path, node
        for key, value in node.items():
            yield from _iter_facts_local(value, f"{path}.{key}" if path else key)
    elif isinstance(node, list):
        for i, item in enumerate(node):
            yield from _iter_facts_local(item, f"{path}[{i}]")


def _iter_facts_local_evidence_shape(node, path=""):
    """Same walk, for the OTHER curated-layer shape SCHEMA.md allows: where/evidence/
    scope (kinds_overlay.yaml/options_overlay.yaml for any pack, e.g. vic's
    curated/options_overlay.yaml, which carries no source/basis/from fields at all and
    so is invisible to _iter_facts_local alone)."""
    if isinstance(node, dict):
        if {"where", "evidence", "scope"} <= node.keys():
            yield path, node
        for key, value in node.items():
            yield from _iter_facts_local_evidence_shape(value, f"{path}.{key}" if path else key)
    elif isinstance(node, list):
        for i, item in enumerate(node):
            yield from _iter_facts_local_evidence_shape(item, f"{path}[{i}]")


def cmd_pitfall_scan(args):
    pack = load_pack(args.pack)
    print(f"# pitfall-scan: {args.pack}")
    if _is_outline(pack):
        print(f"  {OUTLINE_NOTE}.")
        return 0
    checks_doc = pack["layers"]["checks"]
    if not checks_doc:
        print("  No checks layer (curated/checks.yaml) found for this pack.")
        return 0

    results = []
    for entry in checks_doc.get("checks", []):
        pid = entry["id"]
        detect = entry.get("detect")
        if detect is None:
            print(f"\n## {pid}\n  NOT RUN: no automatable detection declared for this pitfall.")
            results.append({"id": pid, "status": "NOT RUN", "reason": "no detect stanza"})
            continue
        check = detect.get("check")
        print(f"\n## {pid}\n  detect.check: {check}")
        if not args.files:
            print("  NOT RUN: inputs missing (no --files given).")
            results.append({"id": pid, "status": "NOT RUN", "reason": "no --files given"})
            continue
        if check == "accumulation-and-fill":
            if not args.var:
                print("  NOT RUN: inputs missing (--var required).")
                results.append({"id": pid, "status": "NOT RUN", "reason": "no --var given"})
                continue
            try:
                np = _need_scientific_stack()
                all_files = sorted({f for pattern in args.files for f in resolve_files(pattern)})
                data, attrs = load_concat(np, all_files, args.var, record="all")
                large_neg = np.isfinite(data) & (data <= -1e4)
                fired = bool(large_neg.any()) and not (("_FillValue" in attrs) or ("missing_value" in attrs))
            except SystemExit as exc:
                print(f"  NOT RUN: {exc}")
                results.append({"id": pid, "status": "NOT RUN", "reason": str(exc)})
                continue
            status = "FIRED" if fired else "QUIET"
            print(f"  observation: undeclared large-negative present={fired}")
            print(f"  {status}")
            results.append({"id": pid, "status": status})
        elif check == "paired-response":
            print("  NOT RUN: paired-response needs --a/--b (two runs); pitfall-scan takes "
                  "a single --files set, so run hcm_check.py paired-response directly with "
                  f"--pack {args.pack} --switch <name> for this pitfall.")
            results.append({"id": pid, "status": "NOT RUN", "reason": "needs paired --a/--b, not --files"})
        else:
            print(f"  NOT RUN: unrecognized check '{check}'.")
            results.append({"id": pid, "status": "NOT RUN", "reason": f"unrecognized check '{check}'"})

    print()
    for r in results:
        print(f"{r['status']}: {r['id']}" + (f" ({r['reason']})" if r.get("reason") else ""))
    if args.json:
        print(json.dumps({"pack": args.pack, "results": results}, indent=2))
    return 0


def cmd_describe(args):
    """List every variable in a file with what was observed (dims, units/attrs, fill
    declared, monotone if it has a leading time-like axis), next to whatever the pack
    declares about it (keyword-matched, inputs and outputs both checked). Most variables
    will read NO DECLARATION -- that is the honest result for a pack whose prose does not
    name exact NetCDF variables."""
    np = _need_scientific_stack()
    import netCDF4
    pack = load_pack(args.pack)
    print(f"# describe: pack={args.pack} file={args.file}")
    if _is_outline(pack):
        print(f"  NOTE: {OUTLINE_NOTE}; every variable below reads NO DECLARATION.")
    with netCDF4.Dataset(args.file) as ds:
        for name, var in sorted(ds.variables.items()):
            attrs = {a: var.getncattr(a) for a in var.ncattrs()}
            fill_declared = ("_FillValue" in attrs) or ("missing_value" in attrs)
            print(f"\n## {name}")
            print(f"  observed: dims={var.dimensions} shape={var.shape} "
                  f"units={attrs.get('units', '<none>')!r} fill_declared={fill_declared}")
            data = np.ma.filled(var[...], np.nan) if np.ma.isMaskedArray(var[...]) else np.asarray(var[...])
            if data.ndim >= 1 and data.shape[0] > 1:
                step_diff = np.diff(data.astype(float), axis=0)
                finite = np.isfinite(step_diff)
                monotone = bool(not (finite & (step_diff < 0)).any())
                print(f"  observed: monotone non-decreasing along axis 0={monotone}")
            facts = find_output_facts(pack, name) + find_input_facts(pack, name)
            if not facts:
                print("  declared: NO DECLARATION -- the pack's interface layer states nothing "
                      "that keyword-matches this variable name.")
            else:
                for fact in facts:
                    note = " [basis: unverified]" if _fact_is_unverified(fact) else ""
                    print(f"  declared ({fact.get('aspect', '?')}): {fact.get('statement')}{note} "
                          f"(scope: {_scope_of(fact)})")
    return 0


def cmd_lookup(args):
    """Print an index.json entry (see tools/build_index.py) for a variable name,
    configuration key or file kind -- exact match first, then a keyword match."""
    pack = load_pack(args.pack)
    if _is_outline(pack):
        print(f"{OUTLINE_NOTE}.")
        return 0
    index_doc = pack["layers"]["index"]
    if not index_doc:
        print(f"No catalogs/index.json for pack '{args.pack}'. Build one with "
              f"tools/build_index.py {args.pack} --write.")
        return 0
    entries = index_doc.get("entries", [])
    exact = [e for e in entries if e["name"].lower() == args.name.lower()]
    matches = exact or [e for e in entries if _keyword_match(e["name"], args.name)]
    if not matches:
        print(f"No index entry for '{args.name}' in pack '{args.pack}'.")
        return 0
    for e in matches:
        print(f"# {e['name']}  (kind: {e['kind']})")
        print(f"  declared_in: {e['declared_in']}")
        print(f"  from: {e['from']}")
        print(f"  related_switches: {e['related_switches']}")
        print(f"  related_checks: {e['related_checks']}")
    if args.json:
        print(json.dumps(matches, indent=2))
    return 0


def cmd_accumulation_and_fill(args):
    np = _need_scientific_stack()
    files = resolve_files(args.files)
    data, attrs = load_concat(np, files, args.var, record="all")
    if data.ndim < 1:
        sys.exit("ERROR: variable has no leading (time/record) axis to check accumulation over")

    thresholds = parse_thresholds(args.thresholds)
    out = {"variable": args.var, "shape": list(data.shape), "attrs": attrs}

    print(f"# accumulation-and-fill: {args.var}  files={files}")
    print(f"Shape: {data.shape} (axis 0 treated as time/record)")
    print(f"Attributes found: units={attrs.get('units', '<none>')!r} "
          f"cell_methods={attrs.get('cell_methods', '<none>')!r} "
          f"long_name={attrs.get('long_name', '<none>')!r}")

    step_diff = np.diff(data, axis=0)
    finite_steps = np.isfinite(step_diff)
    decreasing = finite_steps & (step_diff < 0)
    n_decreasing_steps = int(decreasing.sum())
    cell_has_decrease = decreasing.reshape(decreasing.shape[0], -1).any(axis=0) if decreasing.ndim > 1 \
        else np.array([decreasing.any()])
    frac_cells_reset = float(cell_has_decrease.mean()) if cell_has_decrease.size else 0.0
    monotone = n_decreasing_steps == 0
    print(f"Monotone non-decreasing over time: {monotone}")
    print(f"Decreasing steps observed: {n_decreasing_steps} of {int(finite_steps.sum())} finite steps")
    print(f"Fraction of cells with at least one decrease (reset candidate): {frac_cells_reset:.4f}")
    out["monotone"] = monotone
    out["n_decreasing_steps"] = n_decreasing_steps
    out["frac_cells_reset"] = frac_cells_reset

    large_neg_threshold = args.large_negative_threshold
    large_neg = np.isfinite(data) & (data <= large_neg_threshold)
    n_large_neg = int(large_neg.sum())
    if n_large_neg:
        neg_values = sorted(set(np.round(data[large_neg], 6).tolist()))[:20]
    else:
        neg_values = []
    print(f"Large-magnitude negative values (<= {large_neg_threshold:g}): {n_large_neg} cells; "
          f"distinct sample values: {neg_values}")
    out["n_large_negative"] = n_large_neg
    out["large_negative_sample"] = neg_values

    fill_declared = ("_FillValue" in attrs) or ("missing_value" in attrs)
    print(f"_FillValue/missing_value declared: {fill_declared} "
          f"(_FillValue={attrs.get('_FillValue', '<none>')!r}, missing_value={attrs.get('missing_value', '<none>')!r})")
    out["fill_declared"] = fill_declared

    cell_has_large_neg = large_neg.reshape(large_neg.shape[0], -1).any(axis=0) if large_neg.ndim > 1 \
        else np.array([large_neg.any()])
    frac_cells_large_neg = float(cell_has_large_neg.mean()) if cell_has_large_neg.size else 0.0
    print(f"Fraction of cells ever affected by a large negative value: {frac_cells_large_neg:.4f}")
    out["frac_cells_large_negative"] = frac_cells_large_neg

    if args.pack:
        pack_verdict, pack_detail = declared_vs_observed(
            args.pack, args.var, monotone=monotone, fill_declared=fill_declared,
            n_large_neg=n_large_neg)
        out["pack_declared_vs_observed"] = pack_detail
        out["pack_verdict"] = pack_verdict

    print()
    verdicts = []
    if "monotone_expected" in thresholds:
        expected = bool(thresholds["monotone_expected"])
        verdicts.append(verdict_line("monotone_expected", "monotone_expected", thresholds,
                                      monotone == expected,
                                      f"expected monotone={expected}, observed={monotone}"))
    if "large_negative_allowed" in thresholds:
        allowed = bool(thresholds["large_negative_allowed"])
        ok = allowed or n_large_neg == 0
        verdicts.append(verdict_line("large_negative_allowed", "large_negative_allowed", thresholds,
                                      ok, f"large_negative_allowed={allowed}, observed count={n_large_neg}"))
    if "fill_declared_expected" in thresholds:
        expected = bool(thresholds["fill_declared_expected"])
        verdicts.append(verdict_line("fill_declared_expected", "fill_declared_expected", thresholds,
                                      fill_declared == expected,
                                      f"expected declared={expected}, observed={fill_declared}"))
    if not verdicts:
        verdicts.append("VERDICT: UNVERIFIED — no expectations supplied "
                         "(pass --thresholds with monotone_expected / large_negative_allowed / fill_declared_expected)")
    for v in verdicts:
        print(v)

    if args.json:
        out["verdicts"] = verdicts
        print(json.dumps(out, indent=2, default=str))
    return 0


_CGF_STRUCT_FIELD_TO_KEY_RE = re.compile(r"(global_param|options)\s*\.\s*(\w+)")
_CGF_TOKEN_RE = re.compile(r"[A-Za-z_]\w*")
# A small, fixed resolver for the handful of named C constants VIC's own
# global-parameter-file validation conditions compare against, that are not
# themselves global-parameter-file keys or physical `#define`s already in a pack's
# constants.yaml (they are compiled-in structural limits from vic_def.h, not
# vic_physical_constants.h). Generic in spirit -- reused for any pack whose
# constraints reference them -- but this specific name set is VIC's; a future pack
# would extend it, not replace the mechanism.
_CGF_STRUCT_CONSTANTS = {"MIN_SUBDAILY_STEPS_PER_DAY": 4, "MAX_SUBDAILY_STEPS_PER_DAY": 1440}


def _cgf_parse_file(path):
    """First whitespace token of every non-comment, non-blank line -> its remaining
    tokens (so a repeated key like FORCE_TYPE/OUTVAR keeps every occurrence, not just
    the last) -- same convention as validate_catalogs.py's own
    _parse_global_param_file_keys, kept independent here so this subcommand has no
    import-order dependency on that module."""
    rows = []
    for raw in Path(path).read_text(encoding="utf-8", errors="replace").splitlines():
        s = raw.strip()
        if not s or s.startswith("#"):
            continue
        toks = s.split()
        rows.append((toks[0], toks[1:]))
    return rows


def _cgf_build_constant_env(pack_dir):
    env = dict(_CGF_STRUCT_CONSTANTS)
    const_path = pack_dir / "catalogs" / "constants.yaml"
    if const_path.is_file():
        doc = _load_structured(const_path)
        for c in doc.get("constants", []):
            try:
                env[c["name"]] = float(c["value"]) if "." in c["value"] or "e" in c["value"].lower() else int(c["value"])
            except (ValueError, KeyError):
                continue
    return env


def _cgf_eval_condition(condition, file_values, const_env):
    """Best-effort evaluation of one catalog `constraints[].condition` string (raw C,
    e.g. 'global_param.snow_steps_per_day % global_param.model_steps_per_day != 0')
    against the parsed global-parameter-file's own integer values. Returns (result:
    bool, reason: str) or (None, reason) if the condition could not be evaluated (a key
    the file does not set, an unresolved constant, or C syntax this narrow translator
    does not cover -- e.g. a function call or array index) -- never guessed, always
    reported as NOT EVALUATED rather than silently skipped."""
    py_expr = condition.replace("&&", " and ").replace("||", " or ")

    def repl_field(m):
        struct, field = m.groups()
        key = file_values.get("_field_to_key", {}).get(f"{struct}.{field}")
        if key is None or key not in file_values:
            raise KeyError(f"{struct}.{field}")
        return repr(file_values[key])
    try:
        py_expr = _CGF_STRUCT_FIELD_TO_KEY_RE.sub(repl_field, py_expr)
    except KeyError as exc:
        return None, f"NOT EVALUATED (key not set in this file: {exc})"

    def repl_const(m):
        tok = m.group(0)
        if tok in ("and", "or", "not", "True", "False"):
            return tok
        if re.match(r"^\d", tok):
            return tok
        if tok in const_env:
            return repr(const_env[tok])
        raise KeyError(tok)
    try:
        py_expr = _CGF_TOKEN_RE.sub(repl_const, py_expr)
    except KeyError as exc:
        return None, f"NOT EVALUATED (unresolved constant/expression: {exc})"
    try:
        result = bool(eval(py_expr, {"__builtins__": {}}, {}))  # noqa: S307 -- fully substituted, digits/operators only
    except Exception as exc:  # noqa: BLE001 -- any leftover C syntax this translator can't handle
        return None, f"NOT EVALUATED (could not translate: {exc})"
    return result, py_expr


def cmd_check_global_file(args):
    """Validate a user's VIC (or any pack with the same global_parameters.yaml shape)
    global parameter file against catalogs/global_parameters.yaml: every key present
    is checked for recognition by the given --driver's parser (typo/wrong-driver
    detection), a removed-since-VIC-4 key is flagged with its own quoted rejection
    message, and every catalog `constraints[].condition` this narrow C-expression
    translator can evaluate against the file's own values is checked and reported
    VIOLATED/OK/NOT EVALUATED. Read-only; never modifies the file. Does NOT establish
    that an accepted file will run to completion -- only the checks named above."""
    pack_dir = MODELS_DIR / args.pack
    gp_path = pack_dir / "catalogs" / "global_parameters.yaml"
    if not gp_path.is_file():
        sys.exit(f"ERROR: no catalogs/global_parameters.yaml for pack '{args.pack}' -- "
                  f"this subcommand needs that catalog's shape (key/type/constraints).")
    gp_doc = _load_structured(gp_path)
    driver_keys = {k["key"].upper(): k for k in gp_doc["keys"] if k["where"]["driver"] == args.driver}
    field_to_key = {}
    for k in gp_doc["keys"]:
        if k["where"]["driver"] == args.driver and k.get("assigned_field"):
            field_to_key.setdefault(k["assigned_field"], k["key"].upper())

    rows = _cgf_parse_file(args.file)
    file_values = {"_field_to_key": field_to_key}
    seen_keys = set()
    findings = []
    for key, rest in rows:
        ku = key.upper()
        seen_keys.add(ku)
        entry = driver_keys.get(ku)
        if entry is None:
            findings.append(("UNRECOGNIZED", ku, f"'{key}' is not a key --driver={args.driver}'s "
                                                    f"get_global_param.c recognizes at this pinned commit "
                                                    f"(checked against catalogs/global_parameters.yaml)."))
            continue
        if entry.get("type") == "removed_since_vic4":
            findings.append(("REMOVED", ku, entry.get("removed_since_vic4_message") or
                              "removed since VIC 4 (no message text extracted)."))
        if rest:
            try:
                file_values[ku] = int(rest[0])
            except ValueError:
                try:
                    file_values[ku] = float(rest[0])
                except ValueError:
                    file_values[ku] = rest[0]

    const_env = _cgf_build_constant_env(pack_dir)
    n_evaluated = n_violated = n_not_evaluated = 0
    for c in gp_doc.get("constraints", []):
        if c["where"]["driver"] not in (args.driver, "both"):
            continue
        result, detail = _cgf_eval_condition(c["condition"], file_values, const_env)
        if result is None:
            n_not_evaluated += 1
            continue
        n_evaluated += 1
        if result:
            n_violated += 1
            findings.append(("VIOLATED", c["condition"], c.get("message") or "(no message text extracted)"))

    print(f"# check-global-file: pack={args.pack} driver={args.driver} file={args.file}")
    print(f"  {len(rows)} lines read, {len(seen_keys)} distinct keys, "
          f"{n_evaluated} constraint(s) evaluated ({n_not_evaluated} not evaluated -- "
          f"see tools/README.md), {n_violated} violated.")
    for kind, name, detail in findings:
        print(f"  {kind}: {name} -- {detail}")
    if not findings:
        print("  QUIET: no unrecognized/removed keys, no evaluated constraint violated.")
    if args.json:
        print(json.dumps({"pack": args.pack, "driver": args.driver, "file": str(args.file),
                           "n_keys": len(seen_keys), "n_constraints_evaluated": n_evaluated,
                           "n_not_evaluated": n_not_evaluated,
                           "findings": [{"kind": k, "name": n, "detail": d} for k, n, d in findings]},
                          indent=2))
    return 1 if findings else 0


_CCF_LINE_RE = re.compile(r"^<([^>]+)>(.*)$")


def _ccf_parse_file(path):
    """(key, value, line number) for every `<key>  value  ! comment` line of a tag-style
    control file: a line whose first non-blank character is not `<` is a comment or
    blank and is skipped, and a value ends at the first `!`. This is the file shape the
    catalog's own keys are written as (`<key>`), not a second format guess."""
    rows = []
    for n, raw in enumerate(Path(path).read_text(encoding="utf-8", errors="replace").splitlines(), 1):
        s = raw.strip()
        m = _CCF_LINE_RE.match(s)
        if not m:
            continue
        value = m.group(2).split("!", 1)[0].strip()
        rows.append((m.group(1).strip(), value, n))
    return rows


def _ccf_allowed_value_findings(key_entry, value):
    """(findings, not_evaluated) for one key's `allowed_values` rows against the value
    the file gives it. A row constrains the value as a whole when its `variable` names
    the key itself or the variable the key assigns to; a row about a *part* of the value
    (a units string's length or time half) names that part instead, and this translator
    does not split values, so such a row is reported NOT EVALUATED with its own note
    rather than guessed at. A row without the parser's own `rejection_message` is not a
    closed set -- the code accepts other forms of the value too (a keyword OR a number,
    say) -- so membership is not asserted for it either."""
    findings, not_evaluated = [], []
    for row in key_entry.get("allowed_values") or []:
        subject = row.get("variable")
        whole_value = subject in (key_entry.get("key"), key_entry.get("assigns_to"))
        accepted = [v for group in (row.get("values") or []) for v in (group.get("values") or [])]
        if not accepted:
            continue
        note = row.get("note") or ""
        if not whole_value:
            not_evaluated.append(f"{key_entry['key']}: the accepted set is stated for "
                                  f"{subject} ({note or 'a part of the value'}), not for the "
                                  f"whole value -- not evaluated")
            continue
        if not row.get("rejection_message"):
            not_evaluated.append(f"{key_entry['key']}: {subject} has a listed set "
                                  f"({', '.join(accepted)}) but the code rejects nothing "
                                  f"outside it ({note or 'other forms are accepted too'}) "
                                  f"-- not evaluated")
            continue
        fold = "case insensitive" in note.lower() or "case-insensitive" in note.lower()
        hay = [a.lower() for a in accepted] if fold else accepted
        if (value.lower() if fold else value) not in hay:
            findings.append(("VALUE NOT ACCEPTED", key_entry["key"],
                              f"'{value}' is not one of {', '.join(accepted)}"
                              + (" (matched case-insensitively)" if fold else "")
                              + f" -- the parser's own message: {row['rejection_message']}"))
    return findings, not_evaluated


def cmd_check_control_file(args):
    """Validate a tag-style control file against a pack's catalogs/control_keys.yaml:
    every `<key>` the file sets is checked for recognition by the pinned parser (a
    documented-but-unparsed or sample-file-but-unparsed key is named with the catalogued
    consequence), and every value the catalog carries a closed accepted set for is
    checked against it, quoting the parser's own rejection message. Read-only; never
    modifies the file. Does NOT establish that an accepted file will run: the post-parse
    constraints the catalog carries as messages only, the input files the control file
    points at, and every key whose accepted set is stated for part of its value are all
    outside what this subcommand evaluates -- each is counted and named, never skipped
    silently."""
    pack_dir = MODELS_DIR / args.pack
    ck_path = pack_dir / "catalogs" / "control_keys.yaml"
    if not ck_path.is_file():
        sys.exit(f"ERROR: no catalogs/control_keys.yaml for pack '{args.pack}' -- "
                  f"this subcommand needs that catalog's shape (key/allowed_values/"
                  f"requiredness).")
    doc = _load_structured(ck_path)
    entries = doc.get(doc.get("entries_key") or "keys", [])
    by_key = {e["key"]: e for e in entries}
    unparsed = {}
    for field in ("in_sample_but_not_parsed", "documented_but_not_parsed"):
        for row in doc.get(field) or []:
            unparsed.setdefault(row["key"], (field, row))

    rows = _ccf_parse_file(args.file)
    findings, not_evaluated = [], []
    seen = set()
    for key, value, line_no in rows:
        seen.add(key)
        entry = by_key.get(key)
        if entry is None:
            message = (doc.get("unrecognized_key_message") or "").strip().strip("()")
            detail = (f"line {line_no}: '<{key}>' is not a key the pinned parser recognizes"
                      + (f" -- the parser's own note: {message}" if message else ""))
            if key in unparsed:
                field, row = unparsed[key]
                detail += f" -- {row.get('consequence')} [{field}: {row['where']['file']}:{row['where']['line']}]"
            findings.append(("UNRECOGNIZED", key, detail))
            continue
        f, ne = _ccf_allowed_value_findings(entry, value)
        findings.extend(f)
        not_evaluated.extend(ne)

    constraints = doc.get("post_parse_constraints") or []
    required_missing = sorted(k["key"] for k in entries
                               if k.get("requiredness") == "must_be_set_in_control_file"
                               and k["key"] not in seen)

    print(f"# check-control-file: pack={args.pack} file={args.file}")
    print(f"  {len(rows)} key line(s) read, {len(seen)} distinct keys, "
          f"{len(findings)} finding(s), {len(not_evaluated)} value set(s) not evaluated, "
          f"{len(constraints)} post-parse constraint(s) the catalog carries as a message "
          f"only and this tool does not evaluate.")
    for kind, name, detail in findings:
        print(f"  {kind}: {name} -- {detail}")
    for note in not_evaluated:
        print(f"  NOT EVALUATED: {note}")
    if required_missing:
        print(f"  NOTE: {len(required_missing)} catalogued key(s) with no in-code default are "
              f"not set here: {', '.join(required_missing[:12])}"
              + (" ..." if len(required_missing) > 12 else "")
              + ". Requiredness is read from the declaration alone, so a key needed only "
                "under an option this file does not use is listed too -- this is a note, "
                "not a finding.")
    if not findings:
        print("  QUIET: every key is recognized and every evaluable value is in its "
              "accepted set.")
    if args.json:
        print(json.dumps({"pack": args.pack, "file": str(args.file), "n_keys": len(seen),
                           "n_not_evaluated": len(not_evaluated),
                           "n_constraints_not_evaluated": len(constraints),
                           "required_not_set": required_missing,
                           "findings": [{"kind": k, "name": n, "detail": d} for k, n, d in findings]},
                          indent=2))
    return 1 if findings else 0


NOT_ESTABLISHED_PAIRED = (
    "Does NOT establish: causality (association only), physical correctness of the "
    "magnitude, whether the controlling variable is the right or only cause, or "
    "acceptability of any difference — acceptance criteria belong in the project's "
    "experiment record, set by the research owner."
)
NOT_ESTABLISHED_ACCUM = (
    "Does NOT establish: the correct reset schedule or units, whether a detected "
    "large-negative value is actually a fill value versus a real physical value, or "
    "whether any observed behavior is acceptable — acceptance criteria belong in the "
    "project's experiment record, set by the research owner."
)


def build_parser():
    parser = argparse.ArgumentParser(
        prog="hcm_check.py",
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser(
        "paired-response",
        help="Compare two runs and report where they differ and whether the difference scales with a control field.",
        epilog=NOT_ESTABLISHED_PAIRED,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--a", required=True, help="File or glob for run A")
    p.add_argument("--b", required=True, help="File or glob for run B")
    p.add_argument("--var", required=True, help="Variable to compare")
    p.add_argument("--control-file", help="File holding the controlling variable")
    p.add_argument("--control-var", help="Name of the controlling variable")
    p.add_argument("--mask-file", help="File holding a mask/class variable")
    p.add_argument("--mask-var", help="Name of the mask variable")
    p.add_argument("--mask-value", type=float, default=None, help="Report only this mask class")
    p.add_argument("--invariants", help="Comma-separated variable names expected identical between A and B")
    p.add_argument("--record", default=None, help="Integer time/record index to select, or 'all' (default)")
    p.add_argument("--thresholds", help="JSON file, or a text/Markdown file (e.g. experiment record) "
                                         "with 'key: value' lines; recognized keys: spearman_min, "
                                         "invariants_identical, nonzero_expected")
    p.add_argument("--pack", help="Model pack name (e.g. hrldas-noahmp), resolved under "
                                   "references/models/ next to this tool")
    p.add_argument("--switch", help="Switch name to read declared effects for from the pack's "
                                     "the switches layer (requires --pack); annotation only, never applied")
    p.add_argument("--json", action="store_true", help="Also print a JSON summary")
    p.set_defaults(func=cmd_paired_response)

    p = sub.add_parser(
        "accumulation-and-fill",
        help="Check whether a variable behaves as a monotone accumulator and report undeclared fill/large-negative values.",
        epilog=NOT_ESTABLISHED_ACCUM,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--files", required=True, help="File or glob of files ordered by time")
    p.add_argument("--var", required=True, help="Variable to check")
    p.add_argument("--mask-file", help="File holding a mask/class variable (reserved; not yet applied to this check)")
    p.add_argument("--mask-var", help="Name of the mask variable")
    p.add_argument("--mask-value", type=float, default=None, help="Mask class value")
    p.add_argument("--large-negative-threshold", type=float, default=-1e4,
                    help="Values at or below this are reported as large-magnitude negative (default -1e4)")
    p.add_argument("--thresholds", help="JSON file, or a text/Markdown file (e.g. experiment record) "
                                         "with 'key: value' lines; recognized keys: monotone_expected, "
                                         "large_negative_allowed, fill_declared_expected")
    p.add_argument("--pack", help="Model pack name (e.g. hrldas-noahmp), resolved under "
                                   "references/models/ next to this tool")
    p.add_argument("--json", action="store_true", help="Also print a JSON summary")
    p.set_defaults(func=cmd_accumulation_and_fill)

    p = sub.add_parser(
        "pack-info",
        help="Print a pack's declared layers, coverage, scopes, and fact counts by basis.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--pack", required=True, help="Model pack name, resolved under references/models/")
    p.add_argument("--json", action="store_true", help="Also print a JSON summary")
    p.set_defaults(func=cmd_pack_info)

    p = sub.add_parser(
        "pitfall-scan",
        help="Run every declared pitfall detection in a pack whose required inputs are available.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--pack", required=True, help="Model pack name, resolved under references/models/")
    p.add_argument("--files", nargs="+", default=[], help="Files or globs available for detection")
    p.add_argument("--var", help="Variable name, when a detection needs one")
    p.add_argument("--control-var", help="Controlling variable, when a detection needs one")
    p.add_argument("--thresholds", help="Passed through to detections that use --thresholds")
    p.add_argument("--json", action="store_true", help="Also print a JSON summary")
    p.set_defaults(func=cmd_pitfall_scan)

    p = sub.add_parser(
        "describe",
        help="List every variable in a file with observed dims/units/fill/monotonicity "
             "next to whatever a pack declares about it (NO DECLARATION where silent).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--pack", required=True, help="Model pack name, resolved under references/models/")
    p.add_argument("--file", required=True, help="A single NetCDF file to describe")
    p.set_defaults(func=cmd_describe)

    p = sub.add_parser(
        "lookup",
        help="Print a pack's generated index.json entry for a variable/key/file-kind name.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--pack", required=True, help="Model pack name, resolved under references/models/")
    p.add_argument("name", help="Variable name, configuration key, or file kind to look up")
    p.add_argument("--json", action="store_true", help="Also print a JSON summary")
    p.set_defaults(func=cmd_lookup)

    p = sub.add_parser(
        "check-global-file",
        help="Validate a global-parameter-file-shaped input against a pack's catalogs/"
             "global_parameters.yaml: unrecognized keys, removed-since-VIC-4 keys "
             "(with their own message), and every evaluable step-count/validation "
             "constraint.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--pack", required=True, help="Model pack name, resolved under references/models/ "
                                                   "(needs a catalogs/global_parameters.yaml)")
    p.add_argument("--driver", required=True, help="Driver whose key list/constraints to check against "
                                                     "(e.g. classic or image, for vic)")
    p.add_argument("--file", required=True, help="The global parameter file to check")
    p.add_argument("--json", action="store_true", help="Also print a JSON summary")
    p.set_defaults(func=cmd_check_global_file)

    p = sub.add_parser(
        "check-control-file",
        help="Validate a tag-style control file against a pack's catalogs/"
             "control_keys.yaml: keys the pinned parser does not recognize (including "
             "a key only the documentation or a shipped sample uses) and values outside "
             "a catalogued accepted set, with the parser's own message.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--pack", required=True, help="Model pack name, resolved under references/models/ "
                                                   "(needs a catalogs/control_keys.yaml)")
    p.add_argument("--file", required=True, help="The control file to check")
    p.add_argument("--json", action="store_true", help="Also print a JSON summary")
    p.set_defaults(func=cmd_check_control_file)

    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args) or 0
    except SystemExit:
        raise
    except Exception as exc:  # noqa: BLE001 - top-level usage/IO guard, no traceback for the user
        sys.exit(f"ERROR: {exc}")


if __name__ == "__main__":
    sys.exit(main())
