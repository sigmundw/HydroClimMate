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
        return int(code) < 400, code
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


def check_freshness():
    """Report how old each pack's source review is. Floating URLs decay quietly."""
    stale = []
    for source in sorted(PACKAGE.glob("references/models/*/sources.md")):
        match = re.search(r"^Checked:\s*(\d{4})-(\d{2})-(\d{2})", source.read_text(), re.M)
        assert match, f"{source} has no 'Checked: YYYY-MM-DD' line"
        age = (date.today() - date(*map(int, match.groups()))).days
        if age > STALE_DAYS:
            stale.append((source.parent.name, age))
    if stale:
        for model, age in stale:
            print(f"WARN: {model} sources last checked {age} days ago (limit {STALE_DAYS})")
    else:
        print(f"PASS: all five source packs re-checked within {STALE_DAYS} days")


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

    start, end = "<!-- ROUTING TABLE:", "<!-- END ROUTING TABLE -->"
    routes = []
    for name in ("SKILL.md", "AGENTS.md"):
        text = (PACKAGE / name).read_text()
        routes.append(text[text.index(start):text.index(end)])
        assert "v0.6" in text
    assert routes[0] == routes[1], "Entrypoint route drift"

    models = ("hrldas-noahmp", "wrf-urban", "ctsm", "rbm", "issm")
    for model in models:
        folder = PACKAGE / "references/models" / model
        assert {p.name for p in folder.glob("*.md")} == {
            "overview.md", "execution.md", "outputs.md", "sources.md"
        }, model
        for name in ("overview", "execution", "outputs"):
            text = (folder / f"{name}.md").read_text()
            assert re.search(r"\[[A-Z]\d+\]\(sources.md#[a-z]\d+\)", text), (model, name)

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
    print(f"PASS: {count} package links/anchors, five source-linked packs, routes, fixtures")
    print("PASS: linear-triangle quadrature mean=2.5; fixed-domain mass change=-5400 kg")
    print("These are static/arithmetic checks, not model or agent-behavior validation.")
    check_freshness()
    if "--network" in sys.argv:
        check_urls()
    else:
        print(f"Skipped {len(external_urls())} external URLs; pass --network to verify them.")


if __name__ == "__main__":
    main()
