"""Offline structural checks and independent arithmetic cases; no model execution.

Pass --network to additionally verify that every cited external URL still resolves.
That check is opt-in so the default run stays offline and deterministic.
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

# Structured layers (K2-K6, see references/models/SCHEMA.md) are being rolled out pack
# by pack (B9 does hrldas-noahmp only; B10 does the other seven). Flip to True once every
# pack carries pack.json -- then a pack with no pack.json is a validator failure, not a gap.
REQUIRE_STRUCTURED_LAYERS = True

BASIS_VALUES = {"source_read", "observed_in_output", "unverified"}
STRUCTURED_LAYER_FILES = ("interface.json", "switches.json", "pitfalls.json", "workflows.json",
                          "index.json", "selftest.json")

sys.path.insert(0, str(PACKAGE / "tools"))


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


def check_structured_layers(model, folder, valid_source_ids, valid_checks):
    """Validate a pack's optional K2-K6 JSON layers (see SCHEMA.md). Returns the number
    of facts found, for the caller's summary line."""
    pack_json = folder / "pack.json"
    if not pack_json.is_file():
        assert not REQUIRE_STRUCTURED_LAYERS, (
            model, "pack.json is required (REQUIRE_STRUCTURED_LAYERS=True) but missing")
        return 0

    try:
        manifest = json.loads(pack_json.read_text())
    except json.JSONDecodeError as exc:
        raise AssertionError((model, "pack.json does not parse", str(exc))) from exc

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
            doc = json.loads(layer_path.read_text())
        except json.JSONDecodeError as exc:
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

        if filename == "pitfalls.json":
            check_pitfalls_json(model, folder, doc, valid_checks)
        if filename == "index.json":
            check_index_matches_build(model, folder, doc)

    return fact_count


def check_index_matches_build(model, folder, committed_index):
    """index.json is generated, never hand-written (Addendum 2): it must equal a fresh
    build from the pack's other layers, so it can never drift or carry its own claims."""
    import build_index
    fresh = build_index.build_index_for_pack(folder)
    assert fresh == committed_index, (
        model, "index.json does not match a fresh build -- regenerate with "
        "tools/build_index.py <pack> --write instead of hand-editing")


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
    for model in models:
        folder = PACKAGE / "references/models" / model
        assert {p.name for p in folder.glob("*.md")} == {
            "overview.md", "execution.md", "outputs.md", "pitfalls.md", "sources.md"
        }, model
        for name in ("overview", "execution", "outputs"):
            text = (folder / f"{name}.md").read_text()
            assert re.search(r"\[[A-Z]\d+\]\(sources.md#[a-z]\d+\)", text), (model, name)
        check_pitfalls(model, folder)
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
    print("PASS: linear-triangle quadrature mean=2.5; fixed-domain mass change=-5400 kg")
    print("These are static/arithmetic checks, not model or agent-behavior validation.")
    check_freshness()
    if "--network" in sys.argv:
        check_urls()
    else:
        print(f"Skipped {len(external_urls())} external URLs; pass --network to verify them.")


if __name__ == "__main__":
    main()
