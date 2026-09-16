"""Offline structural checks and independent arithmetic cases; no model execution."""
import json
import re
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "hydroclimmate"


def anchors(text):
    return {
        re.sub(r"[^\w\- ]", "", heading.lower()).replace(" ", "-")
        for heading in re.findall(r"^#+ (.+)$", text, re.M)
    }


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


if __name__ == "__main__":
    main()
