#!/usr/bin/env python3
"""refresh_confirmed_against.py -- the one-command step to re-sync a pack's curated
structured-layer facts (curated/interface.yaml, curated/switches.yaml,
curated/checks.yaml, curated/workflows.yaml) with the CURRENT text of the prose
paragraphs they cite, after a prose correction.

This does NOT check whether a fact's statement still agrees with the prose -- a person
must read the diff and confirm that by hand (that is the point: it forces a human to
look). It only recomputes each fact's `confirmed_against` hash (see _anchor_hash.py) to
match the prose as it stands right now, so `evals/check_knowledge.py`'s drift check goes
quiet again once someone has actually re-confirmed the fact.

Usage:
  python3 tools/refresh_confirmed_against.py --pack hrldas-noahmp [--dry-run]

Run this AFTER hand-confirming every fact the drift check flagged (never as a way to
silence the check without reading the flagged facts).
"""
import argparse
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
MODELS_DIR = HERE.parent / "references/models"
sys.path.insert(0, str(HERE))
import _miniyaml  # noqa: E402
import _anchor_hash  # noqa: E402

CURATED_LAYER_STEMS = ("interface", "switches", "checks", "workflows")


def _iter_facts_with_from(node):
    if isinstance(node, dict):
        if "from" in node and isinstance(node["from"], dict) and "anchor" in node["from"]:
            yield node
        for v in node.values():
            yield from _iter_facts_with_from(v)
    elif isinstance(node, list):
        for item in node:
            yield from _iter_facts_with_from(item)


def refresh_pack(pack_dir, dry_run=False):
    updated_files = []
    for stem in CURATED_LAYER_STEMS:
        path = pack_dir / "curated" / f"{stem}.yaml"
        if not path.is_file():
            continue
        doc = _miniyaml.load_file(path)
        changed = 0
        prose_cache = {}
        for fact in _iter_facts_with_from(doc):
            frm = fact["from"]
            prose_path = pack_dir / frm["file"]
            if frm["file"] not in prose_cache:
                prose_cache[frm["file"]] = prose_path.read_text() if prose_path.is_file() else None
            text = prose_cache[frm["file"]]
            if text is None:
                continue
            new_hash = _anchor_hash.anchor_paragraph_hash(text, frm["anchor"])
            if new_hash != fact.get("confirmed_against"):
                changed += 1
                fact["confirmed_against"] = new_hash
        if changed:
            if not dry_run:
                header = _existing_header(path)
                _miniyaml.write_file(doc, path, header_lines=header)
            updated_files.append((stem, changed))
    return updated_files


def _existing_header(path):
    lines = []
    for line in path.read_text().split("\n"):
        if line.startswith("#"):
            lines.append(line[2:] if line.startswith("# ") else line[1:])
        else:
            break
    return lines


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--pack", required=True)
    p.add_argument("--dry-run", action="store_true", help="Report what would change, write nothing")
    args = p.parse_args(argv)
    pack_dir = MODELS_DIR / args.pack
    if not pack_dir.is_dir():
        sys.exit(f"ERROR: no such pack directory: {pack_dir}")
    updated = refresh_pack(pack_dir, dry_run=args.dry_run)
    if not updated:
        print(f"{args.pack}: all confirmed_against hashes already match the current prose.")
    for stem, n in updated:
        print(f"{args.pack}/curated/{stem}.yaml: {n} fact(s) {'would be ' if args.dry_run else ''}refreshed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
