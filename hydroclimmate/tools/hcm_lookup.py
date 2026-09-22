#!/usr/bin/env python3
"""hcm_lookup.py -- answers a single-name lookup from a pack's generated catalogs
(references/models/<pack>/catalogs/*.yaml; see SCHEMA.md), across output variables,
restart variables, namelist keys, physics options, parameter-table entries, land-use/soil
class names, and physical constants. Where present, curated/kinds_overlay.yaml and
curated/options_overlay.yaml (hand-verified -- never generated) are merged in: an
overlay's `true_kind` is shown ahead of the generated `kind`, never silently replacing
it, plus any `sampling_note`/`units_note`/`gate`. An options_overlay row is merged into
every catalog entry it names -- by option name, by configuration-file key, and by each
name in its own `applies_to` list -- so a curated statement about an output variable or
a forcing type reaches the reader too, not only one about an option. The entry's own
`note` and a `populated: false` flag (a variable registered in the model's output
metadata but never written) are printed as well.

Kept separate from hcm_check.py's own `lookup` subcommand (which answers from the
generated catalogs/index.json -- see SCHEMA.md) so that tool's existing behavior is
untouched.

Exact match first; if none, a fuzzy "did you mean" against every catalog name (near-miss
spellings, e.g. one or two changed letters, are a known failure mode). Output is capped
at 25 printed lines.

--list kind=<true_kind> lists every curated/kinds_overlay.yaml row with that true_kind.
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
    """Load `catalogs/<stem>.yaml`, or `catalogs/<stem>.json`."""
    yaml_path = pack_dir / "catalogs" / f"{stem}.yaml"
    if yaml_path.is_file():
        return _miniyaml.load_file(yaml_path)
    json_path = pack_dir / "catalogs" / f"{stem}.json"
    return json.loads(json_path.read_text()) if json_path.is_file() else None


def _load_curated(pack_dir, stem):
    """Load `curated/<stem>.yaml`, the hand-maintained counterpart to `_load`."""
    yaml_path = pack_dir / "curated" / f"{stem}.yaml"
    return _miniyaml.load_file(yaml_path) if yaml_path.is_file() else None


def load_overlays(pack_dir):
    """curated/kinds_overlay.yaml rows indexed by variable name (upper-cased), and
    curated/options_overlay.yaml rows grouped by internal_option_name. Either file is
    optional; a pack with neither just gets no overlay merge."""
    kinds_by_var = {}
    kinds_doc = _load_curated(pack_dir, "kinds_overlay")
    if kinds_doc:
        for row in kinds_doc.get("rows", []):
            kinds_by_var[row["variable"].upper()] = row

    # Every other curated `*_overlay.yaml` the pack actually has is merged the same way,
    # by listing the directory rather than from a fixed stem list: a pack whose curated
    # judgement lives in an overlay of its own (named for what it holds, not for
    # `options`) would otherwise be unreachable from the tool its own prose routes the
    # reader to -- the exact failure `applies_to` exists to prevent, one level up.
    options_by_opt = {}
    curated_dir = pack_dir / "curated"
    stems = ["options_overlay"]
    if curated_dir.is_dir():
        stems += [p.stem for p in sorted(curated_dir.glob("*_overlay.yaml"))
                  if p.stem not in ("options_overlay", "kinds_overlay")]
    for stem in stems:
        doc = _load_curated(pack_dir, stem)
        if not doc:
            continue
        for row in doc.get("rows", []):
            for key in _overlay_row_keys(row):
                options_by_opt.setdefault(key, []).append(row)

    return kinds_by_var, options_by_opt


def _overlay_row_keys(row):
    """Every catalog name an options_overlay.yaml row is about, upper-cased: its
    `internal_option_name`, its `global_parameter_key`, and each name in its optional
    `applies_to` list (for a row about an output variable or a forcing type, which has
    no option field at all). Indexing by `internal_option_name` alone silently collapsed
    every row whose subject is not an option -- more than half of vic's rows -- into one
    `None` bucket that no lookup could ever reach, so the curated statement was invisible
    to the reader the pack routes to this tool. A key holding a `/`-joined pair (e.g.
    "SPATIAL_SNOW/SPATIAL_FROST") is indexed under each side as well as whole."""
    keys = set()
    # `subject` is the same idea under another overlay's own field name: one row about
    # one or several catalog entries, listed by name. Split on commas as well, so a row
    # whose subject names a family ("KWfloodVolume, MCfloodVolume, DWfloodVolume") is
    # reachable by each member, not only by the whole string.
    subject = row.get("subject")
    if isinstance(subject, str) and subject:
        keys.add(subject.upper())
        for part in subject.split(","):
            if part.strip():
                keys.add(part.strip().upper())
    for field in ("internal_option_name", "global_parameter_key"):
        val = row.get(field)
        if isinstance(val, str) and val:
            keys.add(val.upper())
            for part in val.split("/"):
                if part.strip():
                    keys.add(part.strip().upper())
    for name in row.get("applies_to") or []:
        if isinstance(name, str) and name:
            keys.add(name.upper())
    return keys


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
        overlay_rows = (options_overlay or {}).get(
            (entry.get("internal_option_name") or "").upper(), [])
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
    manifest_path = pack_dir / "pack.yaml"
    depth = _miniyaml.load_file(manifest_path).get("depth", "outline") if manifest_path.is_file() else "outline"
    if depth != "reference":
        sys.exit("outline pack: no machine-readable declarations. "
                  "hcm_lookup.py only applies to a depth: reference pack.")
    if not (pack_dir / "catalogs").is_dir():
        sys.exit(f"No catalogs/ directory for pack '{args.pack}'. "
                  f"Build one with tools/extract_pack.py all --source-root ROOT "
                  f"--out-dir {pack_dir}/catalogs")

    generic = args.pack != "hrldas-noahmp"
    kinds_overlay, options_overlay = load_overlays(pack_dir)
    items = collect_index_generic(pack_dir) if generic else collect_index(pack_dir)
    crossref = {} if generic else history_restart_crossref(pack_dir)
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
        # Generic pack: every entry kind its own catalogs declare, minus the enum-value
        # aliases (a value of a key, listed under its parent's entry, is not a second
        # subject to list here).
        processable = (("output variable", "restart variable") if not generic else
                       tuple({k for _n, k, _e in items if "(enum value of" not in k}))
        for n, k, e in items:
            if k not in processable and not k.startswith("physics option"):
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
            if generic:
                print_entry_generic(n, k, e, lines, all_matches_for_name=exact,
                                    options_overlay=options_overlay)
            else:
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
                    # Every entry kind the pack's own catalogs declare, not a fixed list:
                    # a near-miss pair spanning a history name and a restart name matters
                    # in exactly the same way as one spanning a control key and a
                    # parameter, and which kinds exist is the pack's own business.
                    if n == cn and "(enum value of" not in k:
                        close_kinds.setdefault(k, []).append(cn)
            if len(close_kinds) > 1:
                lines.append("  NOTE: these near-misses span more than one file kind -- "
                              + "; ".join(f"{k}: {', '.join(sorted(set(v)))}"
                                          for k, v in sorted(close_kinds.items())))
            n, k, e = next((n, k, e) for n, k, e in items if n == close[0])
            if generic:
                print_entry_generic(n, k, e, lines, options_overlay=options_overlay)
            else:
                print_entry(n, k, e, lines, kinds_overlay, options_overlay, crossref)

    for line in lines[:MAX_LINES]:
        print(line)
    if len(lines) > MAX_LINES:
        print(f"... ({len(lines) - MAX_LINES} more lines truncated)")

    if args.json:
        print(json.dumps({"query": args.name, "exact_matches": [
            {"name": n, "kind": k, "entry": e} for n, k, e in exact]}, indent=2, default=str))
    return 0


# --------------------------------------------------------------------------------------
# Generic path for a non-hrldas-noahmp `depth: reference` pack (currently: vic,
# mizuroute). Reads whatever catalogs/*.yaml files the pack actually has -- nothing here
# is hrldas-, noahmp-, vic- or mizuroute-specific -- taking each catalog's main list key
# and entry-kind label from the catalog file itself where it states them, else from the
# fallback table below. The printer shows whichever of the known descriptive fields an
# entry carries (units/description, kind, requiredness, allowed values, the control keys
# that switch a variable on, the routing methods that produce it, ...), plus driver
# (classic|image|both) where a pack has drivers, plus a warning when a name's matches all
# share one non-"both" driver.
# --------------------------------------------------------------------------------------

_GENERIC_KIND_LABEL = {
    "outputs": "vic output variable",
    "global_parameters": "vic global parameter key",
    "options": "vic option",
    "constants": "vic physical constant",
    "model_parameters": "vic model parameter key",
    "forcing": "vic forcing type",
    "state": "vic state variable",
}
_GENERIC_LIST_KEY = {
    "outputs": "variables", "global_parameters": "keys", "options": "options",
    "constants": "constants", "model_parameters": "keys", "forcing": "types",
    "state": "variables",
}


def _generic_catalog_keys(pack_dir):
    """(stem -> main list key, stem -> entry-kind label) for every catalog this pack
    actually has. A catalog may name its own two answers in the file itself
    (`entries_key`/`entry_kind`, written by its generator); one that does not falls back
    on the table above. Nothing here is pack-specific either way: without this, a pack
    whose catalog stems are not in that table resolves nothing at all, and a pack that
    happens to share a stem name with another one is labelled with that other pack's
    vocabulary."""
    stems = dict(_GENERIC_LIST_KEY)
    labels = dict(_GENERIC_KIND_LABEL)
    cat_dir = pack_dir / "catalogs"
    if cat_dir.is_dir():
        for path in sorted(cat_dir.glob("*.yaml")):
            doc = _load(pack_dir, path.stem)
            if doc and doc.get("entries_key"):
                stems[path.stem] = doc["entries_key"]
                labels[path.stem] = doc.get("entry_kind") or path.stem
    return stems, labels


def collect_index_generic(pack_dir):
    """Every catalogs/*.yaml entry for a pack that is not hrldas-noahmp, indexed
    generically: file stem -> its documented main list key (SCHEMA.md's
    `<catalog-specific list key>`), one item per list entry, keyed by whichever of
    name/key/internal_option_name/variable/column/nc_variable it carries. Also indexes
    catalogs/parameters.yaml's several named sub-lists (it has no single list key) and
    global_parameters.yaml/model_parameters.yaml's `constraints` (unnamed, so listed
    under --process only, not by single-name lookup)."""
    items = []
    stems, labels = _generic_catalog_keys(pack_dir)
    for stem, list_key in stems.items():
        doc = _load(pack_dir, stem)
        if not doc:
            continue
        kind_label = labels[stem]
        for item in doc.get(list_key, []):
            if not isinstance(item, dict):
                continue
            name = (item.get("name") or item.get("key") or item.get("setting")
                    or item.get("internal_option_name"))
            if name:
                items.append((name, kind_label, item))
            # A key's own enumerated allowed_values (e.g. BASEFLOW's ARNO/NIJSSEN2001)
            # are themselves real identifiers a reader may look up by name -- alias each
            # one to the parent key's entry rather than leaving it only reachable as a
            # value buried inside that entry's own allowed_values list.
            for av in (item.get("allowed_values") or []):
                v = av.get("value")
                # A boolean literal is a value of dozens of keys, not a name of any one
                # of them: aliasing it would answer a lookup for TRUE with whichever
                # boolean key happened to be collected first, which reads as an answer
                # and is not one.
                if v and v.upper() in ("TRUE", "FALSE"):
                    continue
                if v and re.match(r"^[A-Za-z_]\w*$", v):
                    items.append((v, f"{kind_label} (enum value of {name})", item))

    outputs = _load(pack_dir, "outputs")
    if outputs:
        # The aggregation-method constants are the vocabulary of an output entry's own
        # `default_agg_type` and of an OUTVAR line's fourth token, so a reader meets
        # them before any variable name; they live in their own catalog list rather
        # than as a variable, and would otherwise resolve to nothing.
        for item in outputs.get("agg_types", []):
            if item.get("name"):
                items.append((item["name"], "vic output aggregation method", item))

    params = _load(pack_dir, "parameters")
    if params:
        for item in params.get("classic_soil_columns", []):
            if item.get("column"):
                items.append((item["column"], "vic classic soil-file column", item))
        for item in params.get("image_netcdf_parameters", []):
            if item.get("nc_variable"):
                items.append((item["nc_variable"], "vic image NetCDF parameter variable", item))
    return items


def _fmt_value(v):
    """One printable line for a catalog field: a list of scalars joined by commas, a list
    of small records (e.g. a `forced_by_code` row: what the code forces the value to, and
    under which condition) as `value <- condition`, anything else as itself. A raw Python
    repr of a nested record is technically complete and practically unreadable, which is
    how a decisive field gets skipped by the reader it was printed for."""
    if isinstance(v, list) and v and all(not isinstance(i, (dict, list)) for i in v):
        return ", ".join(str(i) for i in v)
    if isinstance(v, list) and v and all(isinstance(i, dict) for i in v):
        parts = []
        for row in v[:3]:
            rest = {k: val for k, val in row.items() if k not in ("where", "evidence", "scope")}
            head = rest.pop("forced_to", None)
            cond = rest.pop("condition", None)
            if head is not None or cond is not None:
                parts.append(f"{head} <- {cond}")
            else:
                parts.append("; ".join(f"{k}={val}" for k, val in rest.items()))
        return " | ".join(parts) + (" ..." if len(v) > 3 else "")
    return str(v)


def _driver_of(entry):
    w = entry.get("where") or {}
    return w.get("driver")


def print_entry_generic(name, kind, entry, lines, all_matches_for_name=None,
                        options_overlay=None):
    canon = (entry.get("name") or entry.get("key") or entry.get("setting")
              or entry.get("internal_option_name") or name)
    header = f"# {canon}  [{kind}]"
    if canon.upper() != name.upper():
        header += f"  (matched via alias '{name}')"
    lines.append(header)

    for key, label in (
        ("long_name", "long_name"), ("standard_name", "standard_name"),
        ("units", "units"), ("description", "description"),
        ("meaning", "meaning"), ("statement", "statement"),
        # The fields that carry a pack's own judgement about an entry: what the written
        # value means over an output interval, whether the configuration file must set
        # the key, which switches turn a variable on, which methods produce it, and where
        # the code overrides the file. Printing name/units/where but not these would show
        # the least decisive part of the entry and stop at the 25-line cap.
        ("kind", "value over the output interval (kind)"),
        ("requiredness", "requiredness"),
        ("conditionally_required", "required when"),
        ("control_keys", "switched on by control key"),
        ("forced_by_code", "forced by code"),
        ("produced_by_methods", "produced by routing method"),
        ("history_buffer", "history buffer"),
        ("belongs_to", "belongs to"),
        ("route_opt_digit", "route_opt digit"),
        ("implementing_module", "implementing module"),
        ("parameter_kind", "parameter kind"), ("namelist_group", "namelist group"),
        ("section_in_parser", "section in the parser"),
        ("assigns_to", "assigns to"),
        ("rename_key", "renamed by control key"),
        ("read_by_default", "read by default"),
        ("default_write", "written by default"),
        ("written_by_default", "written by default"),
        ("dimension", "dimension"), ("dimensions", "dimensions"),
        ("netcdf_type", "NetCDF type"),
        ("fortran_type", "Fortran type"),
        ("default_literal", "default (in code)"),
        ("value_literal", "value (in code)"),
        ("shipped_value", "shipped value"),
        ("used_in_sample_control_files", "used in sample control file(s)"),
        ("header_comment", "header comment (enum, informal)"),
        ("default_agg_type", "default aggregation type (kind)"),
        ("nelem_expr", "nelem (per-band/per-layer count expression)"),
        ("registered_in_default_stream", "default output stream"),
        ("type", "type"), ("sscanf_format", "sscanf format"),
        ("default_in_code", "default (in code)"),
        ("c_type", "C type"), ("comment_first_line", "comment"),
        ("value", "value"), ("comment", "comment"),
        ("assigned_field", "assigned struct field"),
        ("documented_in_docs", "documented in docs/"),
        ("enum_const", "forcing enum constant"),
        ("file_format", "file format (classic vs image)"),
        ("gate", "gate"), ("per_layer", "per soil layer"),
        ("internal_field", "internal struct field (image)"),
        ("read_scale", "conversion applied on read"),
        ("read_note", "read note"),
        ("removed_since_vic4_message", "REMOVED SINCE VIC 4"),
    ):
        v = entry.get(key)
        if v not in (None, "", []):
            lines.append(f"  {label}: {_fmt_value(v)}")
    # An entry's own `populated`/`note` are the catalog's record of a variable that is
    # registered but never written, or of a metadata defect in the source; printing them
    # last would risk the 25-line cap dropping exactly the line that says the number is
    # not real, so they come immediately after the descriptive fields.
    if entry.get("populated") is False:
        lines.append("  NOT POPULATED: registered in the output metadata table but "
                      "never assigned in put_data.c -- always its zero-initialized value")
    if entry.get("note"):
        lines.append(f"  note: {entry['note']}")
    for row in (entry.get("allowed_values") or [])[:3]:
        # Two catalog shapes for the same idea: one value per row (`value`, with the
        # struct field it assigns), or one row per constrained variable holding several
        # accepted spellings (`values`, with the parser's own rejection message). Both
        # are printed; a row of neither shape is skipped rather than printed as "None".
        if row.get("value") is not None:
            vals = ", ".join(f"{a.get('value')}" + (f" ({a.get('assigns')})" if a.get("assigns") else "")
                              for a in entry["allowed_values"][:6])
            lines.append(f"  allowed_values: {vals}"
                          + (" ..." if len(entry["allowed_values"]) > 6 else ""))
            break
        if isinstance(row.get("values"), list):
            accepted = [v for group in row["values"] for v in (group.get("values") or [])]
            label = row.get("variable") or canon
            lines.append(f"  allowed values of {label}: {', '.join(accepted)}")
            if row.get("rejection_message"):
                lines.append(f"    else rejected: {row['rejection_message']}")
            if row.get("note"):
                lines.append(f"    note: {row['note']}")
    if entry.get("registration_gate") or entry.get("nelem_gate"):
        g = entry.get("registration_gate") or entry.get("nelem_gate")
        lines.append(f"  gate: {g}")
    if entry.get("vic_run_branch_count") is not None:
        lines.append(f"  vic_run branch references: {entry['vic_run_branch_count']}"
                      + (" (0 -- likely I/O-only or consumed indirectly, not a direct "
                         "physics-code test; see catalogs/options.yaml's own note)"
                         if entry["vic_run_branch_count"] == 0 else ""))
        for c in (entry.get("vic_run_branch_citations") or [])[:3]:
            lines.append(f"    e.g. {c['where']['file']}:{c['where']['line']}: {c.get('text', '')}")
    where = entry.get("where")
    driver = _driver_of(entry)
    if where:
        # `runmode` is this pack's fourth `where` key (standalone/coupled/both): a fact
        # printed without it reads as unconditional when it may hold in one run mode only.
        runmode = where.get("runmode")
        lines.append(f"  where: {where.get('file')}:{where.get('line')} ({where.get('commit')})"
                      + (f"  [driver: {driver}]" if driver else "")
                      + (f"  [runmode: {runmode}]" if runmode else ""))
    if entry.get("evidence"):
        lines.append(f"  evidence: {entry['evidence']}")

    for orow in (options_overlay or {}).get(canon.upper(), [])[:3]:
        lines.append(f"  CURATED OVERLAY ({orow.get('kind')}): {orow['note']}")
        lines.append(f"  overlay evidence: "
                      f"{orow['where']['file']}:{orow['where']['line']} "
                      f"({orow['where']['commit']}) -- {orow.get('evidence')}")
        if orow.get("code_where"):
            cw = orow["code_where"]
            lines.append(f"  overlay: the code that wins: {cw['file']}:{cw['line']}")

    if all_matches_for_name:
        drivers = {_driver_of(e) for _, _, e in all_matches_for_name}
        drivers.discard(None)
        if drivers and drivers != {"both"} and "both" not in drivers and len(drivers) == 1:
            only = next(iter(drivers))
            lines.append(f"  NOTE: only found for driver={only} -- no matching entry for "
                          f"the other driver under this exact name (may be driver-specific, "
                          f"or spelled differently there; check catalogs/global_parameters.yaml "
                          f"for the other driver's own key list).")


if __name__ == "__main__":
    sys.exit(main())
