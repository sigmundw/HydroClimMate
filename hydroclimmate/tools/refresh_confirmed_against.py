#!/usr/bin/env python3
"""refresh_confirmed_against.py -- the one-command step to re-sync a pack's curated
structured-layer facts with the CURRENT text of the prose paragraphs they cite, after a
prose correction. Covers EVERY curated/*.yaml file the pack actually has (derived by
listing the directory, not a hard-coded stem list -- a curated file added later, or one
whose facts use the where/evidence/scope shape (kinds_overlay.yaml/options_overlay.yaml)
rather than source/basis/from, is picked up automatically as long as its own facts carry
a `from: {file, anchor}` pointer; see references/models/SCHEMA.md).

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


def _iter_facts_with_from(node):
    """Walk any curated-layer shape (source/scope/basis/from, or where/evidence/scope
    with an optional from/confirmed_against pair): a fact is any dict carrying a `from`
    field shaped {file, anchor} -- regardless of which of the two citation shapes the
    rest of the dict otherwise uses."""
    if isinstance(node, dict):
        if "from" in node and isinstance(node["from"], dict) and "anchor" in node["from"]:
            yield node
        for v in node.values():
            yield from _iter_facts_with_from(v)
    elif isinstance(node, list):
        for item in node:
            yield from _iter_facts_with_from(item)


def refresh_pack(pack_dir, dry_run=False):
    """Returns (updated_files, n_examined): `updated_files` is [(stem, n_changed), ...]
    for files that had at least one stale hash refreshed; `n_examined` is the total
    number of curated/*.yaml files this pass actually opened, regardless of whether any
    of their facts needed refreshing -- a pack with a curated/ directory that exists but
    holds files with no `from`-shaped facts (or no facts at all) still counts as
    examined, so `main()` can tell "everything already matched" apart from "there was
    nothing to check" (D0: the previous hard-coded stem list silently examined ZERO
    files for a pack whose only curated file used a stem not in that list, and reported
    the same reassuring message either way)."""
    updated_files = []
    curated_dir = pack_dir / "curated"
    if not curated_dir.is_dir():
        return updated_files, 0
    paths = sorted(curated_dir.glob("*.yaml"))
    for path in paths:
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
            updated_files.append((path.stem, changed))
    return updated_files, len(paths)


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
    updated, n_examined = refresh_pack(pack_dir, dry_run=args.dry_run)
    if n_examined == 0:
        print(f"{args.pack}: no curated layer file found (curated/ is missing, empty, "
              f"or holds no *.yaml files) -- nothing to refresh.")
    elif not updated:
        print(f"{args.pack}: all confirmed_against hashes already match the current "
              f"prose ({n_examined} curated file(s) examined).")
    for stem, n in updated:
        print(f"{args.pack}/curated/{stem}.yaml: {n} fact(s) {'would be ' if args.dry_run else ''}refreshed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
