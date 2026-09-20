#!/usr/bin/env python3
"""hcm_review_packet.py — assemble exactly what an independent reviewer may see.

Information separation between an executor and a reviewer is a checkable
property, not a promise the executor makes in prose. This tool copies a
declared set of inputs (a goal file, an experiment record, decision records,
raw artefacts and check-report outputs) into a packet directory, writes a
MANIFEST.json listing exactly what was included, and refuses anything that
looks like executor narrative rather than a primary record.

It has no authority to modify, re-run or recover anything, and it does not
judge whether the packet is sufficient for the claim being reviewed — that
judgement is the reviewer's and, on disagreement, the research owner's. See
references/review.md for how the packet is used.
"""
import argparse
import hashlib
import json
import os
import shutil
import sys
from datetime import datetime, timezone

# Any of these option names is refused outright: they invite exactly the
# executor narrative the reviewer must not receive.
REFUSED_FLAGS = {"summary", "narrative", "rationale", "explanation", "notes"}

LARGE_FILE_BYTES = 50 * 1024 * 1024  # above this, record a checksum instead of copying

REVIEWER_INSTRUCTIONS = """\
REVIEWER INSTRUCTIONS (read before opening the packet)

You have the packet's contents and nothing else the executor said about them.
Do not ask the executor to explain the packet; treat this as the whole record.

For each claim under review, answer exactly one of:
  SUPPORTED            — the packet's evidence supports the claim; say where.
  CONTRADICTED         — the packet's evidence contradicts the claim; say where.
  INSUFFICIENT EVIDENCE — the packet does not contain enough to decide either way.

Cite the specific file and location (line, variable, table row) behind every
answer. A deterministic check's VIOLATED verdict in a check report cannot be
overridden by prose elsewhere in the packet, from the executor or from you.

You have no authority to modify, re-run, or recover anything in this packet
or in the underlying project. If you disagree with the executor about a
finding, or the executor disagrees with you, record both positions; final
acceptance belongs to the research owner, not to either of you.

If you are the same model (and similar prompting) as the executor, say so in
your report: a same-model reviewer tends to share the executor's blind spots
and this is a limit on what your agreement is worth, not a formality.
"""


def sha256_of(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def add_entry(manifest, packet_dir, category, src_path):
    if not os.path.isfile(src_path):
        sys.exit(f"ERROR: {category} path does not exist or is not a file: {src_path}")
    size = os.path.getsize(src_path)
    checksum = sha256_of(src_path)
    dest_name = f"{category}__{len(manifest['files'])}__{os.path.basename(src_path)}"
    entry = {
        "category": category,
        "source_path": os.path.abspath(src_path),
        "sha256": checksum,
        "size_bytes": size,
    }
    if size > LARGE_FILE_BYTES:
        entry["copied"] = False
        entry["note"] = "file exceeds the copy-size limit; checksum recorded, original left in place"
    else:
        dest_path = os.path.join(packet_dir, dest_name)
        shutil.copy2(src_path, dest_path)
        entry["copied"] = True
        entry["packet_path"] = dest_name
    manifest["files"].append(entry)


def build_parser():
    parser = argparse.ArgumentParser(
        prog="hcm_review_packet.py",
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--goal", required=True, help="Path to the goal/claim statement file")
    parser.add_argument("--experiment-record", help="Path to the project's EXPERIMENT.md-based record")
    parser.add_argument("--decisions", action="append", default=[],
                         help="Path to a decisions record; repeatable")
    parser.add_argument("--artefact", action="append", default=[],
                         help="Path to a raw artefact (data file, log, figure); repeatable")
    parser.add_argument("--check-report", action="append", default=[],
                         help="Path to a hcm_check.py output saved to a file; repeatable")
    parser.add_argument("--out", required=True, help="Directory to create for the packet")
    for flag in sorted(REFUSED_FLAGS):
        parser.add_argument(f"--{flag}", help=argparse.SUPPRESS)
    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)

    for flag in REFUSED_FLAGS:
        if getattr(args, flag, None):
            sys.exit(
                f"REFUSED: --{flag} is executor narrative, not a primary record. "
                "The reviewer must work only from the goal file, experiment record, "
                "decisions, artefacts and check reports — not from the executor's own "
                "account of what happened. Put anything factual this option was meant "
                "to carry into the experiment record or a decision entry instead."
            )

    if os.path.exists(args.out):
        if os.listdir(args.out):
            sys.exit(f"ERROR: --out {args.out} already exists and is not empty")
    else:
        os.makedirs(args.out)

    manifest = {
        "created_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "tool": "hcm_review_packet.py",
        "files": [],
    }

    add_entry(manifest, args.out, "goal", args.goal)
    if args.experiment_record:
        add_entry(manifest, args.out, "experiment_record", args.experiment_record)
    for d in args.decisions:
        add_entry(manifest, args.out, "decisions", d)
    for a in args.artefact:
        add_entry(manifest, args.out, "artefact", a)
    for c in args.check_report:
        add_entry(manifest, args.out, "check_report", c)

    if not any(e["category"] in ("experiment_record", "check_report") for e in manifest["files"]):
        print("WARNING: packet has no experiment record and no check report — "
              "a reviewer will have only the goal, decisions and raw artefacts to work from.",
              file=sys.stderr)

    manifest_path = os.path.join(args.out, "MANIFEST.json")
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)

    instructions_path = os.path.join(args.out, "REVIEWER_INSTRUCTIONS.txt")
    with open(instructions_path, "w") as f:
        f.write(REVIEWER_INSTRUCTIONS)

    print(f"Packet written to {args.out}")
    print(f"  {len(manifest['files'])} file(s) recorded in MANIFEST.json")
    for e in manifest["files"]:
        status = "copied" if e["copied"] else "checksum only (large file)"
        print(f"  [{e['category']}] {e['source_path']} -> {status}")
    print()
    print(REVIEWER_INSTRUCTIONS)
    return 0


if __name__ == "__main__":
    sys.exit(main())
