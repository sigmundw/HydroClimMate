"""_miniyaml.py -- strict-subset YAML reader/writer for HydroClimMate model-pack layers
(see hydroclimmate/references/models/SCHEMA.md "YAML subset" section).

This is deliberately NOT a general YAML implementation. The pack YAML files are written in
one restricted subset:

  - a single top-level block mapping (``key: value`` lines, 2-space indents);
  - a mapping value is either a scalar, a JSON-compatible flow sequence/mapping written
    inline (``[...]`` / ``{...}``), or an indented nested block (a block mapping, or a
    block list of ``- `` items, each item itself a block mapping);
  - every string scalar is always double-quoted with JSON-style escaping;
  - no anchors/aliases, no multi-line scalars, no tabs, no flow scalars other than
    ``null``/``true``/``false``/numbers/double-quoted strings.

Every value that is not itself the start of a nested block is therefore always a single
line of valid JSON, so this reader parses those spans with the stdlib ``json`` module and
only implements the block/indentation walking itself. Because of this, every file this
module can read is also ordinary, valid YAML and loads to the identical Python object
under PyYAML's ``yaml.safe_load`` -- tools in this repo prefer PyYAML when importable and
fall back to this module only when it is not (see ``hcm_check.py``, ``hcm_lookup.py``,
``build_index.py``, ``selftest.py``, ``validate_catalogs.py``).

Regenerate pack YAML with ``tools/extract_pack.py`` (catalogs) or by hand-editing the
curated layers directly; do not write a second tool that reformats these files.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

__all__ = ["load", "dump", "load_file", "write_file", "MiniYamlError"]

_KEY_RE = re.compile(r'^([A-Za-z_][A-Za-z0-9_]*):[ \t]*(.*)$')
_LIST_ITEM_RE = re.compile(r'^-[ \t]+(.*)$')


class MiniYamlError(ValueError):
    """Raised when a document is not in the strict subset this module reads."""


# --------------------------------------------------------------------------------------
# Reader
# --------------------------------------------------------------------------------------

def load(text):
    """Parse a strict-subset YAML document (as produced by `dump`) into plain Python
    dict/list/str/int/float/bool/None data. Comment lines (``#...``) and blank lines are
    ignored; a leading generated-file header comment block is skipped this way."""
    lines = _tokenize(text)
    if not lines:
        return {}
    pos = [0]
    value = _parse_block(lines, lines[0][0], pos)
    if pos[0] != len(lines):
        raise MiniYamlError(f"trailing content at line index {pos[0]}: {lines[pos[0]]}")
    return value


def _tokenize(text):
    """Return a list of (indent, content) pairs for every non-blank, non-comment line."""
    out = []
    for lineno, raw in enumerate(text.split("\n"), start=1):
        if "\t" in raw:
            raise MiniYamlError(f"line {lineno}: tab character not allowed")
        line = raw.rstrip("\r")
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("#"):
            continue
        indent = len(line) - len(line.lstrip(" "))
        out.append((indent, stripped))
    return out


def _parse_block(lines, indent, pos):
    """Parse a block mapping whose keys sit at exactly `indent`, starting at lines[pos[0]]."""
    result = {}
    while pos[0] < len(lines):
        cur_indent, content = lines[pos[0]]
        if cur_indent < indent:
            break
        if cur_indent > indent:
            raise MiniYamlError(f"unexpected indent {cur_indent} (expected {indent}): {content!r}")
        m = _KEY_RE.match(content)
        if not m:
            raise MiniYamlError(f"expected 'key: value' at indent {indent}: {content!r}")
        key, rest = m.group(1), m.group(2)
        pos[0] += 1
        if rest != "":
            result[key] = json.loads(rest)
            continue
        # Nested block follows, or the value is genuinely absent (null).
        if pos[0] < len(lines) and lines[pos[0]][0] > indent:
            nxt_indent, nxt_content = lines[pos[0]]
            if _LIST_ITEM_RE.match(nxt_content):
                result[key] = _parse_list(lines, nxt_indent, pos)
            else:
                result[key] = _parse_block(lines, nxt_indent, pos)
        else:
            result[key] = None
    return result


def _parse_list(lines, indent, pos):
    """Parse a block list of mappings whose ``- `` markers sit at exactly `indent`."""
    items = []
    while pos[0] < len(lines):
        cur_indent, content = lines[pos[0]]
        if cur_indent != indent:
            break
        m = _LIST_ITEM_RE.match(content)
        if not m:
            break
        first_field = m.group(1)
        pos[0] += 1
        item_lines = [(indent + 2, first_field)]
        while pos[0] < len(lines) and lines[pos[0]][0] >= indent + 2:
            item_lines.append(lines[pos[0]])
            pos[0] += 1
        sub_pos = [0]
        items.append(_parse_block(item_lines, indent + 2, sub_pos))
        if sub_pos[0] != len(item_lines):
            raise MiniYamlError(f"could not parse full list item near indent {indent}")
    return items


# --------------------------------------------------------------------------------------
# Writer
# --------------------------------------------------------------------------------------

def dump(obj, header_lines=None):
    """Render `obj` (a dict) as a strict-subset YAML document. `header_lines`, if given,
    is a list of plain-text lines emitted as a leading ``# `` comment block (generator,
    source commits, "do not hand-edit" notice)."""
    if not isinstance(obj, dict):
        raise MiniYamlError("top-level document must be a mapping")
    out = []
    if header_lines:
        for line in header_lines:
            out.append(("# " + line) if line else "#")
    out.extend(_emit_mapping_body(obj, 0))
    return "\n".join(out) + "\n"


def _is_flat(value):
    """A dict all of whose values are themselves scalars (no list/dict) can render as a
    one-level nested block mapping. Anything deeper renders inline as JSON flow."""
    if not isinstance(value, dict):
        return False
    return all(not isinstance(v, (dict, list)) for v in value.values())


def _format_float(f):
    """JSON-valid float text that YAML's implicit float resolver also recognizes.
    Plain json.dumps can emit e.g. "-1e+33" (no decimal point before the exponent),
    which is valid JSON but which YAML 1.1's float regex does NOT match -- PyYAML
    would then load it back as a string, not a float. Always keep a decimal point."""
    s = repr(f) if f == f and f not in (float("inf"), float("-inf")) else json.dumps(f)
    if "e" in s or "E" in s:
        mantissa, exp = re.split("[eE]", s.replace("E", "e"), maxsplit=1)
        if "." not in mantissa:
            mantissa += ".0"
        if not exp.startswith(("+", "-")):
            exp = "+" + exp
        s = f"{mantissa}e{exp}"
    elif "." not in s:
        s += ".0"
    return s


def _encode(value):
    """Custom JSON-compatible encoder (used for both flow values and bare scalars):
    behaves like json.dumps except floats always keep a decimal point (see
    `_format_float`), so every emitted number reads back identically under PyYAML."""
    if value is None:
        return "null"
    if value is True:
        return "true"
    if value is False:
        return "false"
    if isinstance(value, float):
        return _format_float(value)
    if isinstance(value, int):
        return str(value)
    if isinstance(value, str):
        return json.dumps(value)
    if isinstance(value, list):
        return "[" + ", ".join(_encode(v) for v in value) + "]"
    if isinstance(value, dict):
        return "{" + ", ".join(f"{json.dumps(k)}: {_encode(v)}" for k, v in value.items()) + "}"
    raise MiniYamlError(f"unsupported value type: {type(value)!r}")


def _inline(value):
    """JSON-compatible flow rendering: valid on one line, valid YAML, valid JSON."""
    return _encode(value)


def _emit_mapping_body(d, indent):
    """Return the lines for the *fields* of mapping `d`, each field starting at `indent`."""
    pad = "  " * indent
    lines = []
    for key, value in d.items():
        lines.extend(_emit_field(pad, key, value, indent))
    return lines


def _emit_field(pad, key, value, indent):
    if isinstance(value, list) and value and all(isinstance(x, dict) for x in value):
        out = [f"{pad}{key}:"]
        out.extend(_emit_list_body(value, indent + 1))
        return out
    if _is_flat(value) and value:
        out = [f"{pad}{key}:"]
        out.extend(_emit_mapping_body(value, indent + 1))
        return out
    if isinstance(value, dict) and not value:
        return [f"{pad}{key}: {{}}"]
    return [f"{pad}{key}: {_scalar_or_flow(value)}"]


def _emit_list_body(items, indent):
    pad = "  " * indent
    lines = []
    for item in items:
        if not isinstance(item, dict) or not item:
            lines.append(f"{pad}- {_scalar_or_flow(item)}")
            continue
        keys = list(item.keys())
        first_key = keys[0]
        first_lines = _emit_field("", first_key, item[first_key], 0)
        # First line of the first field goes after "- "; any of its own nested-block
        # continuation lines are re-indented under the item's field column.
        lines.append(f"{pad}- {first_lines[0]}")
        for cont in first_lines[1:]:
            lines.append(f"{pad}  {cont}")
        for key in keys[1:]:
            for out_line in _emit_field(f"{pad}  ", key, item[key], indent + 1):
                lines.append(out_line)
    return lines


def _scalar_or_flow(value):
    return _encode(value)


# --------------------------------------------------------------------------------------
# Convenience: the one loader every tool should call
# --------------------------------------------------------------------------------------

def load_file(path):
    """Load a pack YAML file, preferring PyYAML (`yaml.safe_load`) when importable and
    falling back to this module's own strict-subset `load` when it is not. Every file
    this repo writes is verified (see tools/selftest.py) to load identically either way."""
    text = Path(path).read_text(encoding="utf-8")
    try:
        import yaml
    except ImportError:
        return load(text)
    return yaml.safe_load(text)


def write_file(obj, path, header_lines=None):
    """Write `obj` to `path` as a strict-subset YAML document (see `dump`)."""
    Path(path).write_text(dump(obj, header_lines=header_lines))
