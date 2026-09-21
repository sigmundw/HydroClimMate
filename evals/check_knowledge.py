"""Offline structural checks and independent arithmetic cases; no model execution.

Pass --network to additionally verify that every cited external URL still resolves.
That check is opt-in so the default run stays offline and deterministic.

Pass --source-root ROOT (the pinned HRLDAS+noahmp checkout) to additionally, for every
generation-2 pack (see references/models/SCHEMA.md): resolve every `path:line` citation
in its prose against that source tree's actual line counts, and assert that regenerating
its catalogs with tools/extract_pack.py from ROOT reproduces the committed catalogs
structurally (modulo `evidence: source_read` vs `both`, which only validate_catalogs.py
against real output/restart/forcing files -- not available here -- can upgrade). Both
checks are skipped cleanly, with a note, when --source-root is not given.
"""
import json
import re
import sys
from datetime import date
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "hydroclimmate"
# Source packs cite floating branch URLs, so they rot silently. Re-check by this age.
STALE_DAYS = 180

# Structured layers (see references/models/SCHEMA.md) are required for every pack. A pack
# with no pack.yaml/pack.json is a validator failure, not a gap.
REQUIRE_STRUCTURED_LAYERS = True

BASIS_VALUES = {"source_read", "observed_in_output", "both", "unverified"}
STRUCTURED_LAYERS = ("interface", "switches", "pitfalls", "workflows", "index", "selftest")

GEN1_MD_FILES = {"overview.md", "execution.md", "outputs.md", "pitfalls.md", "sources.md"}
# Generation 2 (v0.9 knowledge-layer rebuild): the new prose, plus the redirect stubs kept
# only so pre-rebuild links and the pitfalls.yaml id namespace still resolve.
GEN2_MD_FILES = {"card.md", "processes.md", "failures.md", "recipes.md", "version.md",
                  "sources.md", "overview.md", "outputs.md", "execution.md", "pitfalls.md"}
GEN2_SIZE_CAPS = {"card.md": 4096, "processes.md": 12288, "failures.md": 14336,
                   "recipes.md": 10240, "version.md": 3072}

# `path:line` citation resolution (generation-2 prose only; see check_source_citations).
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


def _pack_manifest_path(folder):
    """A pack's manifest is pack.yaml (generation 2, or a generation-1 pack converted to
    YAML) or pack.json (a generation-1 pack not yet converted); see SCHEMA.md."""
    yaml_path = folder / "pack.yaml"
    if yaml_path.is_file():
        return yaml_path
    return folder / "pack.json"


def check_structured_layers(model, folder, valid_source_ids, valid_checks):
    """Validate a pack's optional structured layers (see SCHEMA.md). Returns the number
    of facts found, for the caller's summary line."""
    manifest_path = _pack_manifest_path(folder)
    if not manifest_path.is_file():
        assert not REQUIRE_STRUCTURED_LAYERS, (
            model, "pack.yaml/pack.json is required (REQUIRE_STRUCTURED_LAYERS=True) but missing")
        return 0

    try:
        manifest = _load_layer_file(manifest_path)
    except (json.JSONDecodeError, _miniyaml.MiniYamlError) as exc:
        raise AssertionError((model, manifest_path.name, "does not parse", str(exc))) from exc

    generation = manifest.get("generation", 1)
    assert generation in (1, 2), (model, "manifest generation must be 1 or 2", generation)

    layers = manifest.get("layers", {})
    fact_count = 0
    for layer_name, layer_info in layers.items():
        filename = layer_info.get("file")
        coverage = layer_info.get("coverage")
        assert coverage in ("full", "partial", "none"), (model, layer_name, "bad coverage value")
        if not filename:
            continue
        layer_path = folder / filename
        assert layer_path.is_file(), (model, layer_name, f"declared file {filename} missing")
        try:
            doc = _load_layer_file(layer_path)
        except (json.JSONDecodeError, _miniyaml.MiniYamlError) as exc:
            raise AssertionError((model, filename, "does not parse", str(exc))) from exc

        layer_has_unverified = False
        for fact_path, fact in _iter_facts(doc):
            fact_count += 1
            assert fact["basis"] in BASIS_VALUES, (model, filename, fact_path, "bad basis", fact["basis"])
            if fact["basis"] == "unverified":
                layer_has_unverified = True
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

        assert not (coverage == "full" and layer_has_unverified), (
            model, filename, "coverage: full is refused while an entry has basis: unverified")

        if layer_name == "pitfalls":
            check_pitfalls_json(model, folder, doc, valid_checks)
        if layer_name == "index":
            check_index_matches_build(model, folder, doc)

    if generation == 2:
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


def _iter_catalog_entries(node):
    """Yield every dict in a generated catalog document that carries a 'where' key (one
    extracted fact), at any nesting depth -- catalogs/*.yaml can nest a record's own
    sub-records (e.g. a parameter-table group's `parameters`, a physics option's
    `values`)."""
    if isinstance(node, dict):
        if "where" in node:
            yield node
        for value in node.values():
            yield from _iter_catalog_entries(value)
    elif isinstance(node, list):
        for item in node:
            yield from _iter_catalog_entries(item)


def check_catalog_evidence(model, folder):
    """Generation 2 (SCHEMA.md): every generated catalog entry (anything carrying a
    `where` fact-location) must also carry an `evidence` grade -- the two are meant to
    travel together, and extract_pack.py never emits one without the other."""
    catalogs_dir = folder / "catalogs"
    assert catalogs_dir.is_dir(), (model, "generation 2 but no catalogs/ directory")
    yaml_files = sorted(catalogs_dir.glob("*.yaml"))
    assert yaml_files, (model, "generation 2 but catalogs/ has no *.yaml files")
    n_entries = 0
    for path in yaml_files:
        doc = _miniyaml.load_file(path)
        for entry in _iter_catalog_entries(doc):
            n_entries += 1
            where = entry["where"]
            assert isinstance(where, dict) and {"file", "line", "commit"} <= where.keys(), (
                model, path.name, "where must be {file, line, commit}", where)
            assert entry.get("evidence") in ("source_read", "observed_in_output", "both"), (
                model, path.name, "entry with 'where' is missing a valid 'evidence'", entry.get("name"))
    assert n_entries > 0, (model, "catalogs/*.yaml carry no where-tagged entries at all")


def _citation_resolve(prefix, source_root):
    """Resolve a citation prefix (e.g. 'drv', 'src/SurfaceAlbedoMod.F90',
    'NoahmpIOVarInitMod.F90', 'hrldas/run/README.namelist') to a path relative to
    `source_root`, or None if it cannot be resolved. A bare filename (no directory) is
    resolved by a basename search, preferring a hit under this pack's own build path
    (CITATION_PREFERRED_DIR_HINT) when more than one driver variant defines the same
    module name -- exactly the ambiguity this pack's own prose warns about
    (version.md: "Two urban drivers exist in this tree")."""
    if prefix in CITATION_SHORTHAND_FILE:
        return CITATION_SHORTHAND_FILE[prefix]
    for key, expansion in CITATION_SHORTHAND_DIR.items():
        if prefix == key:
            return None
        if prefix.startswith(key + "/"):
            return expansion + prefix[len(key):]
    if "/" in prefix:
        return prefix
    if prefix.endswith((".F90", ".F", ".TBL")):
        hits = [h for h in source_root.rglob(prefix) if ".git" not in h.parts]
        if len(hits) > 1:
            preferred = [h for h in hits if CITATION_PREFERRED_DIR_HINT in str(h)]
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
    """catalogs/kinds_overlay.yaml and catalogs/options_overlay.yaml are curated,
    hand-verified, never generated (see SCHEMA.md). Every row's subject must actually
    exist in the corresponding generated catalog (checked always -- cheap, no source
    tree needed), and every citation (`where`, `reset_where`) must resolve to a real
    file and an in-range line when --source-root is given (skipped cleanly otherwise)."""
    catalogs_dir = folder / "catalogs"
    n_checked = 0

    kinds_path = catalogs_dir / "kinds_overlay.yaml"
    if kinds_path.is_file():
        outputs_doc = _miniyaml.load_file(catalogs_dir / "outputs.yaml")
        output_names = {v["name"] for v in outputs_doc["variables"]}
        for row in _miniyaml.load_file(kinds_path).get("rows", []):
            n_checked += 1
            assert row["variable"] in output_names, (
                model, "kinds_overlay.yaml", "variable not in catalogs/outputs.yaml",
                row["variable"])
            if source_root is not None:
                _resolve_and_check_citation(model, "kinds_overlay.yaml", source_root,
                                             row["where"], row["variable"])
                if row.get("reset_where"):
                    _resolve_and_check_citation(model, "kinds_overlay.yaml", source_root,
                                                 row["reset_where"], row["variable"] + " (reset)")

    options_path = catalogs_dir / "options_overlay.yaml"
    if options_path.is_file():
        physics_doc = _miniyaml.load_file(catalogs_dir / "physics_options.yaml")
        option_names = {o["internal_option_name"] for o in physics_doc["options"]}
        for row in _miniyaml.load_file(options_path).get("rows", []):
            n_checked += 1
            assert row["internal_option_name"] in option_names, (
                model, "options_overlay.yaml", "internal_option_name not in "
                "catalogs/physics_options.yaml", row["internal_option_name"])
            if source_root is not None and row.get("where"):
                _resolve_and_check_citation(model, "options_overlay.yaml", source_root,
                                             row["where"], row["internal_option_name"])
    return n_checked


def check_curated_facts_not_stale(model, folder):
    """A curated structured-layer fact's `confirmed_against` (see tools/_anchor_hash.py)
    must match the CURRENT hash of the prose paragraph its `from.anchor` points to. A
    mismatch means the prose changed since a person last confirmed this fact against it
    -- exactly the drift that let switches.yaml/interface.yaml keep an old, wrong urban
    statement after processes.md was corrected to cite the same (corrected) anchor.
    Re-confirm the fact against the new prose by hand, then run
    `tools/refresh_confirmed_against.py --pack <pack>` to update the hash -- never run
    the refresh tool first as a way to silence this without reading the diff."""
    stale = []
    for stem in ("interface", "switches", "pitfalls", "workflows"):
        path = folder / f"{stem}.yaml"
        if not path.is_file():
            path = folder / f"{stem}.json"
        if not path.is_file():
            continue
        doc = _load_layer_file(path)
        for fact_path, fact in _iter_facts(doc):
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
    """Generation 2: every backticked identifier in card.md/processes.md/failures.md/
    recipes.md that looks like a model identifier must resolve through hcm_lookup.py's
    own index (exact match or one of its aliases -- namelist key/IOPT_*/Opt* for a
    physics option, table key/NoahmpIO array/internal name for a parameter, written
    name/driver array/internal noahmp name for a variable) or be named in
    lookup_allowlist.yaml with a reason. Returns (checked, unresolved_but_allowlisted)."""
    import hcm_lookup
    items = hcm_lookup.collect_index(folder)
    names_lower = {n.lower() for n, _k, _e in items}

    allowlist_path = folder / "lookup_allowlist.yaml"
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
    allowlisted_hits = sorted(tok for tok in found if tok.lower() not in names_lower)
    return len(found), allowlisted_hits


def check_source_citations(model, folder, source_root, prose_files):
    """Generation 2, --source-root given: every `path:line` citation in the prose
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
            relpath = _citation_resolve(prefix, source_root)
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
    """Generation 2, --source-root given: re-run extract_pack.py against source_root and
    assert the result is structurally identical to the committed catalogs, modulo
    `evidence` fields that could only differ source_read vs both (validate_catalogs.py
    --apply, which needs real output/restart/forcing files this eval does not have, is
    the only thing that makes that upgrade -- see SCHEMA.md)."""
    import tempfile
    import extract_pack
    with tempfile.TemporaryDirectory() as tmp:
        extract_pack.main(["all", "--source-root", str(source_root), "--out-dir", tmp])
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
                if not (fresh[key] == committed[key] or (fresh[key] == "source_read" and committed[key] == "both")):
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


def check_pitfalls_json(model, folder, doc, valid_checks):
    """pitfalls.json ids must map one-to-one to pitfalls.md headings; each detect.check
    must name a subcommand hcm_check.py actually has."""
    md_ids = {re.sub(r"[^\w\- ]", "", h.lower()).replace(" ", "-")
              for h in re.findall(r"^## (.+)$", (folder / "pitfalls.md").read_text(), re.M)}
    json_ids = [entry["id"] for entry in doc.get("pitfalls", [])]
    assert len(json_ids) == len(set(json_ids)), (model, "pitfalls.json", "duplicate ids")
    assert set(json_ids) == md_ids, (
        model, "pitfalls.json ids do not match pitfalls.md headings one-to-one",
        "json only:", set(json_ids) - md_ids, "md only:", md_ids - set(json_ids))
    for entry in doc.get("pitfalls", []):
        detect = entry.get("detect")
        if detect is None:
            continue
        assert detect.get("check") in valid_checks, (
            model, "pitfalls.json", entry["id"], "detect.check is not an hcm_check.py subcommand",
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

# A short, explicit list of pre-existing files that use one of the words above in its
# ordinary English sense (e.g. "have not been audited" = "have not been checked"), not
# as a reference to a dev-repo process step. Listed with the reason, same discipline as
# the identifier allowlist check_source_identifiers_resolve uses -- never a silent
# blanket exclusion.
PRIVATE_STRING_ALLOWLIST = {
    "evals/check_knowledge.py": "this file defines the patterns/allowlist above as "
        "literal strings, and its own comments explain them using the same words",
    "evals/v0.6-results.md": "pre-existing v0.6 record; 'audit' used in its ordinary sense",
    "evals/v0.6-offline-probe.json": "pre-existing v0.6 record; 'audit' used in its ordinary sense",
    "evals/README.md": "pre-existing text: 'not a complete scientific source audit' (ordinary sense)",
    "hydroclimmate/references/models/vic/sources.md": "pre-existing pack text: 'have not been audited' (ordinary sense)",
    "hydroclimmate/references/models/ctsm/sources.md": "pre-existing pack text: 'have not been audited' (ordinary sense)",
}


def check_no_private_strings():
    """Every file under the package and evals/, scanned for CJK characters and for the
    private/internal-process string patterns above. A hit is a hard failure unless the
    whole file is in PRIVATE_STRING_ALLOWLIST (see its own docstring)."""
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
                m = pat.search(text)
                if m:
                    line_no = text.count("\n", 0, m.start()) + 1
                    hits.append((rel, name, f"line {line_no}: {m.group(0)!r}"))
    assert not hits, ("private/internal-process strings found (add a reason to "
                       "PRIVATE_STRING_ALLOWLIST only if the match is genuinely not "
                       "process bookkeeping)", hits[:20])
    print(f"PASS: no CJK or private/internal-process strings in {scanned} package/evals files")


def check_freshness():
    """Report how old each pack's source review is. Floating URLs decay quietly."""
    stale = []
    sources = sorted(PACKAGE.glob("references/models/*/sources.md"))
    assert sources, "No model source packs found"
    for source in sources:
        match = re.search(r"^Checked:\s*(\d{4})-(\d{2})-(\d{2})", source.read_text(), re.M)
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


def main():
    source_root = None
    if "--source-root" in sys.argv:
        source_root = Path(sys.argv[sys.argv.index("--source-root") + 1]).resolve()
        assert source_root.is_dir(), f"--source-root {source_root} is not a directory"

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
    pointer = (PACKAGE / "AGENTS.md").read_text()
    assert "[SKILL.md](SKILL.md)" in pointer, "Broken legacy integration pointer"
    assert "| Feature |" not in pointer, "Routing rules duplicated in compatibility pointer"

    models = sorted(p.name for p in (PACKAGE / "references/models").iterdir() if p.is_dir())
    assert models, "No model packs found"
    valid_checks = _hcm_check_subcommands()
    assert valid_checks, "Could not read hcm_check.py subcommand names"
    total_facts = 0
    total_citations_checked = 0
    total_overlay_rows_checked = 0
    total_identifiers_checked = 0
    total_identifiers_allowlisted = 0
    for model in models:
        folder = PACKAGE / "references/models" / model
        manifest_path = _pack_manifest_path(folder)
        generation = _load_layer_file(manifest_path).get("generation", 1) if manifest_path.is_file() else 1

        if generation == 1:
            assert {p.name for p in folder.glob("*.md")} == GEN1_MD_FILES, model
            for name in ("overview", "execution", "outputs"):
                text = (folder / f"{name}.md").read_text()
                assert re.search(r"\[[A-Z]\d+\]\(sources.md#[a-z]\d+\)", text), (model, name)
            check_pitfalls(model, folder)
        else:
            assert {p.name for p in folder.glob("*.md")} == GEN2_MD_FILES, model
            for md_name, cap in GEN2_SIZE_CAPS.items():
                size = (folder / md_name).stat().st_size
                assert size <= cap, (model, md_name, f"{size} bytes exceeds the {cap}-byte cap")
            total_overlay_rows_checked += check_overlay_catalogs(model, folder, source_root)
            check_curated_facts_not_stale(model, folder)
            n_ids, allowlisted = check_source_identifiers_resolve(model, folder)
            total_identifiers_checked += n_ids
            total_identifiers_allowlisted += len(allowlisted)
            if source_root is not None:
                total_citations_checked += check_source_citations(
                    model, folder, source_root,
                    ["card.md", "processes.md", "failures.md", "recipes.md", "version.md", "sources.md"])
                check_catalogs_fresh_build(model, folder, source_root)

        valid_source_ids = set(re.findall(r"^## ([A-Za-z]\d+)$", (folder / "sources.md").read_text(), re.M))
        total_facts += check_structured_layers(model, folder, valid_source_ids, valid_checks)

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
    print(f"PASS: {total_facts} structured-layer facts validated (source ids, from-anchors, basis, coverage)")
    print(f"PASS: {total_overlay_rows_checked} curated overlay rows resolve to a real "
          f"catalog entry (kinds_overlay.yaml variables in outputs.yaml, options_overlay.yaml "
          f"internal_option_names in physics_options.yaml)")
    print("PASS: every generation-2 curated structured-layer fact's confirmed_against hash "
          "matches its cited prose paragraph's current text (no stale re-confirmation)")
    print(f"PASS: {total_identifiers_checked} backticked model identifiers in card/processes/"
          f"failures/recipes.md resolve through hcm_lookup.py (exact or alias) or "
          f"lookup_allowlist.yaml ({total_identifiers_allowlisted} allowlisted)")
    if source_root is not None:
        print(f"PASS: {total_citations_checked} prose path:line citations resolved against "
              f"--source-root, generated catalogs match a fresh build (modulo evidence upgrades), "
              f"and every overlay citation resolved")
    else:
        print("Skipped source-root checks (path:line citation resolution, fresh-build catalog "
              "equality, overlay citation resolution); pass --source-root <pinned-checkout> to run them.")
    print("PASS: linear-triangle quadrature mean=2.5; fixed-domain mass change=-5400 kg")
    print("These are static/arithmetic checks, not model or agent-behavior validation.")
    check_no_private_strings()
    check_freshness()
    if "--network" in sys.argv:
        check_urls()
    else:
        print(f"Skipped {len(external_urls())} external URLs; pass --network to verify them.")


if __name__ == "__main__":
    main()
