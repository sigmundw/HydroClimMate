#!/usr/bin/env python3
"""selftest_review_packet.py — exercises hcm_review_packet.py against small
synthetic files in a temp directory. Stdlib only. Run directly:
`python3 selftest_review_packet.py`.
"""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
TOOL = HERE / "hcm_review_packet.py"


def run(*args):
    result = subprocess.run([sys.executable, str(TOOL), *args], capture_output=True, text=True)
    return result.returncode, result.stdout, result.stderr


def expect(condition, message):
    if not condition:
        print(f"FAIL: {message}")
        return False
    print(f"ok: {message}")
    return True


def main():
    ok = True
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        goal = tmp / "goal.md"
        goal.write_text("# Goal\nDoes the response scale with the control field?\n")
        record = tmp / "experiment-record.md"
        record.write_text("# Experiment record\nspearman_min: 0.9\n")
        decision = tmp / "decisions.md"
        decision.write_text("## 2026-09-19 - Adopted threshold\n")
        artefact = tmp / "run_b.nc"
        artefact.write_bytes(b"not a real netcdf, just bytes for the packet test")
        report = tmp / "check_report.txt"
        report.write_text("VERDICT scales_with_control: VERIFIED\n")

        out_dir = tmp / "packet"
        rc, out, err = run(
            "--goal", str(goal), "--experiment-record", str(record),
            "--decisions", str(decision), "--artefact", str(artefact),
            "--check-report", str(report), "--out", str(out_dir),
        )
        ok &= expect(rc == 0, f"packet build exit code 0\n{out}\n{err}")
        manifest_path = out_dir / "MANIFEST.json"
        ok &= expect(manifest_path.is_file(), "MANIFEST.json written")
        manifest = json.loads(manifest_path.read_text())
        ok &= expect(len(manifest["files"]) == 5, f"manifest lists 5 files: {manifest['files']}")
        ok &= expect((out_dir / "REVIEWER_INSTRUCTIONS.txt").is_file(), "reviewer instructions written")
        instr = (out_dir / "REVIEWER_INSTRUCTIONS.txt").read_text()
        ok &= expect("SUPPORTED" in instr and "CONTRADICTED" in instr and "INSUFFICIENT EVIDENCE" in instr,
                     "instructions carry the three-state vocabulary")
        ok &= expect("no authority to modify" in instr, "instructions state no authority to modify/re-run/recover")

        # Refusal of narrative-style inputs.
        rc, out, err = run(
            "--goal", str(goal), "--out", str(tmp / "packet2"),
            "--summary", "everything went fine",
        )
        ok &= expect(rc != 0, "narrative --summary is refused (nonzero exit)")
        ok &= expect("REFUSED" in err, f"refusal message printed\n{out}\n{err}")

        # Refuses to overwrite a non-empty output directory.
        rc, out, err = run("--goal", str(goal), "--out", str(out_dir))
        ok &= expect(rc != 0, "refuses to reuse a non-empty --out directory")

    if ok:
        print("\nALL SELFTESTS PASSED")
        return 0
    print("\nSELFTEST FAILURES ABOVE")
    return 1


if __name__ == "__main__":
    sys.exit(main())
