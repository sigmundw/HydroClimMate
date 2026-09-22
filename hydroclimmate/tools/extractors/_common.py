"""extractors/_common.py -- generic, pack-agnostic helpers shared by every per-pack
extractor module under tools/extractors/. Nothing model-specific lives here: file
reading, path relativization, hashing, and the two output writers (JSON for
machine-only files, strict-subset YAML for pack layers). Each extractor module
(hrldas_noahmp.py, vic.py, ...) supplies its own header text and per-fact citation
shape, since those are pack-specific.
"""
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import _miniyaml  # noqa: E402


def read_lines(path):
    """1-indexed lines: lines[1] is the file's first line."""
    text = path.read_text(encoding="utf-8", errors="replace")
    return [None] + text.split("\n")


def relpath(root, path):
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def sha256_of(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(obj, out_path):
    """Machine-only files stay JSON (catalogs/MANIFEST.json: hashes and counts)."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(obj, indent=2, default=str) + "\n")


def write_yaml(obj, out_path, header_lines):
    """Pack YAML layers a person or agent reads: strict-subset YAML (see
    _miniyaml.py and SCHEMA.md). `obj` must already be a plain dict of JSON-safe
    values (dict/list/str/int/float/bool/None). `header_lines` is the module's own
    generated-file header (generator command, source commit(s))."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(_miniyaml.dump(obj, header_lines=header_lines))
