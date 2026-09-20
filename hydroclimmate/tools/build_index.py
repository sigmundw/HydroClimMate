#!/usr/bin/env python3
"""build_index.py — generates a pack's index.json (K-index) from its other structured
layers (interface.json, switches.json, pitfalls.json) plus its Markdown headings.

index.json carries no claims of its own: every fact in it already exists in the layer it
was collected from. Regenerate and diff rather than hand-edit; evals/check_knowledge.py
asserts the committed file equals a fresh build.

Usage: python3 build_index.py <pack-name> [--write]
With no --write, prints the built index to stdout without touching the file.
"""
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
MODELS_DIR = HERE.parent / "references/models"


def _load(pack_dir, filename):
    path = pack_dir / filename
    return json.loads(path.read_text()) if path.is_file() else None


def _entry(entries, name, kind):
    key = (name, kind)
    if key not in entries:
        entries[key] = {"name": name, "kind": kind, "declared_in": set(),
                         "from": [], "related_switches": set(), "related_pitfalls": set()}
    return entries[key]


def _add_from(entry, fact):
    if isinstance(fact, dict) and isinstance(fact.get("from"), dict):
        item = (fact["from"].get("file"), fact["from"].get("anchor"))
        if item not in entry["from"]:
            entry["from"].append(item)


def build_index_for_pack(pack_dir):
    pack_dir = Path(pack_dir)
    interface = _load(pack_dir, "interface.json")
    switches = _load(pack_dir, "switches.json")
    pitfalls = _load(pack_dir, "pitfalls.json")

    entries = {}

    if interface:
        for fact in interface.get("files", []):
            e = _entry(entries, fact.get("file_kind"), "file")
            e["declared_in"].add("interface.json")
            _add_from(e, fact)
        for fact in interface.get("inputs", []):
            e = _entry(entries, fact.get("variable"), "input")
            e["declared_in"].add("interface.json")
            _add_from(e, fact)
        for fact in interface.get("outputs", []):
            e = _entry(entries, fact.get("variable"), "output")
            e["declared_in"].add("interface.json")
            _add_from(e, fact)

    switch_field_owner = {}  # lowercased field name -> switch name, for related_switches
    if switches:
        for sw in switches.get("switches", []):
            sw_name = sw.get("name")
            e = _entry(entries, sw_name, "switch")
            e["declared_in"].add("switches.json")
            for part in ("structural_change", "expected_scaling_variable"):
                if sw.get(part):
                    _add_from(e, sw[part])
            for part in ("exchanged_fields", "untouched_fields"):
                fact = sw.get(part)
                if not fact:
                    continue
                for field_name in fact.get("fields", []):
                    fe = _entry(entries, field_name, "variable")
                    fe["declared_in"].add("switches.json")
                    _add_from(fe, fact)
                    fe["related_switches"].add(sw_name)
                    switch_field_owner.setdefault(field_name.lower(), set()).add(sw_name)
            scaling = sw.get("expected_scaling_variable")
            if scaling and scaling.get("variable"):
                ve = _entry(entries, scaling["variable"], "variable")
                ve["declared_in"].add("switches.json")
                _add_from(ve, scaling)
                ve["related_switches"].add(sw_name)

    if pitfalls:
        for pf in pitfalls.get("pitfalls", []):
            detect = pf.get("detect")
            if not detect:
                continue
            detect_anchor = (detect.get("from") or {}).get("anchor")
            for entry in entries.values():
                if any(anchor == detect_anchor for _file, anchor in entry["from"]):
                    entry["related_pitfalls"].add(pf["id"])
            hint = detect.get("control_var_hint")
            if hint:
                he = entries.get((hint, "variable"))
                if he:
                    he["related_pitfalls"].add(pf["id"])

    result = []
    for (name, kind), e in sorted(entries.items(), key=lambda kv: (kv[0][0] or "", kv[0][1])):
        result.append({
            "name": name,
            "kind": kind,
            "declared_in": sorted(e["declared_in"]),
            "from": [{"file": f, "anchor": a} for f, a in sorted(e["from"])],
            "related_switches": sorted(e["related_switches"]),
            "related_pitfalls": sorted(e["related_pitfalls"]),
        })

    return {"pack": pack_dir.name, "generated_by": "tools/build_index.py", "entries": result}


def main(argv=None):
    argv = argv if argv is not None else sys.argv[1:]
    if not argv:
        sys.exit("usage: build_index.py <pack-name> [--write]")
    pack_name = argv[0]
    write = "--write" in argv
    pack_dir = MODELS_DIR / pack_name
    if not pack_dir.is_dir():
        sys.exit(f"ERROR: no such pack directory: {pack_dir}")
    index = build_index_for_pack(pack_dir)
    text = json.dumps(index, indent=2) + "\n"
    if write:
        (pack_dir / "index.json").write_text(text)
        print(f"wrote {pack_dir / 'index.json'}")
    else:
        print(text)


if __name__ == "__main__":
    main()
