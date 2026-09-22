"""Offline structural checks and independent arithmetic cases; no model execution.

Pass --network to additionally verify that every cited external URL still resolves.
That check is opt-in so the default run stays offline and deterministic.

Pass a pinned source checkout for a depth: reference pack (see
references/models/SCHEMA.md) to additionally, for that pack: resolve every `path:line`
citation in its prose against that source tree's actual line counts, and assert that
regenerating its catalogs with tools/extract_pack.py from that root reproduces the
committed catalogs structurally (modulo `evidence: source_read` vs `both`, which only
validate_catalogs.py against real output/restart/forcing files -- not available here --
can upgrade). These checks are skipped cleanly, with a note, for a pack whose root is
not given. Any pack:

    --source-root <pack>=<checkout>          e.g. --source-root mizuroute=/path/to/mizuRoute

and the original forms still mean what they did: a bare --source-root <checkout> is the
HRLDAS+noahmp checkout, and --<pack>-source-root <checkout> (e.g. --vic-source-root)
names one pack too.
"""
import json
import re
import sys
from datetime import date
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "hydroclimmate"
EVALS_DIR = ROOT / "evals"
# Source packs cite floating branch URLs, so they rot silently. Re-check by this age.
STALE_DAYS = 180

BASIS_VALUES = {"source_read", "observed_in_output", "both", "unverified"}
# A depth: outline pack is prose only (pack.yaml + its 5 .md files); only a depth:
# reference pack carries curated/ (hand-authored) and catalogs/ (generated). See
# references/models/SCHEMA.md.
DEPTH_VALUES = ("reference", "outline")

REFERENCE_MD_FILES = {"card.md", "processes.md", "failures.md", "recipes.md", "version.md",
                       "sources.md"}
OUTLINE_MD_FILES = {"overview.md", "execution.md", "outputs.md", "pitfalls.md", "sources.md"}
REFERENCE_SIZE_CAPS = {"card.md": 4096, "processes.md": 12288, "failures.md": 14336,
                        "recipes.md": 10240, "version.md": 3072}
# README.md is a new, optional top-level file for a depth: reference pack (human-facing
# entry point; see pack.yaml's own `prose` purpose for it) -- not one of the six
# must-read-by-an-agent REFERENCE_MD_FILES, so it is not required for a pack to count as
# "prose complete", but it IS capped and it must never be routed to from models/index.md
# or core.md (agents are not routed to it; a person finds it by browsing the pack
# directory). Tracked separately so a pack missing only README.md still reports as
# pending-for-that-reason rather than silently invisible.
README_SIZE_CAP = 5120

# `path:line` citation resolution (depth: reference prose only; see check_source_citations).
CITATION_RE = re.compile(r"\b([\w./]+):(\d+(?:-\d+)?(?:,\d+(?:-\d+)?)*)\b")
CITATION_SHORTHAND_FILE = {
    "drv": "hrldas/IO_code/module_NoahMP_hrldas_driver.F",
    "io": "hrldas/IO_code/module_hrldas_netcdf_io.F",
    "nml": "hrldas/run/README.namelist",
    "TBL": "noahmp/parameters/NoahmpTable.TBL",
}
CITATION_SHORTHAND_DIR = {"src": "noahmp/src", "hdrv": "noahmp/drivers/hrldas"}
# This pack's own build path (pack.yaml version_scope) -- used to disambiguate a bare
# filename (no directory) that exists under more than one noahmp/drivers/* variant.
CITATION_PREFERRED_DIR_HINT = "drivers/hrldas"

sys.path.insert(0, str(PACKAGE / "tools"))
sys.path.insert(0, str(EVALS_DIR))
import _miniyaml  # noqa: E402
import _anchor_hash  # noqa: E402


def _load_layer_file(path):
    """Load a pack layer file: YAML (via _miniyaml, which itself prefers PyYAML -- see
    tools/_miniyaml.py) for .yaml, plain json for .json."""
    if path.suffix == ".yaml":
        return _miniyaml.load_file(path)
    return json.loads(path.read_text())


def _hcm_check_subcommands():
    """Subcommand names hcm_check.py actually defines, read from its own source so this
    validator cannot drift from the tool it is checking against."""
    text = (PACKAGE / "tools/hcm_check.py").read_text()
    return set(re.findall(r'sub\.add_parser\(\s*"([a-z-]+)"', text))


def _iter_facts(node, path=""):
    """Yield (path, fact-dict) for every dict in a structured-layer JSON document that
    carries the four required keys, at any nesting depth."""
    if isinstance(node, dict):
        if {"source", "scope", "basis", "from"} <= node.keys():
            yield path, node
        for key, value in node.items():
            yield from _iter_facts(value, f"{path}.{key}" if path else key)
    elif isinstance(node, list):
        for i, item in enumerate(node):
            yield from _iter_facts(item, f"{path}[{i}]")


def _iter_facts_with_from(node, path=""):
    """Yield (path, fact-dict) for every dict carrying a `from: {file, anchor}` prose
    pointer, whichever curated citation shape the rest of the dict uses -- the same rule
    tools/refresh_confirmed_against.py applies, so the guard and the refresh tool cover
    exactly the same facts."""
    if isinstance(node, dict):
        frm = node.get("from")
        if isinstance(frm, dict) and "anchor" in frm and "file" in frm:
            yield path, node
        for key, value in node.items():
            yield from _iter_facts_with_from(value, f"{path}.{key}" if path else key)
    elif isinstance(node, list):
        for i, item in enumerate(node):
            yield from _iter_facts_with_from(item, f"{path}[{i}]")


def _pack_manifest_path(folder):
    """A pack's manifest is always pack.yaml; see SCHEMA.md."""
    return folder / "pack.yaml"


MAX_PURPOSE_WORDS = 12


def _check_purpose(model, filename, purpose):
    assert isinstance(purpose, str) and purpose, (model, filename, "purpose must be a non-empty string")
    n_words = len(purpose.split())
    assert n_words <= MAX_PURPOSE_WORDS, (
        model, filename, f"purpose is {n_words} words, over the {MAX_PURPOSE_WORDS}-word cap", purpose)


def check_structured_layers(model, folder, valid_source_ids, valid_checks):
    """Validate a pack's manifest and, for a depth: reference pack, its curated layers
    and generated catalogs (see SCHEMA.md). Returns the number of facts found, for the
    caller's summary line."""
    manifest_path = _pack_manifest_path(folder)
    assert manifest_path.is_file(), (model, "pack.yaml is required but missing")

    try:
        manifest = _load_layer_file(manifest_path)
    except (json.JSONDecodeError, _miniyaml.MiniYamlError) as exc:
        raise AssertionError((model, manifest_path.name, "does not parse", str(exc))) from exc

    depth = manifest.get("depth")
    assert depth in DEPTH_VALUES, (model, "manifest depth must be one of", DEPTH_VALUES, depth)
    assert manifest.get("pack") == model, (model, "manifest 'pack' does not match the directory name")
    assert manifest.get("title"), (model, "manifest is missing 'title'")
    assert manifest.get("version_scope"), (model, "manifest is missing 'version_scope'")

    prose = manifest.get("prose", [])
    assert prose, (model, "manifest is missing 'prose'")
    for entry in prose:
        filename = entry.get("file")
        assert filename and (folder / filename).is_file(), (model, "prose entry names a missing file", filename)
        _check_purpose(model, filename, entry.get("purpose"))

    if depth == "outline":
        assert not (folder / "curated").is_dir(), (
            model, "depth: outline pack must not carry a curated/ directory")
        assert not (folder / "catalogs").is_dir(), (
            model, "depth: outline pack must not carry a catalogs/ directory")
        for key in ("curated", "catalogs", "known_gaps"):
            assert key not in manifest, (model, f"depth: outline pack's manifest must not declare '{key}'")
        return 0

    # depth: reference.
    catalogs_info = manifest.get("catalogs")
    assert isinstance(catalogs_info, dict) and catalogs_info.get("generated_from") and \
        catalogs_info.get("regenerate") and catalogs_info.get("validate"), (
        model, "depth: reference manifest needs catalogs: {generated_from, regenerate, validate}")

    curated = manifest.get("curated", [])
    assert curated, (model, "depth: reference manifest is missing 'curated'")
    fact_count = 0
    for entry in curated:
        filename = entry.get("file")
        assert filename and (folder / filename).is_file(), (model, "curated entry names a missing file", filename)
        _check_purpose(model, filename, entry.get("purpose"))
        try:
            doc = _load_layer_file(folder / filename)
        except (json.JSONDecodeError, _miniyaml.MiniYamlError) as exc:
            raise AssertionError((model, filename, "does not parse", str(exc))) from exc

        for fact_path, fact in _iter_facts(doc):
            fact_count += 1
            assert fact["basis"] in BASIS_VALUES, (model, filename, fact_path, "bad basis", fact["basis"])
            if fact["source"] is not None:
                assert fact["source"] in valid_source_ids, (
                    model, filename, fact_path, "source id not in sources.md", fact["source"])
            frm = fact["from"]
            assert isinstance(frm, dict) and "file" in frm and "anchor" in frm, (
                model, filename, fact_path, "'from' must be {file, anchor}")
            from_file = folder / frm["file"]
            assert from_file.is_file(), (model, filename, fact_path, "'from' file missing", frm["file"])
            assert frm["anchor"] in anchors(from_file.read_text()), (
                model, filename, fact_path, "'from' anchor not found", frm["anchor"], frm["file"])

        if Path(filename).name == "checks.yaml":
            check_checks_yaml(model, folder, doc, valid_checks)

    for gap in manifest.get("known_gaps", []):
        assert isinstance(gap, str) and gap, (model, "known_gaps entries must be non-empty strings")

    index_path = folder / "catalogs" / "index.json"
    assert index_path.is_file(), (model, "depth: reference pack is missing catalogs/index.json")
    check_index_matches_build(model, folder, json.loads(index_path.read_text()))

    check_catalog_evidence(model, folder)

    return fact_count


def check_index_matches_build(model, folder, committed_index):
    """index.json is generated, never hand-written (Addendum 2): it must equal a fresh
    build from the pack's other layers, so it can never drift or carry its own claims."""
    import build_index
    fresh = build_index.build_index_for_pack(folder)
    assert fresh == committed_index, (
        model, "index.json does not match a fresh build -- regenerate with "
        "tools/build_index.py <pack> --write instead of hand-editing")


# Packs whose pinned checkout carries no model output at all, so no catalog entry of
# theirs may ever be graded against output (each one says so in its own pack.yaml
# known_gaps; this is the machine-checked half of that statement).
NO_REACHABLE_OUTPUT_PACKS = {"vic", "mizuroute"}


def _iter_catalog_entries(node, inside_fact=False):
    """Yield (dict, inside_fact) for every dict in a generated catalog document that
    carries a 'where' key, at any nesting depth -- catalogs/*.yaml can nest a record's
    own sub-records (e.g. a parameter-table group's `parameters`, a physics option's
    `values`). `inside_fact` is True when some enclosing dict already carries an
    `evidence` grade, which makes this `where` one more citation belonging to that graded
    fact (e.g. the line where a variable is forced off, or where a method's parameter is
    named) rather than an ungraded fact of its own."""
    if isinstance(node, dict):
        if "where" in node:
            yield node, inside_fact
        deeper = inside_fact or "evidence" in node
        for value in node.values():
            yield from _iter_catalog_entries(value, deeper)
    elif isinstance(node, list):
        for item in node:
            yield from _iter_catalog_entries(item, inside_fact)


def check_catalog_evidence(model, folder):
    """depth: reference (SCHEMA.md): every generated catalog entry (anything carrying a
    `where` fact-location) must also carry an `evidence` grade -- the two are meant to
    travel together, and extract_pack.py never emits one without the other. A `where`
    nested inside a record that is already graded is one more citation of that same fact,
    not a second fact: it is checked for shape, and its grade is the enclosing record's.
    An ungraded `where` at the top of a record is still a failure, which is the case this
    check exists for."""
    catalogs_dir = folder / "catalogs"
    assert catalogs_dir.is_dir(), (model, "depth: reference but no catalogs/ directory")
    yaml_files = sorted(catalogs_dir.glob("*.yaml"))
    assert yaml_files, (model, "depth: reference but catalogs/ has no *.yaml files")
    n_entries = 0
    for path in yaml_files:
        doc = _miniyaml.load_file(path)
        for entry, inside_fact in _iter_catalog_entries(doc):
            n_entries += 1
            where = entry["where"]
            assert isinstance(where, dict) and {"file", "line", "commit"} <= where.keys(), (
                model, path.name, "where must be {file, line, commit}", where)
            if inside_fact and "evidence" not in entry:
                continue
            assert entry.get("evidence") in (
                "source_read", "observed_in_output", "both", "confirmed_in_sample_input"), (
                model, path.name, "entry with 'where' is missing a valid 'evidence'", entry.get("name"))
            if entry.get("evidence") in ("observed_in_output", "both"):
                assert model not in NO_REACHABLE_OUTPUT_PACKS, (
                    model, path.name, "no model output for this pack exists anywhere reachable "
                    "from this repository (see its pack.yaml known_gaps) -- its catalog entries "
                    "may never claim observed_in_output/both", entry.get("name"))
    assert n_entries > 0, (model, "catalogs/*.yaml carry no where-tagged entries at all")


# Per-pack citation shorthand: each depth: reference pack's own prose states its own
# shorthand scheme in its own words (see e.g. vic/processes.md's opening line); this
# table only needs to match that stated scheme, not invent one.
PACK_CITATION_SHORTHAND_DIR = {
    "hrldas-noahmp": CITATION_SHORTHAND_DIR,
    "vic": {
        "run": "vic/vic_run/src", "sh": "vic/drivers/shared_all/src",
        "cl": "vic/drivers/classic/src", "im": "vic/drivers/image/src",
        "shim": "vic/drivers/shared_image/src",
    },
    "mizuroute": {"src": "route/build/src", "sa": "route/build/src/standalone"},
}
PACK_CITATION_SHORTHAND_FILE = {
    "hrldas-noahmp": CITATION_SHORTHAND_FILE,
    "vic": {},
    "mizuroute": {"ctl": "route/settings/SAMPLE.control"},
}
PACK_CITATION_PREFERRED_DIR_HINT = {
    "hrldas-noahmp": CITATION_PREFERRED_DIR_HINT,
    "vic": "",
    "mizuroute": "",
}
# A pack whose prose cites a source file by bare module stem, with no directory and no
# extension (`read_control:100-118`), states here where such a stem lives and what it is
# called on disk. Without it every one of those citations lands in the "unresolved
# prefix" note, which reports the count and checks nothing -- the prose form the pack
# uses most would be the one form the line-range check never sees.
PACK_CITATION_BARE_STEM = {
    "mizuroute": ("route/build/src", ".f90"),
}
# A bare filename (no directory) is resolved by a basename search when it carries one of
# these extensions -- the suffixes the three packs' prose actually cites.
CITATION_BARE_FILE_EXTS = (".F90", ".F", ".TBL", ".c", ".h", ".f90", ".rst", ".control")
_CITATION_RGLOB_CACHE = {}


def _citation_resolve(prefix, source_root, model="hrldas-noahmp"):
    """Resolve a citation prefix (e.g. 'drv', 'src/SurfaceAlbedoMod.F90',
    'NoahmpIOVarInitMod.F90', 'hrldas/run/README.namelist') to a path relative to
    `source_root`, or None if it cannot be resolved. A bare filename (no directory) is
    resolved by a basename search, preferring a hit under this pack's own build path
    (CITATION_PREFERRED_DIR_HINT) when more than one driver variant defines the same
    module name -- exactly the ambiguity this pack's own prose warns about
    (version.md: "Two urban drivers exist in this tree"). The shorthand table itself is
    per-pack (PACK_CITATION_SHORTHAND_DIR/_FILE), since each depth: reference pack's
    prose states its own scheme."""
    shorthand_file = PACK_CITATION_SHORTHAND_FILE.get(model, {})
    shorthand_dir = PACK_CITATION_SHORTHAND_DIR.get(model, {})
    preferred_hint = PACK_CITATION_PREFERRED_DIR_HINT.get(model, "")
    bare_dir, bare_ext = PACK_CITATION_BARE_STEM.get(model, (None, None))
    if prefix in shorthand_file:
        return shorthand_file[prefix]
    for key, expansion in shorthand_dir.items():
        if prefix == key:
            return None
        if prefix.startswith(key + "/"):
            expanded = expansion + prefix[len(key):]
            # A shorthand directory plus a bare module stem (`sa/model_setup`) is the
            # same citation form as the bare stem below, one directory down.
            if bare_ext and "." not in Path(expanded).name:
                expanded += bare_ext
            return expanded
    if "/" in prefix:
        return prefix
    if bare_dir and "." not in prefix and (source_root / bare_dir / (prefix + bare_ext)).is_file():
        return f"{bare_dir}/{prefix}{bare_ext}"
    if prefix.endswith(CITATION_BARE_FILE_EXTS):
        cache_key = (str(source_root), prefix)
        if cache_key not in _CITATION_RGLOB_CACHE:
            _CITATION_RGLOB_CACHE[cache_key] = [
                h for h in source_root.rglob(prefix) if ".git" not in h.parts]
        hits = _CITATION_RGLOB_CACHE[cache_key]
        if len(hits) > 1 and preferred_hint:
            preferred = [h for h in hits if preferred_hint in str(h)]
            if len(preferred) == 1:
                hits = preferred
        if len(hits) == 1:
            return str(hits[0].relative_to(source_root))
    return None


def _resolve_and_check_citation(model, folder_label, source_root, where, context):
    """Assert `where` = {file, line, commit} resolves to an existing file under
    source_root whose line count is at least `line`. `where["file"]` in this pack's
    catalogs is already a real path relative to source_root (not a prose shorthand), so
    this is a direct check, not the prefix-resolution check_source_citations needs."""
    fpath = source_root / where["file"]
    assert fpath.is_file(), (model, folder_label, context, "citation file does not exist",
                              where["file"])
    n_lines = sum(1 for _ in open(fpath, encoding="utf-8", errors="replace"))
    assert where["line"] <= n_lines, (
        model, folder_label, context, "citation line past end of file",
        where["file"], where["line"], "has", n_lines, "lines")


def check_overlay_catalogs(model, folder, source_root):
    """curated/kinds_overlay.yaml and curated/options_overlay.yaml are curated,
    hand-verified, never generated (see SCHEMA.md). Every row's subject must actually
    exist in the corresponding generated catalog (checked always -- cheap, no source
    tree needed), and every citation (`where`, `reset_where`) must resolve to a real
    file and an in-range line when --source-root is given (skipped cleanly otherwise)."""
    catalogs_dir = folder / "catalogs"
    curated_dir = folder / "curated"
    n_checked = 0

    kinds_path = curated_dir / "kinds_overlay.yaml"
    if kinds_path.is_file():
        outputs_doc = _miniyaml.load_file(catalogs_dir / "outputs.yaml")
        output_names = {v["name"] for v in outputs_doc["variables"]}
        for row in _miniyaml.load_file(kinds_path).get("rows", []):
            n_checked += 1
            assert row["variable"] in output_names, (
                model, "curated/kinds_overlay.yaml", "variable not in catalogs/outputs.yaml",
                row["variable"])
            if source_root is not None:
                _resolve_and_check_citation(model, "curated/kinds_overlay.yaml", source_root,
                                             row["where"], row["variable"])
                if row.get("reset_where"):
                    _resolve_and_check_citation(model, "curated/kinds_overlay.yaml", source_root,
                                                 row["reset_where"], row["variable"] + " (reset)")

    options_path = curated_dir / "options_overlay.yaml"
    if options_path.is_file():
        # The generated catalog this overlay cross-checks against, and the field naming
        # the option's own identity, differ per pack (hrldas-noahmp: physics_options.yaml
        # / internal_option_name; vic: options.yaml / name) -- everything else about the
        # check (every overlay row's subject must exist in that catalog) is pack-agnostic.
        options_catalog_name, option_name_field = {
            "vic": ("options.yaml", "name"),
        }.get(model, ("physics_options.yaml", "internal_option_name"))
        physics_doc = _miniyaml.load_file(catalogs_dir / options_catalog_name)
        option_names = {o[option_name_field] for o in physics_doc["options"]}
        for row in _miniyaml.load_file(options_path).get("rows", []):
            n_checked += 1
            # internal_option_name: null is itself a documented fact for a row whose
            # whole point is that no corresponding option-struct field exists (e.g.
            # vic's OUTPUT_FORCE row: a global-parameter key rejected by one driver and
            # absent from the other's parser, at this commit) -- not an omitted value.
            if row["internal_option_name"] is not None:
                assert row["internal_option_name"] in option_names, (
                    model, "curated/options_overlay.yaml", f"internal_option_name not in "
                    f"catalogs/{options_catalog_name}", row["internal_option_name"])
            # `applies_to` is how a row whose subject is an output variable or a forcing
            # type -- and so has no option-struct field to be named by -- reaches
            # tools/hcm_lookup.py. A name that matches nothing makes the row silently
            # unreachable again, which is the exact failure this field exists to end, so
            # every name must resolve in one of the pack's own generated catalogs.
            for name in row.get("applies_to") or []:
                assert name in _catalog_names(catalogs_dir), (
                    model, "curated/options_overlay.yaml",
                    "applies_to names nothing in catalogs/", name)
            if source_root is not None and row.get("where"):
                _resolve_and_check_citation(model, "curated/options_overlay.yaml", source_root,
                                             row["where"], row["internal_option_name"])

    # Any other curated row-shaped overlay the pack has, found by listing the directory:
    # its rows carry the same `where` citation shape, and a citation nobody resolves is
    # exactly the kind of quiet decay this check exists to prevent. The subject-exists
    # check above stays specific to the two overlays whose subject field is defined by
    # SCHEMA.md; what is generic here is the citation resolution.
    for path in sorted(curated_dir.glob("*_overlay.yaml")) if curated_dir.is_dir() else []:
        if path.name in ("kinds_overlay.yaml", "options_overlay.yaml"):
            continue
        for i, row in enumerate(_miniyaml.load_file(path).get("rows", [])):
            n_checked += 1
            label = row.get("subject") or f"rows[{i}]"
            if source_root is None:
                continue
            for field in ("where", "code_where"):
                if row.get(field):
                    _resolve_and_check_citation(model, f"curated/{path.name}", source_root,
                                                 row[field], f"{label} ({field})")
    return n_checked


_CATALOG_NAME_KEYS = ("variables", "keys", "options", "constants", "types",
                       "classic_soil_columns", "image_netcdf_parameters", "agg_types")


_CATALOG_NAMES_CACHE = {}


def _catalog_names(catalogs_dir):
    """Every entry name in every generated catalog of a pack, across each catalog's own
    main list key -- the set a curated row's `applies_to` must name from."""
    key = str(catalogs_dir)
    if key in _CATALOG_NAMES_CACHE:
        return _CATALOG_NAMES_CACHE[key]
    names = set()
    for path in sorted(catalogs_dir.glob("*.yaml")):
        doc = _miniyaml.load_file(path)
        for key in _CATALOG_NAME_KEYS:
            for item in doc.get(key, []) or []:
                if isinstance(item, dict):
                    n = item.get("name") or item.get("key") or item.get("column") \
                        or item.get("nc_variable") or item.get("internal_option_name")
                    if n:
                        names.add(n)
    _CATALOG_NAMES_CACHE[key] = names
    return names


def check_curated_facts_not_stale(model, folder):
    """A curated structured-layer fact's `confirmed_against` (see tools/_anchor_hash.py)
    must match the CURRENT hash of the prose paragraph its `from.anchor` points to. A
    mismatch means the prose changed since a person last confirmed this fact against it.
    Re-confirm the fact against the new prose by hand, then run
    `tools/refresh_confirmed_against.py --pack <pack>` to update the hash -- never run
    the refresh tool first as a way to silence this without reading the diff.

    Every curated/*.yaml file the pack actually has is examined, derived by listing the
    directory rather than from a fixed stem list, so this guard and the refresh tool
    cover exactly the same set of files: a hard-coded list on either side lets a curated
    file added later fall outside one of them, and the two then disagree silently."""
    stale = []
    curated_dir = folder / "curated"
    curated_paths = sorted(curated_dir.glob("*.yaml")) if curated_dir.is_dir() else []
    for path in curated_paths:
        doc = _load_layer_file(path)
        # Both curated citation shapes in one walk -- the four-key structured fact
        # ({source, scope, basis, from}) and an overlay row (where/evidence/scope plus an
        # optional from/confirmed_against pair) -- by the same rule the refresh tool uses:
        # a fact is any dict carrying a `from: {file, anchor}`. The two must cover exactly
        # the same set, or a fact the refresh tool updates is one this guard never reads.
        for fact_path, fact in _iter_facts_with_from(doc):
            frm = fact["from"]
            prose_path = folder / frm["file"]
            if not prose_path.is_file():
                continue  # already reported by check_structured_layers's own from-file check
            current_hash = _anchor_hash.anchor_paragraph_hash(prose_path.read_text(), frm["anchor"])
            if current_hash != fact.get("confirmed_against"):
                stale.append((path.name, fact_path, frm["file"], frm["anchor"],
                              fact.get("confirmed_against"), current_hash))
    assert not stale, (
        model, "curated fact(s) not re-confirmed since their cited prose paragraph "
        "changed -- read the new prose, fix the fact's statement if needed, then run "
        "tools/refresh_confirmed_against.py --pack " + model, stale)
    return None


BACKTICK_IDENTIFIER_RE = re.compile(r"`([A-Za-z][A-Za-z0-9_]*)`")


def _looks_like_model_identifier(tok):
    """ALLCAPS/underscore tokens (SFCRNOFF, IOPT_RUNSUB, MAX_SOILTYP) or Opt*/IOPT_*
    internal names -- deliberately conservative (misses lowercase/mixed-case prose
    words, which is fine: the point is to catch model identifiers, not every backtick)."""
    if re.match(r"^(Opt|IOPT_)\w+$", tok):
        return True
    return tok.isupper() and ("_" in tok or len(tok) >= 3)


def check_source_identifiers_resolve(model, folder):
    """depth: reference: every backticked identifier in card.md/processes.md/failures.md/
    recipes.md that looks like a model identifier must resolve through hcm_lookup.py's
    own index (exact match or one of its aliases -- namelist key/IOPT_*/Opt* for a
    physics option, table key/NoahmpIO array/internal name for a parameter, written
    name/driver array/internal noahmp name for a variable) or be named in
    evals/<pack>/lookup_allowlist.yaml with a reason. Returns (checked,
    unresolved_but_allowlisted)."""
    import hcm_lookup
    items = (hcm_lookup.collect_index(folder) if model == "hrldas-noahmp"
              else hcm_lookup.collect_index_generic(folder))
    names_lower = {n.lower() for n, _k, _e in items}

    allowlist_path = EVALS_DIR / folder.name / "lookup_allowlist.yaml"
    allowlist = {}
    if allowlist_path.is_file():
        for row in _miniyaml.load_file(allowlist_path).get("rows", []):
            allowlist[row["identifier"]] = row["reason"]

    found = set()
    for md_name in ("card.md", "processes.md", "failures.md", "recipes.md"):
        text = (folder / md_name).read_text()
        for m in BACKTICK_IDENTIFIER_RE.finditer(text):
            tok = m.group(1)
            if _looks_like_model_identifier(tok):
                found.add(tok)

    unresolved_unlisted = sorted(
        tok for tok in found if tok.lower() not in names_lower and tok not in allowlist)
    assert not unresolved_unlisted, (
        model, "identifiers in card/processes/failures/recipes.md that do not resolve "
        "through hcm_lookup.py and are not in lookup_allowlist.yaml", unresolved_unlisted)
    # An allowlist row whose identifier HAS since become resolvable is not harmless: its
    # stated reason ("not indexed as its own lookup entry", "out of scope") is then a
    # false claim about the pack, kept alive by a check that only ever reads the list
    # for permission. Every row must still be needed.
    obsolete = sorted(tok for tok in allowlist if tok.lower() in names_lower)
    assert not obsolete, (
        model, f"evals/{folder.name}/lookup_allowlist.yaml rows that now resolve through "
        "hcm_lookup.py -- remove the row (its stated reason no longer holds)", obsolete)
    allowlisted_hits = sorted(tok for tok in found if tok.lower() not in names_lower)
    return len(found), allowlisted_hits


def check_source_citations(model, folder, source_root, prose_files):
    """depth: reference, --source-root given: every `path:line` citation in the prose
    resolves to a real file under source_root, whose line count is at least the largest
    line number cited. A citation whose prefix cannot be resolved at all (a handful of
    known prose shorthand forms this simple regex cannot split, e.g. brace-expansion
    listing two related files) is reported, not asserted, but an out-of-range line
    number on a citation that DID resolve is a hard failure."""
    line_count_cache = {}
    unresolved = []
    n_checked = 0
    for name in prose_files:
        path = folder / name
        if not path.is_file():
            continue
        text = path.read_text()
        for m in CITATION_RE.finditer(text):
            prefix, nums = m.group(1), m.group(2)
            if prefix.isdigit() and len(prefix) <= 2:
                continue  # a clock time like "00:00"/"01:00", not a citation
            relpath = _citation_resolve(prefix, source_root, model=model)
            if relpath is None:
                unresolved.append((name, prefix, nums))
                continue
            fpath = source_root / relpath
            assert fpath.is_file(), (model, name, prefix, "resolved to a missing file", relpath)
            if relpath not in line_count_cache:
                line_count_cache[relpath] = sum(1 for _ in open(fpath, encoding="utf-8", errors="replace"))
            n_lines = line_count_cache[relpath]
            max_cited = max(int(tok) for group in nums.split(",") for tok in group.split("-"))
            assert max_cited <= n_lines, (
                model, name, f"{prefix}:{nums}", "cites a line past the end of the file",
                f"{relpath} has {n_lines} lines")
            n_checked += 1
    if unresolved:
        print(f"  note: {model}: {len(unresolved)} prose citation(s) with an unresolved "
              f"prefix (not asserted -- see check_source_citations docstring): {unresolved}")
    return n_checked


def check_catalogs_fresh_build(model, folder, source_root):
    """depth: reference, --source-root given: re-run extract_pack.py against source_root and
    assert the result is structurally identical to the committed catalogs, modulo
    `evidence` fields that could only differ source_read vs both (validate_catalogs.py
    --apply, which needs real output/restart/forcing files this eval does not have, is
    the only thing that makes that upgrade -- see SCHEMA.md)."""
    import tempfile
    import extract_pack
    with tempfile.TemporaryDirectory() as tmp:
        argv = ["all", "--source-root", str(source_root), "--out-dir", tmp]
        if model != "hrldas-noahmp":
            argv = ["--pack", model] + argv
        extract_pack.main(argv)
        tmp_path = Path(tmp)
        committed_dir = folder / "catalogs"
        for fresh_path in sorted(tmp_path.glob("*.yaml")):
            committed_path = committed_dir / fresh_path.name
            assert committed_path.is_file(), (model, fresh_path.name, "committed catalog missing")
            fresh_doc = _miniyaml.load_file(fresh_path)
            committed_doc = _miniyaml.load_file(committed_path)
            mismatch = _diff_modulo_evidence(fresh_doc, committed_doc)
            assert mismatch is None, (
                model, fresh_path.name, "fresh extract_pack.py build disagrees with the "
                "committed catalog beyond an evidence upgrade", mismatch)


def _diff_modulo_evidence(fresh, committed, path=""):
    """Return a description of the first structural disagreement between `fresh` (a raw
    extract_pack.py build, evidence always source_read) and `committed` (that build after
    validate_catalogs.py --apply may have upgraded some evidence fields to both), or None
    if the only differences are exactly that evidence upgrade."""
    if isinstance(fresh, dict) and isinstance(committed, dict):
        if set(fresh) != set(committed):
            return f"{path}: key sets differ: {set(fresh) ^ set(committed)}"
        for key in fresh:
            if key == "evidence":
                valid_upgrade = fresh[key] == "source_read" and committed[key] in (
                    "both", "confirmed_in_sample_input")
                if not (fresh[key] == committed[key] or valid_upgrade):
                    return f"{path}.evidence: {fresh[key]!r} -> {committed[key]!r} is not a valid upgrade"
                continue
            sub = _diff_modulo_evidence(fresh[key], committed[key], f"{path}.{key}")
            if sub:
                return sub
        return None
    if isinstance(fresh, list) and isinstance(committed, list):
        if len(fresh) != len(committed):
            return f"{path}: list length differs: {len(fresh)} vs {len(committed)}"
        for i, (a, b) in enumerate(zip(fresh, committed)):
            sub = _diff_modulo_evidence(a, b, f"{path}[{i}]")
            if sub:
                return sub
        return None
    if fresh != committed:
        return f"{path}: {fresh!r} != {committed!r}"
    return None


def check_checks_yaml(model, folder, doc, valid_checks):
    """Every curated/checks.yaml id must be the anchor of an actual heading in this
    pack's symptom-indexed prose (failures.md for a depth: reference pack, pitfalls.md
    for a depth: outline pack -- whichever this pack has) -- no stale id left over after
    a heading is renamed or removed. checks.yaml need not cover every heading: it is the
    detectable-checks layer, one entry per failure this pack can automate a check for,
    not a restatement of the whole prose list. Each detect.check must name a subcommand
    hcm_check.py actually has."""
    md_path = folder / "failures.md"
    if not md_path.is_file():
        md_path = folder / "pitfalls.md"
    assert md_path.is_file(), (model, "curated/checks.yaml but neither failures.md nor "
                                "pitfalls.md exists to cross-reference against")
    md_ids = {re.sub(r"[^\w\- ]", "", h.lower()).replace(" ", "-")
              for h in re.findall(r"^## (.+)$", md_path.read_text(), re.M)}
    yaml_ids = [entry["id"] for entry in doc.get("checks", [])]
    assert len(yaml_ids) == len(set(yaml_ids)), (model, "curated/checks.yaml", "duplicate ids")
    assert set(yaml_ids) <= md_ids, (
        model, f"curated/checks.yaml has id(s) not among {md_path.name} headings (stale?)",
        set(yaml_ids) - md_ids)
    for entry in doc.get("checks", []):
        detect = entry.get("detect")
        if detect is None:
            continue
        assert detect.get("check") in valid_checks, (
            model, "curated/checks.yaml", entry["id"], "detect.check is not an hcm_check.py subcommand",
            detect.get("check"))


def anchors(text):
    return {
        re.sub(r"[^\w\- ]", "", heading.lower()).replace(" ", "-")
        for heading in re.findall(r"^#+ (.+)$", text, re.M)
    }


def external_urls():
    """Every external URL cited anywhere in the package, with the file citing it."""
    found = {}
    for path in sorted(PACKAGE.rglob("*.md")):
        for link in re.findall(r"\]\(([^)]+)\)", path.read_text()):
            if "://" in link:
                found.setdefault(link.rstrip(".,"), path.relative_to(ROOT))
    return found


def _fetch(url, timeout=30):
    """Return (ok, detail). Prefers curl: a bare macOS python often has no CA bundle,
    so urllib reports every HTTPS URL as unreachable even when the network is fine."""
    import shutil
    import subprocess
    if shutil.which("curl"):
        done = subprocess.run(
            ["curl", "-sS", "-o", "/dev/null", "-w", "%{http_code}", "-L",
             "--max-time", str(timeout), url],
            capture_output=True, text=True)
        code = done.stdout.strip()
        if done.returncode != 0 or not code.isdigit():
            return False, (done.stderr.strip().splitlines() or ["curl failed"])[-1][:80]
        return 200 <= int(code) < 400, code
    import urllib.error
    import urllib.request
    request = urllib.request.Request(url, headers={"User-Agent": "hydroclimmate-linkcheck"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.status < 400, str(response.status)
    except urllib.error.HTTPError as error:
        return False, str(error.code)
    except Exception as error:
        return False, type(error).__name__


def check_urls():
    """Opt-in: confirm each cited URL still resolves. Needs network access.

    A control URL is probed first. Without it, a broken transport (no CA bundle, no
    egress, a captive portal) makes every link look dead, and a uniform 100% failure
    would be recorded as catastrophic link rot. That is an unmeasured run, not a result.
    """
    control = "https://example.com"
    ok, detail = _fetch(control, timeout=20)
    if not ok:
        raise SystemExit(
            f"UNMEASURED: control URL {control} unreachable ({detail}). "
            "Link checking needs working HTTPS; no conclusion about cited URLs.")

    failures = []
    urls = external_urls()
    for url, citing in sorted(urls.items()):
        ok, detail = _fetch(url)
        if not ok:
            failures.append((url, citing, detail))
    for url, citing, detail in failures:
        print(f"FAIL: {detail} {url} (cited in {citing})")
    if len(failures) == len(urls) and urls:
        raise SystemExit(
            f"UNMEASURED: all {len(urls)} cited URLs failed while the control URL "
            "succeeded. Suspect the checker or a network policy before assuming rot.")
    if failures:
        raise SystemExit(f"{len(failures)} of {len(urls)} cited URLs did not resolve")
    print(f"PASS: {len(urls)} cited URLs resolved")


def check_pitfalls(model, folder):
    """A pack's pitfalls.md must exist (checked by the caller's file-set assertion),
    have at least two entries (or say plainly that it doesn't), and cite for each
    entry a source id that actually exists in that pack's sources.md -- or state
    that the source record does not support one, rather than a fabricated id."""
    text = (folder / "pitfalls.md").read_text()
    entries = re.split(r"^## ", text, flags=re.M)[1:]
    if not entries:
        assert re.search(r"fewer than two|no genuine|not enough", text, re.I), (
            model, "empty pitfalls.md must plainly say content was insufficient")
        return
    valid_ids = set(re.findall(r"^## ([A-Za-z]\d+)$", (folder / "sources.md").read_text(), re.M))
    for entry in entries:
        scope = re.search(r"Scope and source:.*?(?=\n- |\n## |\Z)", entry, re.S)
        assert scope, (model, "pitfalls entry missing 'Scope and source' field")
        line = scope.group(0)
        if "not stated in the source record" in line:
            continue
        cited = re.findall(r"\[([A-Za-z]\d+)\]\(sources\.md#[a-z]\d+\)", line)
        assert cited, (model, "pitfalls entry cites no source id", line[:80])
        for cid in cited:
            assert cid in valid_ids, (model, cid, "not defined in sources.md")


PRIVATE_STRING_PATTERNS = {
    # Internal phase/process bookkeeping (dev-repo lettered work phases, fault/silent-
    # failure register ids, eval task ids) -- private project bookkeeping, must not ship.
    # The K-number pattern excludes a digit/letter/slash immediately before it so it does
    # not fire on a legitimate unit like "W/m2/K4" (Stefan-Boltzmann's K^4).
    "phase_label_K": re.compile(r"(?<![\w/])K[1-9](?!\w)"),
    "fault_id_SF": re.compile(r"\bSF-\d+\b"),
    "fault_id_F": re.compile(r"\bF-\d+\b"),
    "eval_task_id_E1": re.compile(r"\bE1n?\b"),
    "process_word_audit": re.compile(r"\baudit\w*\b", re.I),
    "process_word_worksheet": re.compile(r"\bworksheet\b", re.I),
    # Site/private strings.
    "abs_path_glade": re.compile(r"/glade/\S*"),
}
CJK_RE = re.compile("[\u4e00-\u9fff\u3400-\u4dbf\u3040-\u30ff\uac00-\ud7af\uff00-\uffef]")

# A pack's own history (how it got to its current form) does not belong anywhere in the
# shipped product except CHANGELOG.md. This pattern list catches the common tells of that
# narration; it is intentionally literal (a handful of fixed phrases), not a general
# tense/style checker.
PROCESS_NARRATION_PATTERNS = {
    "moved_to": re.compile(r"\bmoved to\b", re.I),
    "re_sourced": re.compile(r"\bre-sourced\b", re.I),
    "converted_from": re.compile(r"\bconverted from\b", re.I),
    "formerly": re.compile(r"\bformerly\b", re.I),
    "no_longer": re.compile(r"\bno longer\b", re.I),
    "superseded": re.compile(r"\bsuperseded\b", re.I),
    "generation_12": re.compile(r"\bgeneration [12]\b", re.I),
    "stub": re.compile(r"\bstub\b", re.I),
    "redirect": re.compile(r"\bredirect(s|ed|ing)?\b", re.I),
}
# A tiny allowlist for a legitimate scientific (not process-history) use of one of the
# phrases above. Matched against the same-line text, not the whole file -- so it stays
# precise rather than silencing an entire file. Add an entry here only when the match is
# genuinely not narrating this repository's own history.
PROCESS_NARRATION_LINE_ALLOWLIST = (
    "converted internally to mixing ratio",
    # core.md / DECISIONS.md: a project's own decision log preserving a superseded
    # *project* decision (generic project-record methodology), not narration about this
    # package's history.
    "preserve superseded decisions and link replacements",
    "preserve superseded entries and link replacements",
    "status: <adopted / superseded>",
    # sources.md files: describe which cited SOURCE document is more authoritative than
    # another (a citation-hierarchy fact about the literature), not this package's history.
    "superseded for every",
    "superseded by the pinned copy",
    "superseded and corrected by",
    # HANDOVER.md template: generic snapshot-hygiene instruction, not narration about
    # this package's own history.
    "remove completed items no longer needed",
    # _anchor_hash.py: ordinary technical description of a hash comparison.
    "the hash no longer matches",
    # vic/catalogs/global_parameters.yaml's removed_since_vic4_message: the VIC parser's
    # own quoted rejection text for a key it no longer accepts (a fact about the pinned
    # VIC source's own log_err() string, mechanically extracted -- not narration about
    # this package's history).
    "is no longer a supported option",
)

# A short, explicit list of pre-existing files that use one of the words above in its
# ordinary English sense (e.g. "have not been audited" = "have not been checked"), not
# as a reference to a dev-repo process step. Listed with the reason, same discipline as
# the identifier allowlist check_source_identifiers_resolve uses -- never a silent
# blanket exclusion.
PRIVATE_STRING_ALLOWLIST = {
    "evals/check_knowledge.py": "this file defines the patterns/allowlist above as "
        "literal strings, and its own comments explain them using the same words",
    "hydroclimmate/references/models/ctsm/sources.md": "pre-existing pack text: 'have not been audited' (ordinary sense)",
}

# The same idea one level finer, for a file where only ONE phrase uses such a word in its
# ordinary English sense: matched against the surrounding text, so the rest of that file
# is still scanned. Allowlisting the whole file for a single ordinary word would also
# stop it being scanned for site paths and process bookkeeping, which is a real loss.
PRIVATE_STRING_LINE_ALLOWLIST = (
    # mizuroute/failures.md: "audit the mapping weights first" -- an instruction to the
    # reader about their own remapping file, the ordinary English verb, not a reference
    # to any review step of this project's own.
    "audit the mapping weights",
)


def check_no_private_strings():
    """Every file under the package and evals/, scanned for CJK characters, for the
    private/internal-process string patterns above, and (everywhere except
    CHANGELOG.md) for process-narration language describing this repository's own
    history. A hit is a hard failure unless the whole file is in
    PRIVATE_STRING_ALLOWLIST, or the matching line is covered by
    PRIVATE_STRING_LINE_ALLOWLIST (private-string patterns) or
    PROCESS_NARRATION_LINE_ALLOWLIST (narration patterns)."""
    hits = []
    scanned = 0
    roots = [PACKAGE, ROOT / "evals"]
    for root_dir in roots:
        for path in sorted(root_dir.rglob("*")):
            if not path.is_file() or path.suffix not in (".md", ".yaml", ".json", ".py"):
                continue
            rel = str(path.relative_to(ROOT))
            if rel in PRIVATE_STRING_ALLOWLIST:
                continue
            scanned += 1
            try:
                text = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                hits.append((rel, "not valid utf-8", ""))
                continue
            if CJK_RE.search(text):
                hits.append((rel, "CJK characters", ""))
            for name, pat in PRIVATE_STRING_PATTERNS.items():
                for m in pat.finditer(text):
                    context = re.sub(r"\s+", " ", text[max(0, m.start() - 80):m.end() + 40]).lower()
                    if any(allowed in context for allowed in PRIVATE_STRING_LINE_ALLOWLIST):
                        continue
                    line_no = text.count("\n", 0, m.start()) + 1
                    hits.append((rel, name, f"line {line_no}: {m.group(0)!r}"))
                    break
            if path.name != "CHANGELOG.md":
                # A window of surrounding text, newlines collapsed to spaces, so the
                # allowlist still matches a phrase that happens to be soft-wrapped across
                # a line break in the source file.
                for name, pat in PROCESS_NARRATION_PATTERNS.items():
                    for m in pat.finditer(text):
                        window_start = max(0, m.start() - 80)
                        window_end = min(len(text), m.end() + 40)
                        context = re.sub(r"\s+", " ", text[window_start:window_end]).lower()
                        if any(allowed in context for allowed in PROCESS_NARRATION_LINE_ALLOWLIST):
                            continue
                        line_no = text.count("\n", 0, m.start()) + 1
                        hits.append((rel, f"process_narration_{name}", f"line {line_no}: {m.group(0)!r}"))
    assert not hits, ("private/internal-process strings found (add a reason to "
                       "PRIVATE_STRING_ALLOWLIST, or the matching line to "
                       "PROCESS_NARRATION_LINE_ALLOWLIST, only if the match is genuinely "
                       "not process bookkeeping or history narration)", hits[:20])
    print(f"PASS: no CJK, private/internal-process strings, or process-narration language "
          f"in {scanned} package/evals files")


def check_no_orphan_files(model, folder, manifest):
    """Every hand-maintained file in a pack must be reachable: named in pack.yaml's
    `prose` or `curated` list, or one of the generated catalog files
    tools/extract_pack.py and tools/build_index.py always produce. A leftover file from a
    restructuring that nothing points to any more is exactly the kind of clutter this
    check exists to catch."""
    referenced = {entry.get("file") for entry in manifest.get("prose", []) if entry.get("file")}
    referenced |= {entry.get("file") for entry in manifest.get("curated", []) if entry.get("file")}
    # Every catalog filename any pack's extractor module can produce, plus the two
    # machine-only files every `depth: reference` pack has -- derived from the
    # extractor modules themselves so a new pack's catalogs never need a hand-kept
    # filename list here (SCHEMA.md: "pack-specific knowledge confined to the
    # extractor module").
    import extract_pack
    known_generated = {"MANIFEST.json", "index.json"}
    for mod in extract_pack.PACKS.values():
        known_generated |= set(mod.FILENAME.values())
    known_curated = {"kinds_overlay.yaml", "options_overlay.yaml"}
    for path in sorted(folder.rglob("*")):
        if not path.is_file() or path.suffix not in (".yaml", ".json"):
            continue
        if path.name == "pack.yaml":
            continue
        rel = str(path.relative_to(folder))
        if rel in referenced or path.name in known_generated:
            continue
        if path.parent.name == "curated" and path.name in known_curated:
            continue
        raise AssertionError((
            model, rel, "not declared as a layer file in pack.yaml and not a recognized "
            "generated catalog file -- an orphan left over from a restructuring, or a "
            "new curated file pack.yaml has not been told about yet"))


def check_markdown_formatted():
    """Every Markdown file must already be one-line-per-paragraph formatted (see
    format_markdown.py) -- run `python3 evals/format_markdown.py` and re-check if this
    fails."""
    import format_markdown
    files = format_markdown.default_files()
    problems_by_file = {}
    not_formatted = []
    for path in files:
        original = path.read_text(encoding="utf-8")
        formatted = format_markdown.format_text(original)
        problems = format_markdown.verify(original, formatted)
        rel = str(path.relative_to(ROOT))
        if problems:
            problems_by_file[rel] = problems
            continue
        if formatted != original:
            not_formatted.append(rel)
    assert not problems_by_file, (
        "format_markdown.py could not safely reflow some file(s) -- fix the file or the "
        "formatter, never by forcing the join", problems_by_file)
    assert not not_formatted, (
        "Markdown file(s) not one-line-per-paragraph formatted -- run "
        "`python3 evals/format_markdown.py`", not_formatted)
    print(f"PASS: {len(files)} Markdown files are one-line-per-paragraph formatted")


def check_freshness():
    """Report how old each pack's source review is. Floating URLs decay quietly."""
    stale = []
    sources = sorted(PACKAGE.glob("references/models/*/sources.md"))
    assert sources, "No model source packs found"
    for source in sources:
        # Not line-anchored: one-line-per-paragraph formatting (see format_markdown.py)
        # can leave a "Checked: ..." sentence mid-line, as the end of its paragraph.
        match = re.search(r"Checked:\s*(\d{4})-(\d{2})-(\d{2})", source.read_text())
        assert match, f"{source} has no 'Checked: YYYY-MM-DD' line"
        age = (date.today() - date(*map(int, match.groups()))).days
        assert age >= 0, f"{source} has a future Checked date"
        if age > STALE_DAYS:
            stale.append((source.parent.name, age))
    if stale:
        for model, age in stale:
            print(f"WARN: {model} sources last checked {age} days ago (limit {STALE_DAYS})")
    else:
        print(f"PASS: all {len(sources)} source-pack review dates within {STALE_DAYS} days")


DEFAULT_SOURCE_ROOT_PACK = "hrldas-noahmp"


def _parse_source_roots(argv):
    """{pack: source root} from the command line. `--source-root PACK=PATH` names its
    pack (any pack, including one added later); `--source-root PATH` keeps its original
    meaning, the pack this checker originally shipped for; `--<pack>-source-root PATH`
    keeps every existing per-pack flag working, for any pack, so a command written
    against an earlier version of this file still runs unchanged."""
    roots = {}
    for i, arg in enumerate(argv):
        pack = None
        if arg == "--source-root":
            value = argv[i + 1]
            pack, _, path = value.partition("=")
            if not path:
                pack, path = DEFAULT_SOURCE_ROOT_PACK, value
        elif arg.startswith("--") and arg.endswith("-source-root"):
            pack = arg[len("--"):-len("-source-root")]
            path = argv[i + 1]
        if pack is None:
            continue
        root = Path(path).resolve()
        assert root.is_dir(), f"{arg} {path}: not a directory"
        roots[pack] = root
    return roots


def main():
    source_roots = _parse_source_roots(sys.argv)
    pending = []

    count = 0
    for path in sorted(PACKAGE.rglob("*.md")):
        text = path.read_text()
        assert text.endswith("\n"), path
        assert all(line == line.rstrip() for line in text.splitlines()), path
        for link in re.findall(r"\]\(([^)]+)\)", text):
            if "://" in link:
                continue
            target, _, anchor = unquote(link).partition("#")
            destination = path.parent / target if target else path
            assert destination.is_file(), (path, link)
            if anchor:
                assert anchor in anchors(destination.read_text()), (path, link)
            count += 1

    entry = (PACKAGE / "SKILL.md").read_text()
    match = re.search(r"HydroClimMate v(\d+\.\d+)", entry)
    assert match, "Missing skill version"
    assert f"Version {match.group(1)} " in (ROOT / "README.md").read_text(), "README version drift"

    models = sorted(p.name for p in (PACKAGE / "references/models").iterdir() if p.is_dir())
    assert models, "No model packs found"
    valid_checks = _hcm_check_subcommands()
    assert valid_checks, "Could not read hcm_check.py subcommand names"
    total_facts = 0
    total_citations_checked = 0
    total_overlay_rows_checked = 0
    total_identifiers_checked = 0
    total_identifiers_allowlisted = 0
    n_reference = 0
    for model in models:
        folder = PACKAGE / "references/models" / model
        manifest_path = _pack_manifest_path(folder)
        assert manifest_path.is_file(), (model, "pack.yaml is required")
        manifest = _load_layer_file(manifest_path)
        depth = manifest.get("depth")
        assert depth in DEPTH_VALUES, (model, "manifest depth must be one of", DEPTH_VALUES, depth)

        if depth == "outline":
            assert {p.name for p in folder.glob("*.md")} == OUTLINE_MD_FILES, model
            for name in ("overview", "execution", "outputs"):
                text = (folder / f"{name}.md").read_text()
                assert re.search(r"\[[A-Z]\d+\]\(sources.md#[a-z]\d+\)", text), (model, name)
            check_pitfalls(model, folder)
        else:
            n_reference += 1
            present_md = {p.name for p in folder.glob("*.md")}
            missing_prose = REFERENCE_MD_FILES - present_md
            has_readme = "README.md" in present_md
            # Anything present that is neither a required file nor the optional README
            # is either a leftover outline file (rebuild not yet finished) or truly
            # unexpected clutter -- both reported, not silently accepted.
            leftover_outline = (present_md - REFERENCE_MD_FILES - {"README.md"})
            if missing_prose or leftover_outline or not has_readme:
                # Prose is a separate author's deliverable (this pack's own pack.yaml
                # names who); a pack mid-rebuild carries this honestly, as a reported
                # pending item, rather than a silent pass or an uninformative crash --
                # every other check below (catalogs, manifest, curated overlays) still
                # runs against whatever IS present.
                pending.append({
                    "model": model, "missing_prose_files": sorted(missing_prose),
                    "leftover_outline_files": sorted(leftover_outline),
                    "readme_missing": not has_readme,
                })
            if not missing_prose and not leftover_outline:
                for md_name, cap in REFERENCE_SIZE_CAPS.items():
                    size = (folder / md_name).stat().st_size
                    assert size <= cap, (model, md_name, f"{size} bytes exceeds the {cap}-byte cap")
            if has_readme:
                size = (folder / "README.md").stat().st_size
                assert size <= README_SIZE_CAP, (
                    model, "README.md", f"{size} bytes exceeds the {README_SIZE_CAP}-byte cap")
                for routing_file in (PACKAGE / "references/models/index.md", PACKAGE / "references/core.md"):
                    if routing_file.is_file():
                        assert f"{model}/README.md" not in routing_file.read_text(), (
                            model, routing_file.name, "must not route an agent to README.md "
                            "(human-facing entry point, agents are not routed to it -- see SCHEMA.md)")
            pack_source_root = source_roots.get(model)
            total_overlay_rows_checked += check_overlay_catalogs(model, folder, pack_source_root)
            check_curated_facts_not_stale(model, folder)
            n_ids, allowlisted = check_source_identifiers_resolve(model, folder)
            total_identifiers_checked += n_ids
            total_identifiers_allowlisted += len(allowlisted)
            if pack_source_root is not None:
                if not missing_prose:
                    total_citations_checked += check_source_citations(
                        model, folder, pack_source_root,
                        ["card.md", "processes.md", "failures.md", "recipes.md", "version.md", "sources.md"])
                check_catalogs_fresh_build(model, folder, pack_source_root)

        check_no_orphan_files(model, folder, manifest)
        valid_source_ids = set(re.findall(r"^## ([A-Za-z]\d+)$", (folder / "sources.md").read_text(), re.M))
        total_facts += check_structured_layers(model, folder, valid_source_ids, valid_checks)
    assert n_reference >= 1, "No depth: reference pack found"

    for filename in ("trigger-eval.json", "knowledge-eval.json"):
        cases = json.loads((ROOT / "evals" / filename).read_text())
        assert cases and isinstance(cases, list), filename
        if filename == "knowledge-eval.json":
            assert len({c["id"] for c in cases}) == len(cases)
            for case in cases:
                assert case["prompt"] and case["rubric"]
                for topic in case["relevant_topics"]:
                    assert (PACKAGE / "references/models" / topic).is_file(), topic

    # Independent three-point quadrature, exact for a linear triangular field.
    barycentric = ((2 / 3, 1 / 6, 1 / 6),
                   (1 / 6, 2 / 3, 1 / 6), (1 / 6, 1 / 6, 2 / 3))
    triangles = ((1.0, (0.0, 0.0, 3.0)), (3.0, (3.0, 3.0, 3.0)))
    integral = 0.0
    for area, values in triangles:
        quadrature = sum(sum(w * v for w, v in zip(point, values))
                         for point in barycentric) / 3
        integral += area * quadrature
    assert abs(integral / 4 - 2.5) < 1e-12
    # Evaluate volumes separately rather than repeating the delta-thickness formula.
    old_mass = 2 * 10 * 900
    new_mass = 2 * 7 * 900
    assert new_mass - old_mass == -5400
    print(f"PASS: {count} package links/anchors, {len(models)} source-linked packs, shared entrypoint, fixtures")
    print(f"PASS: {total_facts} structured-layer facts validated (source ids, from-anchors, basis)")
    print(f"PASS: {total_overlay_rows_checked} curated overlay rows checked (kinds_overlay.yaml "
          f"variables resolve in outputs.yaml, options_overlay.yaml internal_option_names in "
          f"physics_options.yaml, and every overlay row's citations resolve where a source "
          f"root was given)")
    print("PASS: every depth: reference curated structured-layer fact's confirmed_against hash "
          "matches its cited prose paragraph's current text (no stale re-confirmation)")
    print(f"PASS: {total_identifiers_checked} backticked model identifiers in card/processes/"
          f"failures/recipes.md resolve through hcm_lookup.py (exact or alias) or "
          f"lookup_allowlist.yaml ({total_identifiers_allowlisted} allowlisted)")
    reference_models = [m for m in models
                        if _load_layer_file(_pack_manifest_path(PACKAGE / "references/models" / m)).get("depth") == "reference"]
    checked_roots = [m for m in reference_models if m in source_roots]
    if checked_roots:
        print(f"PASS: {total_citations_checked} prose path:line citations resolved, generated "
              f"catalogs match a fresh build (modulo evidence upgrades), and every overlay "
              f"citation resolved -- for {', '.join(checked_roots)} (source root given)")
    skipped_roots = [m for m in reference_models if m not in source_roots]
    if skipped_roots:
        print(f"Skipped source-root checks (path:line citation resolution, fresh-build catalog "
              f"equality, overlay citation resolution) for {', '.join(skipped_roots)}; pass "
              f"--source-root <pack>=<checkout> for each of them to run these "
              f"(a bare --source-root <checkout> still means {DEFAULT_SOURCE_ROOT_PACK}).")
    print("PASS: linear-triangle quadrature mean=2.5; fixed-domain mass change=-5400 kg")
    print("These are static/arithmetic checks, not model or agent-behavior validation.")
    check_no_private_strings()
    check_freshness()
    check_markdown_formatted()
    if "--network" in sys.argv:
        check_urls()
    else:
        print(f"Skipped {len(external_urls())} external URLs; pass --network to verify them.")

    if pending:
        print(f"\nPENDING ({len(pending)} depth: reference pack(s) mid-rebuild -- catalogs/"
              f"manifest/curated checks above still ran and passed for these; only the "
              f"prose-shape/size and prose-citation checks are withheld):")
        for item in pending:
            print(f"  {item['model']}: missing {item['missing_prose_files'] or '(none)'}"
                  + (f"; leftover outline files not yet removed: {item['leftover_outline_files']}"
                     if item["leftover_outline_files"] else "")
                  + ("; README.md not yet written" if item.get("readme_missing") else ""))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
