#!/usr/bin/env python3
"""hcm_lookup.py -- answers a single-name lookup from a pack's generated catalogs
(references/models/<pack>/catalogs/*.yaml; see SCHEMA.md), across output variables,
restart variables, namelist keys, physics options, parameter-table entries, land-use/soil
class names, and physical constants. Where present, catalogs/kinds_overlay.yaml and
catalogs/options_overlay.yaml (curated, hand-verified -- never generated) are merged in:
an overlay's `true_kind` is shown ahead of the generated `kind`, never silently replacing
it, plus any `sampling_note`/`units_note`/`gate`.

Kept separate from hcm_check.py's own `lookup` subcommand (which answers from the
curated, hand-authored index.json -- see SCHEMA.md) so that tool's existing behavior is
untouched.

Exact match first; if none, a fuzzy "did you mean" against every catalog name (near-miss
spellings, e.g. one or two changed letters, are a known failure mode -- see the rebuild
plan's KISS comparison). Output is capped at 25 printed lines.

--list kind=<true_kind> lists every kinds_overlay.yaml row with that true_kind.
--process <keyword> lists output variables/physics options whose name or description
contains the keyword (a cheap substring filter over the already-loaded catalogs, not a
second index) -- e.g. --process snow, --process urban, --process runoff.
"""
import argparse
import difflib
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
MODELS_DIR = HERE.parent / "references/models"
MAX_LINES = 25
sys.path.insert(0, str(HERE))
import _miniyaml  # noqa: E402


def _load(pack_dir, stem):
    """Load `catalogs/<stem>.yaml`, or `catalogs/<stem>.json` for a pack that has not
    been converted to the catalog family yet."""
    yaml_path = pack_dir / "catalogs" / f"{stem}.yaml"
    if yaml_path.is_file():
        return _miniyaml.load_file(yaml_path)
    json_path = pack_dir / "catalogs" / f"{stem}.json"
    return json.loads(json_path.read_text()) if json_path.is_file() else None


def load_overlays(pack_dir):
    """kinds_overlay.yaml rows indexed by variable name (upper-cased), and
    options_overlay.yaml rows grouped by internal_option_name. Either file is optional;
    a pack with neither just gets no overlay merge."""
    kinds_by_var = {}
    kinds_doc = _load(pack_dir, "kinds_overlay")
    if kinds_doc:
        for row in kinds_doc.get("rows", []):
            kinds_by_var[row["variable"].upper()] = row

    options_by_opt = {}
    options_doc = _load(pack_dir, "options_overlay")
    if options_doc:
        for row in options_doc.get("rows", []):
            options_by_opt.setdefault(row["internal_option_name"], []).append(row)

    return kinds_by_var, options_by_opt


_INTERNAL_NAME_RE = re.compile(r"noahmp\s*%(?:\s*\w+\s*%)+\s*(\w+)\s*(?:\(|$)", re.I)


def _internal_name_from_evidence(entry):
    """The noahmp-internal (physics-struct) name a variable's value comes from, parsed
    from kind_evidence's transfer-assignment text (e.g. 'NoahmpIO%HFX(I,J) =
    noahmp%energy%flux%HeatSensibleSfc' -> 'HeatSensibleSfc'). None if kind_evidence has
    no transfer/accumulate text to parse (state fields set elsewhere, forcing pass-
    through, etc.) -- never guessed."""
    ev = entry.get("kind_evidence") or {}
    for key in ("overwrite_in_transfer", "accumulate"):
        sub = ev.get(key)
        if sub and sub.get("text"):
            m = _INTERNAL_NAME_RE.search(sub["text"])
            if m:
                return m.group(1)
    return None


def collect_index(pack_dir):
    """List of (display_name, kind, entry) across every catalog, for exact/fuzzy match.
    Every identifier a user or the pack's own prose might type is indexed, not just the
    catalog's own primary name: for a physics option, the namelist key, the IOPT_*
    driver/IO variable and the Opt* internal name all resolve to the same entry
    (case-insensitively, since lookup already lower()s); for a table parameter, the
    table's own key, the NoahmpIO *_TABLE array name and the short internal name (e.g.
    BB / BEXP_TABLE / BEXP) all resolve to the same entry; for an output/restart
    variable, the written name, the driver array, and the noahmp-internal name (parsed
    from the same transfer-assignment evidence the kind classifier already extracted)
    all resolve to the same entry. See `history_restart_crossref` for the separate
    history<->restart name link, since those are two different catalog entries, not
    aliases of the same one."""
    items = []

    outputs = _load(pack_dir, "outputs")
    if outputs:
        for v in outputs["variables"]:
            items.append((v["name"], "output variable", v))
            internal = _internal_name_from_evidence(v)
            if internal and internal.upper() != v["name"].upper():
                items.append((internal, "output variable (by internal noahmp name)", v))

    restart = _load(pack_dir, "restart")
    if restart:
        for v in restart["variables"]:
            items.append((v["name"], "restart variable", v))
            internal = _internal_name_from_evidence(v)
            if internal and internal.upper() != v["name"].upper():
                items.append((internal, "restart variable (by internal noahmp name)", v))

    forcing = _load(pack_dir, "forcing")
    if forcing:
        for e in forcing["inputs"]:
            name = e.get("ldasin_name") or e.get("namelist_default") or e.get("role")
            if name:
                items.append((name, "forcing input", e))

    setup = _load(pack_dir, "setup")
    if setup:
        for f in setup["fields"]:
            fname = f.get("field")
            if fname and not fname.startswith("("):  # skip the landuse/soilcat placeholders
                items.append((fname, "setup-file field", f))

    namelist = _load(pack_dir, "namelist")
    if namelist:
        for o in namelist["options"]:
            items.append((o["key"], "namelist option", o))

    physics = _load(pack_dir, "physics_options")
    if physics:
        for o in physics["options"]:
            items.append((o["internal_option_name"], "physics option", o))
            if o.get("namelist_key"):
                items.append((o["namelist_key"], "physics option (by namelist key)", o))
            if o.get("iopt_field"):
                items.append((o["iopt_field"], "physics option (by driver/IO variable)", o))

    constants = _load(pack_dir, "constants")
    if constants:
        for c in constants["constants"]:
            items.append((c["name"], "physical constant", c))

    parameters = _load(pack_dir, "parameters")
    if parameters:
        for g in parameters["noahmp_table_groups"]:
            for p in g["parameters"]:
                items.append((p["parameter"], f"parameter ({g['group']})", p))
                if p.get("noahmp_io_array"):
                    items.append((p["noahmp_io_array"], f"parameter (by NoahmpIO table array, {g['group']})", p))
                if p.get("internal_name") and p["internal_name"].upper() != p["parameter"].upper():
                    items.append((p["internal_name"], f"parameter (by internal name, {g['group']})", p))
            for c in g.get("class_index_to_name", []):
                items.append((c["name"], f"class name ({g['group']}, index {c['index']})", c))
        for t in parameters["urbparm_tables"]:
            for k in t["keys"]:
                items.append((k["key"], f"urban parameter table key ({t['table']})", k))

    return items


def history_restart_crossref(pack_dir):
    """{driver_array: {"history": name_or_None, "restart": name_or_None}} -- the
    mechanical link between a history (output) name and its restart counterpart is the
    shared NoahmpIO% driver array both catalogs already record; two different names for
    the same array is exactly the SFCRNOFF/SFCRUNOFF trap (see failures.md)."""
    crossref = {}
    outputs = _load(pack_dir, "outputs")
    for v in (outputs or {}).get("variables", []):
        crossref.setdefault(v["driver_array"], {})["history"] = v["name"]
    restart = _load(pack_dir, "restart")
    for v in (restart or {}).get("variables", []):
        crossref.setdefault(v["driver_array"], {})["restart"] = v["name"]
    return crossref


def _where_str(w):
    return f"{w['file']}:{w['line']} ({w['commit']})" if w else None


def _file_order_dims(entry):
    """SCHEMA.md: a real file's dimension order is the REVERSE of the source-declared
    (Fortran nf90_def_var) order this catalog records -- confirmed by
    validate_catalogs.py against real files, not a discrepancy. Report what a reader
    will actually see in the file, not the source declaration order, since that is what
    "dims in FILE order as observed" means."""
    dims = entry.get("dim_order")
    return list(reversed(dims)) if dims else None


_CANONICAL_NAME_KEY = {
    "output variable": "name", "restart variable": "name",
    "physics option": "internal_option_name",
}


def print_entry(name, kind, entry, lines, kinds_overlay=None, options_overlay=None, crossref=None):
    base_kind = kind.split(" (by ")[0]
    alias_desc = kind[len(base_kind):].strip()  # "" or "(by internal noahmp name)" etc.
    canon_key = _CANONICAL_NAME_KEY.get(base_kind)
    canon = entry.get(canon_key) if canon_key else None
    header = f"# {canon}  [{base_kind}]" if canon else f"# {name}  [{kind}]"
    if canon and canon.upper() != name.upper():
        header += f"  (matched via alias '{name}' {alias_desc})" if alias_desc else f"  (matched via alias '{name}')"
    lines.append(header)

    if base_kind in ("output variable", "restart variable"):
        canonical_name = entry.get("name", name)
        if crossref:
            this_kind, other_kind = (("history", "restart") if base_kind == "output variable"
                                      else ("restart", "history"))
            pair = crossref.get(entry.get("driver_array"), {})
            other_name = pair.get(other_kind)
            if other_kind not in pair:
                lines.append(f"  NOTE: this field has no {other_kind.upper()} counterpart "
                              f"(driver array {entry.get('driver_array')} is not written to "
                              f"{other_kind} output at this commit)")
            elif other_name and other_name.upper() != canonical_name.upper():
                lines.append(f"  NOTE: this is the {this_kind.upper()} name; in {other_kind} "
                              f"output the same field (driver array {entry.get('driver_array')}) "
                              f"is written as `{other_name}`")
        if entry.get("description"):
            lines.append(f"  description: {entry['description']}")
        units_line = f"  units: {entry.get('units')}"
        overlay_row = kinds_overlay.get(canonical_name.upper()) if kinds_overlay else None
        if overlay_row and overlay_row.get("units_note"):
            units_line += f"  [units_note: {overlay_row['units_note']}]"
        if entry.get("units") is not None or (overlay_row and overlay_row.get("units_note")):
            lines.append(units_line)
        kind_line = f"  kind: {entry.get('kind')}"
        if overlay_row:
            kind_line = f"  kind: {entry.get('kind')}  [true_kind (curated): {overlay_row['true_kind']}]"
        lines.append(kind_line)
        if overlay_row and overlay_row.get("sampling_note"):
            lines.append(f"  sampling_note: {overlay_row['sampling_note']}")
        if overlay_row and overlay_row.get("note"):
            lines.append(f"  overlay_note: {overlay_row['note']}")
        file_dims = _file_order_dims(entry)
        if file_dims:
            lines.append(f"  dims (file order, observed -- reverse of source-declared): {file_dims}")
        if entry.get("gating"):
            lines.append(f"  gating (written only when): {entry['gating']}")
        if entry.get("fill_note"):
            lines.append(f"  fill/mask: {entry['fill_note']}")
        where = entry.get("where")
        if where:
            lines.append(f"  where (output registration): {_where_str(where)}")
        if overlay_row and overlay_row.get("where") and overlay_row["where"] != where:
            lines.append(f"  where (true_kind evidence): {_where_str(overlay_row['where'])}")
        if overlay_row and overlay_row.get("reset_where"):
            lines.append(f"  where (reset): {_where_str(overlay_row['reset_where'])}")
        if overlay_row and overlay_row.get("gate"):
            lines.append(f"  overlay gate (written when): {overlay_row['gate']}")
        if overlay_row and overlay_row.get("updated_when"):
            lines.append(f"  UPDATED WHEN (may be written every record but only live "
                          f"under this): {overlay_row['updated_when']}")
        if entry.get("evidence"):
            lines.append(f"  evidence: {entry['evidence']}")
        return

    if kind.startswith("physics option"):
        if entry.get("namelist_key"):
            lines.append(f"  namelist_key: {entry['namelist_key']}")
        if entry.get("default_in_code") is not None:
            lines.append(f"  default_in_code: {entry['default_in_code']}")
        readme_vals = {v["value"]: v["meaning"] for v in entry.get("readme_values", [])}
        code_vals = {b["value"]: b for b in entry.get("code_branches", [])}
        all_values = sorted(set(readme_vals) | set(code_vals), key=lambda x: int(x))
        for v in all_values[:8]:
            meaning = readme_vals.get(v, "<no README meaning found>")
            branch = code_vals.get(v)
            if branch:
                cites = branch["citations"]
                # A citation with a named routine ('call Routine(...)' on that line) is
                # the site that actually selects the scheme; an 'inline' citation (no
                # named routine) is just a comparison and should not be shown first just
                # because it happened to scan first (file-alphabetical, then line order
                # -- not dispatch order).
                ordered = sorted(cites, key=lambda c: c.get("routine") is None)
                lead = ordered[0]
                routine = lead.get("routine") or "(inline, no named routine)"
                branch_str = f"{routine} @ {lead['where']['file']}:{lead['where']['line']}"
                if len(ordered) > 1:
                    if len(ordered) <= 6:
                        rest = ", ".join(
                            f"{c.get('routine') or '(inline)'} @ {c['where']['file']}:{c['where']['line']}"
                            for c in ordered[1:])
                        branch_str += f"; also: {rest}"
                    else:
                        branch_str += f" (+{len(ordered) - 1} more site(s))"
            else:
                branch_str = "<no code branch found -- see options_overlay.yaml or it may " \
                             "be a relational (>, /=) gate, not a literal ==N>"
            lines.append(f"  {v} = {meaning}  ->  {branch_str}")
        if len(all_values) > 8:
            lines.append(f"  ... ({len(all_values) - 8} more values)")
        overlay_rows = (options_overlay or {}).get(entry.get("internal_option_name"), [])
        for orow in overlay_rows[:3]:
            lines.append(f"  overlay ({orow['value']}): {orow['note']}")
        mc = entry.get("mapping_chain") or {}
        if mc.get("iopt_to_internal"):
            lines.append(f"  where (namelist->internal mapping): "
                          f"{_where_str(mc['iopt_to_internal'].get('where'))}")
        return

    # Generic fallback for every other catalog kind (forcing/namelist/parameter/constant/...).
    for key in ("description", "readme_description", "value_or_row", "values_as_written",
                "units", "value", "role", "default_in_code", "readme_default"):
        if key in entry and entry[key] not in (None, ""):
            lines.append(f"  {key}: {entry[key]}")
    if "kind" in entry:
        lines.append(f"  kind: {entry['kind']}")
    if "gating" in entry and entry["gating"]:
        lines.append(f"  gating: {entry['gating']}")
    if "allowed_values" in entry and entry["allowed_values"]:
        vals = ", ".join(f"{o['value']}={o['meaning']}" for o in entry["allowed_values"][:4])
        lines.append(f"  allowed_values: {vals}" + (" ..." if len(entry["allowed_values"]) > 4 else ""))
    where = entry.get("where")
    if where:
        lines.append(f"  where: {_where_str(where)}")
    if "evidence" in entry:
        lines.append(f"  evidence: {entry['evidence']}")


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--pack", required=True, help="Model pack name, e.g. hrldas-noahmp")
    p.add_argument("name", nargs="?",
                    help="Variable/key/parameter/constant/class name to look up "
                         "(omit when using --list or --process)")
    p.add_argument("--list", metavar="kind=VALUE",
                    help="List every kinds_overlay.yaml row with this true_kind, "
                         "e.g. --list kind=accumulated_since_start")
    p.add_argument("--process", metavar="KEYWORD",
                    help="List output variables and physics options whose name or "
                         "description contains KEYWORD (cheap substring filter)")
    p.add_argument("--json", action="store_true")
    args = p.parse_args(argv)

    pack_dir = MODELS_DIR / args.pack
    if not pack_dir.is_dir():
        sys.exit(f"ERROR: no such pack directory: {pack_dir}")
    if not (pack_dir / "catalogs").is_dir():
        sys.exit(f"No catalogs/ directory for pack '{args.pack}'. "
                  f"Build one with tools/extract_pack.py all --source-root ROOT "
                  f"--out-dir {pack_dir}/catalogs")

    kinds_overlay, options_overlay = load_overlays(pack_dir)
    items = collect_index(pack_dir)
    crossref = history_restart_crossref(pack_dir)
    lines = []

    if args.list:
        if not args.list.startswith("kind="):
            sys.exit("ERROR: --list expects 'kind=<true_kind>', e.g. --list kind=state")
        wanted = args.list[len("kind="):]
        matches = [r for r in kinds_overlay.values() if r["true_kind"] == wanted]
        if not matches:
            known = sorted({r["true_kind"] for r in kinds_overlay.values()})
            lines.append(f"No kinds_overlay.yaml rows with true_kind='{wanted}'. Known "
                          f"values in this pack: {', '.join(known) if known else '(none)'}")
        else:
            lines.append(f"# {len(matches)} variable(s) with true_kind={wanted}")
            for r in sorted(matches, key=lambda r: r["variable"]):
                lines.append(f"  {r['variable']}" + (f"  -- {r['note']}" if r.get("note") else ""))
        for line in lines[:MAX_LINES]:
            print(line)
        if len(lines) > MAX_LINES:
            print(f"... ({len(lines) - MAX_LINES} more lines truncated)")
        return 0

    if args.process:
        kw = args.process.lower()
        hits = []
        for n, k, e in items:
            if k not in ("output variable", "restart variable") and not k.startswith("physics option"):
                continue
            haystack = " ".join(str(e.get(f, "")) for f in
                                 ("description", "namelist_key", "internal_option_name")).lower()
            if kw in n.lower() or kw in haystack:
                hits.append((n, k, e))
        if not hits:
            lines.append(f"No output variable, restart variable or physics option matches "
                          f"'{args.process}' by name or description.")
        else:
            lines.append(f"# {len(hits)} match(es) for '{args.process}'")
            seen = set()
            for n, k, e in hits:
                if (n, k) in seen:
                    continue
                seen.add((n, k))
                desc = e.get("description") or ""
                lines.append(f"  {n}  [{k}]" + (f"  -- {desc}" if desc else ""))
        for line in lines[:MAX_LINES]:
            print(line)
        if len(lines) > MAX_LINES:
            print(f"... ({len(lines) - MAX_LINES} more lines truncated; narrow --process or "
                  "look up a specific name)")
        return 0

    if not args.name:
        sys.exit("ERROR: give a name to look up, or use --list / --process")

    exact = [(n, k, e) for n, k, e in items if n.lower() == args.name.lower()]

    if exact:
        for n, k, e in exact:
            print_entry(n, k, e, lines, kinds_overlay, options_overlay, crossref)
    else:
        names = sorted({n for n, _, _ in items})
        close = difflib.get_close_matches(args.name, names, n=5, cutoff=0.6)
        if not close:
            lines.append(f"No catalog entry for '{args.name}' in pack '{args.pack}', "
                          "and no near-miss spelling found.")
        else:
            lines.append(f"No exact catalog entry for '{args.name}'. Did you mean: "
                          + ", ".join(close) + "?")
            # If the near-miss spellings span more than one file kind (e.g. a history
            # name and a restart name that differ by one letter), say so explicitly --
            # picking just the closest one and printing it silently would repeat
            # exactly the SFCRNOFF/SFCRUNOFF trap this tool exists to prevent.
            close_kinds = {}
            for cn in close:
                for n, k, e in items:
                    if n == cn and k in ("output variable", "restart variable"):
                        close_kinds.setdefault(k, []).append(cn)
            if len(close_kinds) > 1:
                lines.append("  NOTE: these near-misses span more than one file kind -- "
                              + "; ".join(f"{k}: {', '.join(sorted(set(v)))}"
                                          for k, v in sorted(close_kinds.items())))
            n, k, e = next((n, k, e) for n, k, e in items if n == close[0])
            print_entry(n, k, e, lines, kinds_overlay, options_overlay, crossref)

    for line in lines[:MAX_LINES]:
        print(line)
    if len(lines) > MAX_LINES:
        print(f"... ({len(lines) - MAX_LINES} more lines truncated)")

    if args.json:
        print(json.dumps({"query": args.name, "exact_matches": [
            {"name": n, "kind": k, "entry": e} for n, k, e in exact]}, indent=2, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
