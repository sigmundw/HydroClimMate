"""extractors/vic.py -- mechanical, deterministic extractor module for the VIC
knowledge pack's catalogs, dispatched by tools/extract_pack.py --pack vic. Every
function here reads the pinned VIC source tree given by --source-root and returns one
catalog's data (see SCHEMA.md). Nothing here is hand-typed: each fact is produced by a
regex/parse pass over the actual source files, and carries `where` = {file, line,
commit} pointing at the exact source line(s) it came from, plus a `driver` field
(classic | image | both) stating which driver(s) the fact applies to.

Pinned source: VIC tag 5.1.0, commit 14a371a8 (see version_scope in pack.yaml). Scope:
drivers classic and image only (the cesm and python drivers exist in the source tree
but are out of scope here). CODE WINS over docs/ -- any docs/ text quoted here is for
cross-reference only, and a disagreement between docs/ and code is recorded as a fact,
not silently resolved.

No real VIC output exists anywhere reachable by this pack: every fact here starts (and
stays) `evidence: source_read`. Input-FORMAT facts (global-parameter keys the file
parser actually recognizes, soil-file column counts, image parameter/domain/forcing
NetCDF variable names/dims/units) can additionally be confirmed against the public VIC
sample data (Stehekin) -- see tools/validate_catalogs.py's vic hook -- which upgrades
those facts' evidence to `confirmed_in_sample_input`. Nothing in this pack may ever
carry `observed_in_output` or `both`, since there is no model output to observe.

Source-root layout expected (matches the pinned VIC checkout):
  <root>/vic/drivers/shared_all/src/history_metadata.c      (OUT_* variable metadata)
  <root>/vic/drivers/shared_all/src/set_output_defaults.c   (default output streams)
  <root>/vic/drivers/shared_all/src/vic_history.c            (default aggregation type)
  <root>/vic/drivers/shared_all/include/vic_driver_shared_all.h  (OUT_*/AGG_TYPE_*/
                                                                    forcing-type enums)
  <root>/vic/drivers/classic/src/get_global_param.c          (classic global-param parser)
  <root>/vic/drivers/image/src/get_global_param.c            (image global-param parser)
  <root>/vic/drivers/shared_all/src/initialize_global.c      (global_param defaults)
  <root>/vic/drivers/shared_all/src/initialize_options.c     (options defaults)
  <root>/vic/vic_run/include/vic_def.h                       (option_struct fields)
  <root>/vic/vic_run/src/*.c                                 (physics: options.X branches)
  <root>/vic/drivers/shared_all/src/get_parameters.c         (model-parameters-file keys)
  <root>/vic/drivers/shared_all/src/initialize_parameters.c  (parameters-file defaults)
  <root>/vic/vic_run/include/vic_physical_constants.h        (physical constants)
  <root>/vic/drivers/classic/src/get_force_type.c            (classic forcing types)
  <root>/vic/drivers/shared_image/src/set_force_type.c       (image forcing types)
  <root>/vic/drivers/classic/src/read_soilparam.c            (classic soil-file columns)
  <root>/vic/drivers/classic/src/read_vegparam.c             (classic veg-file layout)
  <root>/vic/drivers/classic/src/read_veglib.c                (classic veg-library columns)
  <root>/vic/drivers/shared_image/src/vic_init.c              (image NetCDF param reads)
  <root>/vic/drivers/shared_image/src/state_metadata.c        (STATE_* variable metadata)
  <root>/vic/drivers/shared_image/src/vic_restore.c            (state-file consistency checks)
  <root>/vic/drivers/classic/src/make_in_and_outfiles.c        (classic output file naming)
  <root>/vic/drivers/classic/src/write_header.c                (classic ASCII/binary headers)
  <root>/vic/drivers/shared_image/src/vic_init_output.c        (image output NetCDF dims)
  <root>/vic/drivers/shared_image/src/vic_nc_info.c            (image output var dim order)
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import _miniyaml  # noqa: E402
sys.path.insert(0, str(Path(__file__).resolve().parent))
import _common  # noqa: E402

GENERATOR_VERSION = "1.0.0"
# Canonical short form: `git rev-parse --short=8` in the pinned checkout.
VIC_COMMIT = "14a371a8"
VIC_TAG = "5.1.0"
SAMPLE_DATA_COMMIT = "3f2dcb4"
SCOPE = f"VIC {VIC_COMMIT} (tag {VIC_TAG}); drivers classic + image; sample data {SAMPLE_DATA_COMMIT}"

PACK = "vic"
SOURCE_COMMITS = {"vic": VIC_COMMIT}

read_lines = _common.read_lines
relpath = _common.relpath


# --------------------------------------------------------------------------------------
# Generic C-source helpers (brace/paren matching, string-literal concatenation) -- none
# of this is VIC-specific; it would move to _common.py the day a second C-source pack
# needs it too, but stays local here for now (only one pack needs it).
# --------------------------------------------------------------------------------------

def where(rel_path, line, driver="both"):
    return {"file": rel_path, "line": line, "commit": f"vic@{VIC_COMMIT}", "driver": driver}


def fact(extra, rel_path, line, driver="both", evidence="source_read"):
    d = dict(extra)
    d["where"] = where(rel_path, line, driver)
    d["evidence"] = evidence
    d["scope"] = SCOPE
    return d


def _strip_line_comment(line):
    """Best-effort: drop a trailing '// ...' comment that is not inside a string
    literal. Does not handle /* */ block comments (handled separately where needed)."""
    in_str = False
    esc = False
    i = 0
    while i < len(line) - 1:
        c = line[i]
        if in_str:
            if esc:
                esc = False
            elif c == "\\":
                esc = True
            elif c == '"':
                in_str = False
        else:
            if c == '"':
                in_str = True
            elif c == "/" and line[i + 1] == "/":
                return line[:i]
        i += 1
    return line


def merged_block(lines, start_idx, max_lines=400):
    """Join lines[start_idx : start_idx+max_lines] into one string (newline-joined,
    None entries as empty), for brace/paren scanning that must see the whole
    statement/block regardless of line breaks."""
    end = min(start_idx + max_lines, len(lines))
    return "\n".join((lines[j] or "") for j in range(start_idx, end))


def matching_delim_text(blob, open_char, close_char, from_index=0):
    """Return (inner_text, end_index_in_blob) for the delimiter pair starting at the
    first `open_char` at or after from_index, string-literal aware (braces/parens
    inside a "..." literal are not counted)."""
    start = blob.find(open_char, from_index)
    if start == -1:
        return None, -1
    depth = 0
    in_str = False
    esc = False
    k = start
    while k < len(blob):
        c = blob[k]
        if in_str:
            if esc:
                esc = False
            elif c == "\\":
                esc = True
            elif c == '"':
                in_str = False
        else:
            if c == '"':
                in_str = True
            elif c == open_char:
                depth += 1
            elif c == close_char:
                depth -= 1
                if depth == 0:
                    return blob[start + 1:k], k
        k += 1
    return blob[start + 1:], len(blob)


_STR_LIT_RE = re.compile(r'"((?:[^"\\]|\\.)*)"')


def concat_c_string_literals(text):
    """Concatenate every adjacent double-quoted C string literal in `text` (C's own
    adjacent-literal concatenation), unescaping \\" and \\n/\\t. Returns None if no
    string literal is present."""
    parts = _STR_LIT_RE.findall(text)
    if not parts:
        return None
    out = []
    for p in parts:
        out.append(p.replace('\\"', '"').replace("\\n", " ").replace("\\t", " "))
    return re.sub(r"\s+", " ", "".join(out)).strip()


def first_top_level_comma_split(text):
    """Everything before the first comma that is not inside a string literal or a
    nested (), [] or {} -- i.e. a call's first argument's raw text."""
    depth = 0
    in_str = False
    esc = False
    for idx, c in enumerate(text):
        if in_str:
            if esc:
                esc = False
            elif c == "\\":
                esc = True
            elif c == '"':
                in_str = False
            continue
        if c == '"':
            in_str = True
        elif c in "([{":
            depth += 1
        elif c in ")]}":
            depth -= 1
        elif c == "," and depth == 0:
            return text[:idx]
    return text


def call_message_arg(lines, call_line_idx, call_name="log_err", max_lines=25):
    """For a call `call_name(...)` beginning at or after lines[call_line_idx], return
    the concatenated string-literal text of its first argument (the printf-style
    format/message string), or None if not found."""
    blob = merged_block(lines, call_line_idx, max_lines)
    m = re.search(re.escape(call_name) + r"\s*\(", blob)
    if not m:
        return None
    inner, _ = matching_delim_text(blob, "(", ")", from_index=m.start())
    if inner is None:
        return None
    return concat_c_string_literals(first_top_level_comma_split(inner))


# --------------------------------------------------------------------------------------
# C if/brace-stack tracking (VIC's uncrustify-formatted code puts one condition per
# `if (...) {`/`else if (...) {` line and a lone `}` on its own closing line almost
# everywhere this extractor scans -- checked by inspection of every file this module
# reads; a block that violates this convention would be under-gated, not over-gated,
# since an unmatched close just pops one level early).
# --------------------------------------------------------------------------------------

_C_IF_RE = re.compile(r"^\s*(?:\}\s*)?else\s+if\s*\((.*)\)\s*\{\s*$|^\s*if\s*\((.*)\)\s*\{\s*$")
_C_ELSE_RE = re.compile(r"^\s*\}?\s*else\s*\{\s*$")
_C_CLOSE_RE = re.compile(r"^\s*\}\s*(?:else\b.*)?$")
_C_BARE_BLOCK_OPEN_RE = re.compile(r"\{\s*(?://.*)?$")


def c_if_stack_by_line(lines, start, end):
    """Map line number -> list of currently-open `if (...)`/`else if (...)` condition
    strings, for lines start..end inclusive. A bare `else {` re-uses the immediately
    preceding sibling condition text prefixed with 'else of: ' (best-effort; VIC's own
    option-gating never actually uses else on the registration paths this extractor
    scans, so this is exercised rarely, if at all). Any OTHER line that opens a brace
    (`for (...) {`, `while (...) {`, `switch (...) {`, a function body's own `{`) pushes
    `None` instead of a condition, so the stack's depth still matches the source's
    actual brace nesting and a later close (`}`) pops the right frame -- without this,
    a `for`-loop's own closing brace silently pops the ENCLOSING if's condition instead
    of the loop's own (harmless-looking but corrupts every gate recorded after it; found
    by cross-checking catalogs/parameters.yaml's soil-column gates against the real
    ORGANIC_FRACT/SPATIAL_FROST/JULY_TAVG_SUPPLIED option guards, which the unfixed
    version silently dropped -- see the extraction report in the development record)."""
    stack = []
    out = {}
    last_if_text = None
    _if_opener_re = re.compile(r"^\s*(?:\}\s*)?else\s+if\s*\(|^\s*if\s*\(")
    skip_until = 0
    for i in range(start, end + 1):
        if i < skip_until:
            out[i] = list(stack)
            continue
        line = lines[i]
        if line is None:
            out[i] = list(stack)
            continue
        s = _strip_line_comment(line)
        m = _C_IF_RE.match(s)
        if m:
            out[i] = list(stack)
            cond = (m.group(1) or m.group(2) or "").strip()
            last_if_text = cond
            stack.append(cond)
            continue
        # A multi-line if/else-if condition (uncrustify wraps a long `||`/`&&` chain
        # onto a continuation line, e.g. vic_init.c's FCAN_SRC == FROM_VEGLIB ||
        # FCAN_SRC == FROM_VEGPARAM check) does not match the single-line _C_IF_RE
        # above -- merge forward to find its closing `) {` before giving up on it as
        # a bare block open (independent review C3: this exact case dropped fcanopy's gate).
        om = _if_opener_re.match(s)
        if om:
            blob = merged_block(lines, i, 6)
            inner, end_off = matching_delim_text(blob, "(", ")", from_index=om.end() - 1)
            if inner is not None and re.match(r"\s*\{", blob[end_off + 1:]):
                out[i] = list(stack)
                cond = re.sub(r"\s+", " ", inner).strip()
                last_if_text = cond
                stack.append(cond)
                # How many physical lines did the merged condition actually span?
                consumed_newlines = blob[:end_off].count("\n")
                skip_until = i + consumed_newlines + 1
                continue
        if _C_ELSE_RE.match(s):
            out[i] = list(stack)
            stack.append(f"else of: {last_if_text}" if last_if_text else "else")
            continue
        if _C_CLOSE_RE.match(s):
            out[i] = list(stack)
            if stack:
                stack.pop()
            continue
        if _C_BARE_BLOCK_OPEN_RE.search(s):
            out[i] = list(stack)
            stack.append(None)
            continue
        out[i] = list(stack)
    return out


def find_function_body(lines, name, return_type_hint=None):
    """(start, end) 1-indexed inclusive line range of a C function's `{ ... }` body,
    located by its name at the start of a line (K&R style: return type on its own
    line, `name(args)` on the next, `{` on the next -- VIC's consistent layout).
    Returns (None, None) if not found."""
    name_re = re.compile(r"^" + re.escape(name) + r"\s*\(")
    for i in range(1, len(lines)):
        line = lines[i]
        if line is None:
            continue
        if name_re.match(line.strip()):
            # scan forward (a few lines, for multi-line arg lists) to the opening brace
            for j in range(i, min(i + 20, len(lines))):
                if lines[j] and lines[j].strip() == "{":
                    blob = merged_block(lines, j, 100000)
                    _, end_off = matching_delim_text(blob, "{", "}", from_index=0)
                    # count newlines up to end_off to get the end line number
                    end_line = j + blob[:end_off].count("\n")
                    return i, end_line
    return None, None


# --------------------------------------------------------------------------------------
# outputs: OUT_* variables (name/units/description, default agg type, gating, nelem,
# default stream membership), classic ASCII/binary header & naming, image NetCDF dims.
# --------------------------------------------------------------------------------------

HDR = "vic/drivers/shared_all/include/vic_driver_shared_all.h"
HIST_META = "vic/drivers/shared_all/src/history_metadata.c"
SET_OUT_DEF = "vic/drivers/shared_all/src/set_output_defaults.c"
VIC_HISTORY = "vic/drivers/shared_all/src/vic_history.c"
STATE_META = "vic/drivers/shared_image/src/state_metadata.c"
VIC_RESTORE = "vic/drivers/shared_image/src/vic_restore.c"
VIC_STORE = "vic/drivers/shared_image/src/vic_store.c"
MAKE_IO_FILES = "vic/drivers/classic/src/make_in_and_outfiles.c"
WRITE_HEADER = "vic/drivers/classic/src/write_header.c"
VIC_INIT_OUTPUT = "vic/drivers/shared_image/src/vic_init_output.c"
VIC_NC_INFO = "vic/drivers/shared_image/src/vic_nc_info.c"


def parse_enum_block(lines, start_marker_line, prefix, stop_name):
    """Parse an unnamed `enum { NAME, /**< comment */ ... };` block starting at or
    after 1-indexed `start_marker_line`, collecting every `PREFIX_...` identifier plus
    its trailing Doxygen comment, up to and including `stop_name` (the loop-counter
    sentinel, e.g. N_OUTVAR_TYPES / N_STATE_VARS). Returns [{"name", "comment", "line"}]
    in declaration order (excludes the sentinel itself)."""
    entry_re = re.compile(
        r"^\s*(" + re.escape(prefix) + r"\w+)\s*,?\s*(?:/\*\*<\s*(.*?)\s*\*/)?\s*$")
    out = []
    for i in range(start_marker_line, len(lines)):
        line = lines[i]
        if line is None:
            continue
        s = line.strip()
        if s.startswith(stop_name):
            break
        m = entry_re.match(s)
        if m:
            out.append({"name": m.group(1), "comment": (m.group(2) or "").strip(), "line": i})
    return out


def parse_metadata_strcpy_block(lines, start, end, array_name, prefix):
    """Parse the `strcpy(<array_name>[<PREFIX>_X].<field>, <VALUE>);` block (used
    identically by set_output_met_data_info/history_metadata.c for out_metadata and by
    set_state_meta_data_info/state_metadata.c for state_metadata). VALUE is either a
    double-quoted C string (possibly split across lines / concatenated literals) or a
    reference to another entry's own field (out_metadata[OUT_Y].field) -- the latter is
    recorded as {"same_as": {"variable": Y, "field": field}} rather than guessed text.
    Returns {name: {field: value_or_same_as, "_lines": {field: line}, "_all_lines":
    {field: [line, ...]}}}. `_all_lines` keeps every assignment site for a field, not
    only the last (which is the one that survives at run time and is what `_lines`/the
    field value report) -- a field assigned more than once is either a harmless
    re-statement or, mechanically indistinguishable from that but real (found by
    independent review at OUT_TFOL_FBFLAG/OUT_VEGT), a copy-paste that leaves a DIFFERENT entry's
    field never assigned at all. Both are detectable from `_all_lines` plus which
    fields never appear as a key at all for some other name -- see cmd_outputs's
    `_flag_metadata_copy_paste`."""
    call_re = re.compile(r"strcpy\(\s*" + array_name + r"\[(" + re.escape(prefix) + r"\w+)\]\.(\w+)\s*,")
    entries = {}
    for i in range(start, end + 1):
        line = lines[i]
        if line is None or "strcpy(" not in line or array_name not in line:
            continue
        m = call_re.search(line)
        if not m:
            continue
        name, field = m.groups()
        blob = merged_block(lines, i, 6)
        mm = call_re.search(blob)
        inner, _ = matching_delim_text(blob, "(", ")", from_index=mm.start())
        first = first_top_level_comma_split(inner)
        rest = inner[len(first):].lstrip(",")
        value = concat_c_string_literals(rest)
        if value is None:
            rm = re.search(re.escape(array_name) + r"\[(" + re.escape(prefix) + r"\w+)\]\.(\w+)", rest)
            if rm:
                value = {"same_as": {"variable": rm.group(1), "field": rm.group(2)}}
        entries.setdefault(name, {"_lines": {}, "_all_lines": {}})
        entries[name][field] = value
        entries[name]["_lines"][field] = i
        entries[name]["_all_lines"].setdefault(field, []).append(i)
    return entries


def _flag_metadata_copy_paste(meta, all_names):
    """Mechanical, generic detection of the OUT_TFOL_FBFLAG/OUT_VEGT class of upstream
    copy-paste bug (independent review, S4): a field assigned more than once for the SAME entry
    (only the last write survives, which is already what `meta` reports) next to a
    DIFFERENT entry that never got that field assigned at all. Returns {name:
    note_string} for every name on either side of such a pair -- both the one whose
    field was double-written and the one left empty, so a reader hits the explanation
    from either name. Not exhaustive proof of a copy-paste (an intentional
    re-statement would also double-write), but the pairing with a same-field, same
    nearby-region empty neighbor is specific enough not to false-positive on the
    corpus checked so far."""
    doubled = {name: fields["_all_lines"] for name, fields in meta.items()
               if any(len(lns) > 1 for lns in fields.get("_all_lines", {}).values())}
    missing = {name: [f for f in ("varname", "long_name", "standard_name", "units", "description")
                       if f not in meta.get(name, {})]
               for name in all_names}

    def nearest_known_line(name):
        return min(meta.get(name, {}).get("_lines", {}).values(), default=None)

    notes = {}
    for name, all_lines in doubled.items():
        for field, lines_list in all_lines.items():
            if len(lines_list) <= 1:
                continue
            second_write_line = lines_list[-1]
            # The specific pairing worth flagging is a candidate missing exactly this
            # field whose OWN nearest known assignment line (source-line distance, not
            # enum order) sits closest to this entry's second write -- the two strcpy
            # blocks being adjacent in the source is the actual copy-paste signature,
            # not adjacency in the enum declaration.
            scored = []
            for n in all_names:
                if n == name or field not in missing.get(n, []):
                    continue
                nkl = nearest_known_line(n)
                if nkl is None:
                    continue
                scored.append((abs(nkl - second_write_line), n))
            if not scored:
                continue
            scored.sort()
            best_dist, best_name = scored[0]
            if best_dist > 15:
                continue  # too far apart in source to be the same copy-paste block
            notes[name] = (
                f"{field} was assigned more than once in source (lines "
                f"{lines_list}); the LAST write is the true runtime value (already "
                f"what this entry reports), but it duplicates text that reads as "
                f"though it belongs to {best_name} instead, which has no "
                f"{field} of its own -- a likely upstream copy-paste, not resolved "
                f"further. See catalogs/outputs.yaml's own entry for {best_name}.")
            notes[best_name] = (
                f"{field} is never assigned anywhere in source for this entry "
                f"-- {name}'s {field} was written twice instead (lines "
                f"{lines_list}), a likely upstream copy-paste. See "
                f"catalogs/outputs.yaml's own entry for {name}.")
    return notes


def parse_default_aggtype_switch(lines):
    """get_default_outvar_aggtype()'s `switch (varid) { case OUT_X: ... agg_type =
    AGG_TYPE_Y; break; ... default: agg_type = AGG_TYPE_AVG; }` -- a run of `case
    OUT_X:` lines takes the agg_type of the next `agg_type = AGG_TYPE_Y;` assignment
    line that follows them. Returns ({name: (agg_type, case_line)}, default_agg_type,
    default_where_line)."""
    start, end = find_function_body(lines, "get_default_outvar_aggtype")
    if start is None:
        return {}, None, None
    case_re = re.compile(r"^\s*case\s+(OUT_\w+)\s*:\s*$")
    assign_re = re.compile(r"^\s*agg_type\s*=\s*(AGG_TYPE_\w+)\s*;\s*$")
    default_re = re.compile(r"^\s*default\s*:\s*$")
    pending = []
    result = {}
    default_agg = None
    default_line = None
    in_default = False
    for i in range(start, end + 1):
        line = lines[i]
        if line is None:
            continue
        s = line.strip()
        m = case_re.match(s)
        if m:
            pending.append((m.group(1), i))
            continue
        if default_re.match(s):
            in_default = True
            continue
        m = assign_re.match(s)
        if m:
            if in_default:
                default_agg = m.group(1)
                default_line = i
                in_default = False
            elif pending:
                for name, ln in pending:
                    result[name] = (m.group(1), ln)
                pending = []
            continue
    return result, default_agg, default_line


def parse_nelem_assignments(lines, start, end):
    """`out_metadata[OUT_X].nelem = <expr>;` assignments after the main strcpy block,
    with any enclosing `if (options.Y)` gate (see the FROZEN_SOIL-gated OUT_FDEPTH/
    OUT_TDEPTH block). Returns {name: {"expr": ..., "gate": [...], "line": i}}."""
    assign_re = re.compile(r"out_metadata\[(OUT_\w+)\]\.nelem\s*=\s*([\w.]+)\s*;")
    stacks = c_if_stack_by_line(lines, start, end)
    out = {}
    for i in range(start, end + 1):
        line = lines[i]
        if line is None:
            continue
        m = assign_re.search(line)
        if m:
            out[m.group(1)] = {"expr": m.group(2),
                                "gate": [c for c in stacks.get(i, []) if c], "line": i}
    return out


def parse_default_streams(lines):
    """set_output_defaults()/set_output_var(...) calls: which default output stream
    (prefix string) each OUT_* variable is registered into, and any `if (options.X)`
    gate active at that registration call. Returns {name: {"stream": prefix,
    "gate": [...], "line": i}} (first registration only; no variable is registered
    twice at this commit, checked by construction -- a second registration would
    silently overwrite the first here, which is itself worth recording as a gap if it
    is ever observed)."""
    start, end = find_function_body(lines, "set_output_defaults")
    if start is None:
        return {}
    stacks = c_if_stack_by_line(lines, start, end)
    prefix_re = re.compile(r'strcpy\(\(\*streams\)\[streamnum\]\.prefix,\s*"([^"]+)"\s*\);')
    call_re = re.compile(r'set_output_var\([^,]+,\s*"(OUT_\w+)"')
    current_prefix = None
    out = {}
    for i in range(start, end + 1):
        line = lines[i]
        if line is None:
            continue
        m = prefix_re.search(line)
        if m:
            current_prefix = m.group(1)
            continue
        m = call_re.search(line)
        if m and m.group(1) not in out:
            out[m.group(1)] = {"stream": current_prefix,
                                "gate": [c for c in stacks.get(i, []) if c], "line": i}
    return out


PUT_DATA = "vic/drivers/shared_all/src/put_data.c"
# Every file where an OUT_* enum member is ever assigned into an out_data slot: the
# main driver-agnostic accumulator (put_data.c) plus the routing extensions, which
# write OUT_DISCHARGE through a second-position subscript (out_data[i][OUT_DISCHARGE])
# that a [OUT_X]-first-only pattern would not match -- both subscript shapes are
# matched below, across every file in this list, so a routing-extension assignment
# counts as "populated" exactly like a put_data.c one.
POPULATED_SEARCH_FILES = [
    PUT_DATA,
    "vic/extensions/rout_rvic/src/rout_run.c",
    "vic/extensions/rout_stub/src/rout.c",
]
_OUT_DATA_SUBSCRIPT_RE = re.compile(r"out_data\s*\[(OUT_\w+)\]")
_OUT_DATA_SUBSCRIPT_RE2 = re.compile(r"out_data\s*\[[^\[\]]*\]\s*\[(OUT_\w+)\]")


def parse_populated_outputs(root):
    """Every OUT_X assigned into an out_data slot (either subscript shape,
    `out_data[OUT_X]` or `out_data[i][OUT_X]`) anywhere in POPULATED_SEARCH_FILES (read
    OR write -- any reference proves the slot is touched at run time). An enum member
    that never appears in any of them is a phantom: registered in the shared metadata
    table (so either driver accepts it as an OUTVAR) and allocated in out_data, but
    never populated -- always its zero-initialized value (independent review C10: OUT_SURF_COND,
    OUT_IN_LONG_BAND; OUT_DISCHARGE is NOT a phantom by this rule -- it IS populated,
    but only when the image driver was built with the rout_rvic extension, which the
    shipped default build (rout_stub) does not include; that build-time gate is a
    separate fact from "never populated anywhere", not conflated with it)."""
    populated = {}
    for relf in POPULATED_SEARCH_FILES:
        p = root / relf
        if not p.is_file():
            continue
        lines = read_lines(p)
        for i in range(1, len(lines)):
            line = lines[i]
            if line is None:
                continue
            for pat in (_OUT_DATA_SUBSCRIPT_RE, _OUT_DATA_SUBSCRIPT_RE2):
                for m in pat.finditer(line):
                    populated.setdefault(m.group(1), (relf, i))
    return populated, PUT_DATA


_AGG_TYPE_RE = re.compile(r"^\s*(AGG_TYPE_\w+)\s*,?\s*(?:/\*\*<\s*(.*?)\s*\*/)?\s*$")


def parse_agg_types(hdr_lines):
    """The output aggregation-method enum (AGG_TYPE_DEFAULT/AVG/BEG/END/MAX/MIN/SUM)
    with each constant's own Doxygen comment. These are the vocabulary a reader meets
    first -- an OUTVAR line's fourth token and every output entry's own
    `default_agg_type` -- so they are catalogued as named entries in their own right,
    not left reachable only as a string inside another entry's field."""
    out = []
    for i in range(1, len(hdr_lines)):
        line = hdr_lines[i]
        if line is None:
            continue
        m = _AGG_TYPE_RE.match(line)
        if m:
            out.append(fact({"name": m.group(1),
                              "comment": (m.group(2) or "").strip() or None},
                             HDR, i, driver="both"))
    return out


def cmd_outputs(root):
    hdr_lines = read_lines(root / HDR)
    hist_lines = read_lines(root / HIST_META)
    history_start, history_end = find_function_body(hist_lines, "set_output_met_data_info")
    if history_start is None:
        sys.exit("ERROR: could not locate set_output_met_data_info in " + HIST_META)

    enum_entries = parse_enum_block(hdr_lines, 1, "OUT_", "N_OUTVAR_TYPES")
    meta = parse_metadata_strcpy_block(hist_lines, history_start, history_end,
                                        "out_metadata", "OUT_")
    nelem = parse_nelem_assignments(hist_lines, history_start, history_end)
    agg_by_name, default_agg, default_agg_line = parse_default_aggtype_switch(
        read_lines(root / VIC_HISTORY))
    streams_lines = read_lines(root / SET_OUT_DEF)
    stream_by_name = parse_default_streams(streams_lines)
    populated, put_data_rel = parse_populated_outputs(root)
    copy_paste_notes = _flag_metadata_copy_paste(meta, [e["name"] for e in enum_entries])

    def resolve_field(m_dict, field, _depth=0):
        """Resolve a metadata field that may be {"same_as": {"variable", "field"}}
        (copied from another entry's own field, e.g. OUT_SWE_BAND's units =
        out_metadata[OUT_SWE].units) to its literal string value, plus the same_as
        pointer if one was followed. VIC never chains these more than one level deep
        at this commit (checked by inspection of every same_as case actually
        produced); `_depth` guards against an unexpected chain rather than looping."""
        val = m_dict.get(field)
        if isinstance(val, dict) and "same_as" in val and _depth < 4:
            ref = val["same_as"]
            resolved, _ = resolve_field(meta.get(ref["variable"], {}), ref["field"], _depth + 1)
            return resolved, ref
        return (val if isinstance(val, str) else None), None

    variables = []
    for e in enum_entries:
        name = e["name"]
        m = meta.get(name, {})
        agg, agg_line = agg_by_name.get(name, (default_agg, default_agg_line))
        nel = nelem.get(name)
        stream = stream_by_name.get(name)
        long_name, long_name_same_as = resolve_field(m, "long_name")
        standard_name, standard_name_same_as = resolve_field(m, "standard_name")
        units, units_same_as = resolve_field(m, "units")
        description, desc_same_as = resolve_field(m, "description")
        entry = fact({
            "name": name,
            "varid_enum": name,
            "header_comment": e["comment"] or None,
            "long_name": long_name,
            "long_name_same_as": long_name_same_as,
            "standard_name": standard_name,
            "standard_name_same_as": standard_name_same_as,
            "units": units,
            "units_same_as": units_same_as,
            "description": description,
            "description_same_as": desc_same_as,
            "default_agg_type": agg,
            "nelem_expr": (nel or {}).get("expr", "1"),
            "nelem_gate": (nel or {}).get("gate", []),
            "registered_in_default_stream": stream["stream"] if stream else None,
            "registration_gate": stream["gate"] if stream else [],
            "populated": name in populated,
        }, HIST_META, (m.get("_lines", {}) or {}).get("varname", e["line"]))
        # nelem/agg-type evidence points at their own source lines, not the varname
        # registration line, when they differ enough to matter for a reader chasing
        # `where` -- kept as a secondary citation rather than overwriting `where`.
        if nel:
            entry["nelem_where"] = where(HIST_META, nel["line"])
        if agg_line:
            entry["agg_type_where"] = where(VIC_HISTORY, agg_line)
        if stream:
            entry["stream_where"] = where(SET_OUT_DEF, stream["line"])
        if name in populated:
            pop_file, pop_line = populated[name]
            entry["populated_where"] = where(pop_file, pop_line)
        else:
            entry["note"] = (
                "PHANTOM: registered in the shared output metadata table (so either "
                "driver accepts it as an OUTVAR) and allocated in out_data, but no "
                f"out_data[{name}] assignment (either subscript order) exists anywhere "
                "in put_data.c or the routing extensions -- never populated, always its "
                "zero-initialized value.")
        if name in copy_paste_notes:
            entry["note"] = (entry.get("note", "") + " " + copy_paste_notes[name]).strip()
        variables.append(entry)

    enum_names = {e["name"] for e in enum_entries}
    assert {v["name"] for v in variables} == enum_names, (
        "cmd_outputs produced a name not in the OUT_* enum, or vice versa -- extractor bug")

    return {
        "pack": "vic", "catalog": "outputs",
        "generator": "tools/extract_pack.py --pack vic outputs", "generator_version": GENERATOR_VERSION,
        "scope": SCOPE, "count": len(variables), "variables": variables,
        "agg_types": parse_agg_types(hdr_lines),
        "note": "name/units/description/kind (default_agg_type) are driver: both -- "
                "history_metadata.c/set_output_defaults.c/vic_history.c are shared code "
                "(vic/drivers/shared_all/src), not per-driver. default_agg_type is "
                "AGG_TYPE_AVG (mean over the output interval) unless the mechanical "
                "switch in get_default_outvar_aggtype() names AGG_TYPE_END (state, "
                "valid at interval end) or AGG_TYPE_SUM (flux, summed over the "
                "interval) for that variable -- AGG_TYPE_MAX/MIN/BEG exist in the enum "
                "for user-overridden aggregation in the global parameter file but are "
                "never a variable's own default at this commit. `populated` is `true` "
                "iff the name appears as an out_data[...] subscript anywhere in "
                "put_data.c -- `false` means registered but never written (a phantom; "
                "see the entry's own `note`). `note` also flags the mechanical "
                "signature of an upstream metadata copy-paste (a field written twice "
                "for one entry, paired with a neighbor missing that field entirely). "
                "`agg_types` is the aggregation-method enum itself, catalogued so each "
                "AGG_TYPE_* constant resolves by name through tools/hcm_lookup.py.",
    }


# --------------------------------------------------------------------------------------
# global_parameters: every key each driver's get_global_param.c recognizes (type,
# allowed values, default, removed-since-VIC-4 rejections), plus the post-parse
# validation constraints (log_err conditions) found in the same function.
# --------------------------------------------------------------------------------------

GLOBAL_PARAM_FILE = {
    "classic": "vic/drivers/classic/src/get_global_param.c",
    "image": "vic/drivers/image/src/get_global_param.c",
}
INIT_GLOBAL = "vic/drivers/shared_all/src/initialize_global.c"
INIT_OPTIONS = "vic/drivers/shared_all/src/initialize_options.c"
DOCS_GLOBALPARAM = {
    "classic": "docs/Documentation/Drivers/Classic/GlobalParam.md",
    "image": "docs/Documentation/Drivers/Image/GlobalParam.md",
}

_KEY_IF_RE = re.compile(
    r'(?:else\s+if|if)\s*\(\s*strcasecmp\(\s*"([A-Z0-9_]+)"\s*,\s*optstr\s*\)\s*==\s*0\s*\)\s*\{')
_SSCANF_FMT_RE = re.compile(r'sscanf\(\s*cmdstr\s*,\s*"%\*s\s*%(\w+)"')
_ASSIGN_FIELD_RE = re.compile(
    r'\b(options|global_param|param|filenames|param_set)\s*\.\s*([A-Za-z_]\w*(?:\s*\.\s*[A-Za-z_]\w*)?)')
_ENUM_BRANCH_RE = re.compile(
    r'strcasecmp\(\s*"([^"]+)"\s*,\s*flgstr\s*\)\s*==\s*0\s*\)\s*\{\s*\n?\s*'
    r'([\w.\[\]]+)\s*=\s*([A-Za-z_]\w*)\s*;')
_ENUM_ELSE_RE = re.compile(r'else\s*\{\s*log_err\(')
_HELPER_ENUM_RE = re.compile(r'\b(str_to_\w+)\(\s*flgstr\s*\)')


def strip_c_strings(text):
    """Blank the *content* of every double-quoted string literal (keep the quotes),
    so a regex looking for real code (e.g. a struct-field assignment) never matches
    text that only appears inside an error message."""
    return _STR_LIT_RE.sub('""', text)


def _blob_message(blob, call_name="log_err"):
    m = re.search(re.escape(call_name) + r"\s*\(", blob)
    if not m:
        return None
    inner, _ = matching_delim_text(blob, "(", ")", from_index=m.start())
    if inner is None:
        return None
    return concat_c_string_literals(first_top_level_comma_split(inner))


_KEY_IF_OPENER_RE = re.compile(r'^\s*(?:else\s+if|if)\s*\(')
_KEY_STRCASECMP_RE = re.compile(r'strcasecmp\(\s*"([A-Z0-9_]+)"\s*,\s*optstr\s*\)')


def parse_key_blocks(root, rel_path, driver):
    """Every `if/else if (strcasecmp("KEY", optstr) == 0[ || strcasecmp("ALIAS", optstr)
    == 0[...]]) { ... }` block in the driver's global-parameter-file parser: key name,
    line, type classification, allowed enum values (if any), assigned struct field, and
    whether the block is a removed-since-VIC-4 rejection (log_err with no field
    assignment anywhere in the block). The condition is matched by merging forward from
    the `if`/`else if` OPENER to its closing `) {`, not by requiring the whole condition
    on one physical line -- a long multi-`strcasecmp`/`||` condition commonly wraps
    across lines (uncrustify), which a single-line match silently drops entirely
    (independent review C13: NOFLUX/NO_FLUX, a two-way alias condition, wrapped exactly this way and
    neither name reached the catalog under the old single-line match). Every alias name
    found in the condition gets its OWN catalog entry, all sharing the same body/
    behavior/where -- a key recognized under more than one spelling is not silently
    reduced to just its first spelling."""
    lines = read_lines(root / rel_path)
    entries = []
    for i in range(1, len(lines)):
        line = lines[i]
        if line is None or not _KEY_IF_OPENER_RE.match(line):
            continue
        blob = merged_block(lines, i, 12)
        cond, cond_end = matching_delim_text(blob, "(", ")", from_index=0)
        if cond is None or not re.match(r"\s*\{", blob[cond_end + 1:]):
            continue
        keys = _KEY_STRCASECMP_RE.findall(cond)
        if not keys:
            continue
        body, _ = matching_delim_text(blob, "{", "}", from_index=cond_end + 1)
        if body is None:
            continue
        body_nostr = strip_c_strings(body)
        for key in keys:
            entries.append(_key_block_entry(key, i, body, body_nostr, rel_path, driver))
    return entries


def _key_block_entry(key, i, body, body_nostr, rel_path, driver):
    has_assignment = _ASSIGN_FIELD_RE.search(body_nostr) is not None
    has_log_err = "log_err(" in body_nostr
    removed = has_log_err and not has_assignment
    message = _blob_message(body) if removed else None

    fmt_m = _SSCANF_FMT_RE.search(body)
    sscanf_fmt = fmt_m.group(1) if fmt_m else None
    field_m = _ASSIGN_FIELD_RE.search(body_nostr)
    assigned_struct, assigned_field = (field_m.group(1), field_m.group(2)) if field_m else (None, None)

    allowed_values = []
    for vm in _ENUM_BRANCH_RE.finditer(body):
        allowed_values.append({
            "value": vm.group(1), "assigns": f"{vm.group(2)}={vm.group(3)}",
        })
    enum_unknown_message = None
    if allowed_values and _ENUM_ELSE_RE.search(body):
        em = _ENUM_ELSE_RE.search(body)
        enum_unknown_message = _blob_message(body[em.start():em.start() + 400])

    helper_m = _HELPER_ENUM_RE.search(body_nostr)

    if removed:
        key_type = "removed_since_vic4"
    elif allowed_values:
        key_type = "enum"
    elif helper_m:
        key_type = f"enum (resolved via {helper_m.group(1)}(), allowed values not " \
                   f"enumerated inline in get_global_param.c)"
    elif "str_to_bool(" in body_nostr:
        key_type = "bool"
    elif sscanf_fmt in ("zu", "d", "u", "hu", "hd", "ld", "lu"):
        key_type = "integer"
    elif sscanf_fmt in ("lf", "f"):
        key_type = "double"
    elif sscanf_fmt == "s":
        key_type = "string"
    else:
        key_type = "unclassified"

    return fact({
        "key": key,
        "type": key_type,
        "sscanf_format": sscanf_fmt,
        "assigned_field": f"{assigned_struct}.{assigned_field}" if assigned_struct else None,
        "allowed_values": allowed_values,
        "enum_unknown_value_message": enum_unknown_message,
        "removed_since_vic4_message": message,
    }, rel_path, i, driver=driver)


def parse_struct_defaults(root, rel_path, driver):
    """`struct.field = VALUE;` default assignments (initialize_global.c /
    initialize_options.c), one clean statement per line at this commit (checked by
    inspection: neither file uses multi-line default assignments). Returns
    {"struct.field": {"value": ..., "line": i}}."""
    lines = read_lines(root / rel_path)
    out = {}
    assign_re = re.compile(
        r'^\s*(options|global_param|param)\s*\.\s*([A-Za-z_]\w*)\s*(?:\[\w+\])?\s*=\s*(.+?)\s*;\s*$')
    for i in range(1, len(lines)):
        line = lines[i]
        if line is None:
            continue
        m = assign_re.match(_strip_line_comment(line))
        if m:
            out.setdefault(f"{m.group(1)}.{m.group(2)}", {"value": m.group(3), "line": i})
    return out


def parse_docs_key_table(root, rel_path):
    """Best-effort cross-reference set of key names documented in a Markdown option
    table (`| KEY | Type | Units | Description |` rows) in docs/Documentation. Purely
    a documented-vs-parsed cross-check, not a full docs parse -- rows whose first
    column is not an all-caps identifier (table dividers, 'EITHER:'/'OR:' notes,
    TRUE/FALSE sub-rows) are dropped by requiring at least one '_' or length >= 4, but
    this is a heuristic, not exhaustive (see known_gaps)."""
    p = root / rel_path
    if not p.is_file():
        return {}
    lines = read_lines(p)
    row_re = re.compile(r'^\|\s*([A-Z][A-Z0-9_]*)\s*\|')
    skip = {"TRUE", "FALSE", "NAME", "TYPE", "UNITS", "DESCRIPTION", "EITHER", "OR", "NOTE"}
    out = {}
    for i in range(1, len(lines)):
        line = lines[i]
        if line is None:
            continue
        m = row_re.match(line.strip())
        if m and m.group(1) not in skip and (len(m.group(1)) >= 4):
            out.setdefault(m.group(1), i)
    return out


def parse_validation_constraints(root, rel_path, driver):
    """Post-parse validation `log_err(...)` calls guarded by an `if (COND) { ... }`
    whose condition does not reference `optstr` (i.e. not a key-match branch) and
    whose body has no further nested `if (` (a leaf condition -- an outer wrapper
    condition around several leaf checks is skipped so it is not recorded twice).
    Also excludes any condition nested inside the key-parsing while-loop's per-key
    branches (indent >= 12 at this commit's uncrustify formatting, e.g. the inner
    `if (strcasecmp("TRUE", flgstr) == 0)` checks that belong to a removed-key
    rejection, already captured by parse_key_blocks) -- real post-parse validation
    checks sit at indent <= 8, checked against every example found by hand before
    fixing this threshold (see the extraction report in the development record)."""
    lines = read_lines(root / rel_path)
    facts_out = []
    seen_lines = set()
    for i in range(1, len(lines)):
        line = lines[i]
        if line is None:
            continue
        indent = len(line) - len(line.lstrip(" "))
        if indent > 8:
            continue
        s = _strip_line_comment(line)
        m = _C_IF_RE.match(s)
        cond = None
        cond_end_off = None
        if m:
            cond = (m.group(1) or m.group(2) or "").strip()
            blob = merged_block(lines, i, 40)
        elif _KEY_IF_OPENER_RE.match(s):
            # A multi-line condition (e.g. classic's MODEL_STEPS_PER_DAY > HOURS_PER_DAY
            # && ... % HOURS_PER_DAY != 0 check wraps across two lines) does not match
            # the single-line _C_IF_RE above -- merge forward to find its closing `) {`
            # the same way parse_key_blocks/c_if_stack_by_line already do, so a wrapped
            # validation condition is not silently dropped entirely.
            blob = merged_block(lines, i, 12)
            inner, end_off = matching_delim_text(blob, "(", ")", from_index=0)
            if inner is None or not re.match(r"\s*\{", blob[end_off + 1:]):
                continue
            cond = re.sub(r"\s+", " ", inner).strip()
            cond_end_off = end_off
        if cond is None:
            continue
        if not cond or "optstr" in cond:
            continue
        if cond_end_off is not None:
            body, end_off = matching_delim_text(blob, "{", "}", from_index=cond_end_off + 1)
        else:
            body, end_off = matching_delim_text(blob, "{", "}", from_index=0)
        if body is None or "log_err(" not in body:
            continue
        # Skip if the body itself opens another `if (` (not a leaf condition) -- its
        # nested log_err calls are recorded individually at their own line instead.
        body_after_first_brace = body
        if re.search(r'\bif\s*\(', strip_c_strings(body_after_first_brace)):
            continue
        if i in seen_lines:
            continue
        seen_lines.add(i)
        msg = _blob_message(body)
        facts_out.append(fact({
            "condition": cond, "message": msg,
        }, rel_path, i, driver=driver))
    return facts_out


def cmd_global_parameters(root):
    init_global = parse_struct_defaults(root, INIT_GLOBAL, "both")
    init_options = parse_struct_defaults(root, INIT_OPTIONS, "both")
    defaults = {}
    defaults.update(init_global)
    defaults.update(init_options)

    entries = []
    constraints = []
    for driver, rel_path in GLOBAL_PARAM_FILE.items():
        docs_keys = parse_docs_key_table(root, DOCS_GLOBALPARAM[driver])
        for e in parse_key_blocks(root, rel_path, driver):
            default_info = defaults.get(e.get("assigned_field")) if e.get("assigned_field") else None
            e["default_in_code"] = default_info["value"] if default_info else None
            e["default_where"] = (where(
                INIT_OPTIONS if e["assigned_field"].startswith("options.") else INIT_GLOBAL,
                default_info["line"], driver="both")
                if default_info and e.get("assigned_field") else None)
            e["documented_in_docs"] = e["key"] in docs_keys
            entries.append(e)
        constraints.extend(parse_validation_constraints(root, rel_path, driver))

    # documented-but-not-parsed, per driver (best-effort cross-reference; see
    # parse_docs_key_table's own caveats).
    documented_not_parsed = []
    for driver, rel_path in GLOBAL_PARAM_FILE.items():
        docs_keys = parse_docs_key_table(root, DOCS_GLOBALPARAM[driver])
        parsed_keys = {e["key"] for e in entries if e["where"]["driver"] == driver}
        for k in sorted(set(docs_keys) - parsed_keys):
            documented_not_parsed.append(fact(
                {"key": k}, DOCS_GLOBALPARAM[driver], docs_keys[k], driver=driver))

    return {
        "pack": "vic", "catalog": "global_parameters",
        "generator": "tools/extract_pack.py --pack vic global-parameters",
        "generator_version": GENERATOR_VERSION, "scope": SCOPE,
        "count": len(entries), "keys": entries,
        "constraints": constraints,
        "documented_but_not_parsed": documented_not_parsed,
        "note": "Each key's `where` carries its own `driver` (classic|image); a key "
                "recognized by only one driver's get_global_param.c is not "
                "duplicated for the other. `constraints` are the post-parse "
                "log_err(...) validation conditions found in the same function "
                "(time-stepping divisibility rules, FULL_ENERGY/FROZEN_SOIL/"
                "QUICK_FLUX option-combination requirements, etc.) -- leaf "
                "conditions only, so a wrapping if-block around several checks is "
                "not also recorded as a duplicate, broader constraint. "
                "`documented_but_not_parsed` is a best-effort Markdown-table "
                "cross-reference (docs/Documentation/Drivers/<Driver>/GlobalParam.md), "
                "not a semantic docs parse -- code wins on any disagreement.",
    }


# --------------------------------------------------------------------------------------
# options: option_struct fields (vic_def.h) and where each one branches in the shared
# physics code (vic/vic_run/src/*.c) -- driver: both, since vic_run is shared between
# classic and image (only the global-parameter-file KEY that sets an option's value is
# driver-specific; see catalogs/global_parameters.yaml for that half).
# --------------------------------------------------------------------------------------

VIC_DEF_H = "vic/vic_run/include/vic_def.h"
VIC_RUN_SRC_DIR = "vic/vic_run/src"

_OPTION_FIELD_RE = re.compile(
    r'^\s*(bool|short|unsigned\s+short\s+int|unsigned\s+short|size_t|int|double)\s+'
    r'([A-Za-z_]\w*)\s*;\s*(?:/\*\*<\s*(.*?)(?:\*/)?\s*)?$')
_OPTIONS_USE_RE_CACHE = {}


def parse_option_struct_fields(root):
    """Every field of `option_struct` (vic_def.h), in declaration order, with its C
    type and (first-line only) Doxygen comment. A field's full multi-line comment is
    not reconstructed here -- only the text on the declaration's own line -- since the
    field's real behavior is established from its branch citations, not the comment."""
    lines = read_lines(root / VIC_DEF_H)
    start, end = None, None
    for i in range(1, len(lines)):
        if lines[i] and re.match(r'^\s*typedef\s+struct\s*\{\s*$', lines[i]):
            # Confirm this is option_struct by checking the closing line names it.
            blob = merged_block(lines, i, 200)
            m = re.search(r'\}\s*option_struct\s*;', blob)
            if m:
                end_line = i + blob[:m.end()].count("\n")
                start, end = i, end_line
                break
    if start is None:
        sys.exit("ERROR: could not locate option_struct in " + VIC_DEF_H)
    fields = []
    for i in range(start, end + 1):
        line = lines[i]
        if line is None:
            continue
        m = _OPTION_FIELD_RE.match(line)
        if m:
            fields.append({"name": m.group(2), "c_type": re.sub(r"\s+", " ", m.group(1)),
                            "comment_first_line": (m.group(3) or "").strip() or None, "line": i})
    return fields


def find_option_branch_citations(root, field_name, max_citations=20):
    """Every line under vic/vic_run/src/*.c referencing `options.FIELD` (word-
    boundary), file:line plus the stripped source line text, capped at
    `max_citations` (a field referenced more than that is still counted in full via
    `total_references`, just not cited that many times)."""
    if not _OPTIONS_USE_RE_CACHE:
        pass
    pattern = re.compile(r'\boptions\s*\.\s*' + re.escape(field_name) + r'\b')
    src_dir = root / VIC_RUN_SRC_DIR
    citations = []
    total = 0
    for p in sorted(src_dir.glob("*.c")):
        rel = relpath(root, p)
        lines = read_lines(p)
        for i in range(1, len(lines)):
            line = lines[i]
            if line is None:
                continue
            if pattern.search(line):
                total += 1
                if len(citations) < max_citations:
                    citations.append({"file": rel, "line": i, "text": line.strip()})
    return citations, total


def cmd_options(root):
    fields = parse_option_struct_fields(root)
    entries = []
    for f in fields:
        citations, total = find_option_branch_citations(root, f["name"])
        entries.append(fact({
            "name": f["name"],
            "c_type": f["c_type"],
            "comment_first_line": f["comment_first_line"],
            "vic_run_branch_count": total,
            "vic_run_branch_citations": [
                fact({"text": c["text"]}, c["file"], c["line"]) for c in citations],
        }, VIC_DEF_H, f["line"]))
    return {
        "pack": "vic", "catalog": "options",
        "generator": "tools/extract_pack.py --pack vic options", "generator_version": GENERATOR_VERSION,
        "scope": SCOPE, "count": len(entries), "options": entries,
        "note": "vic_run_branch_citations covers every options.FIELD reference under "
                "vic/vic_run/src/*.c (both `if (options.X)` plain-bool tests and "
                "`options.X == ENUM_VALUE` equality tests, since both compile to the "
                "same source-text pattern this regex matches; distinguishing them is "
                "left to the citation's own text). vic_run is shared between drivers, "
                "so every citation here is driver: both -- the driver-specific half "
                "(which global-parameter-file KEY sets this option, and its default) "
                "is in catalogs/global_parameters.yaml's `assigned_field` cross-"
                "reference (options.<FIELD>). A field with vic_run_branch_count == 0 "
                "is not itself a physics-code no-op: it may gate driver/parameter-I/O "
                "code outside vic/vic_run (e.g. Noutstreams, STATE_FORMAT) or be "
                "consumed indirectly through a derived count rather than a direct "
                "field test (e.g. SPATIAL_FROST via Nfrost) -- not distinguished "
                "further at this mechanical pass; see known_gaps.",
    }


# --------------------------------------------------------------------------------------
# constants: the physical constants header (#define NAME VALUE /**< comment */).
# --------------------------------------------------------------------------------------

CONSTANTS_H = "vic/vic_run/include/vic_physical_constants.h"
_DEFINE_RE = re.compile(
    r'^#define\s+([A-Za-z_]\w*)(\([^)]*\))?\s+(.+?)\s*(?:/\*\*?<?\s*(.*?)\s*\*/)?\s*$')


def cmd_constants(root):
    lines = read_lines(root / CONSTANTS_H)
    entries = []
    for i in range(1, len(lines)):
        line = lines[i]
        if line is None or not line.startswith("#define"):
            continue
        m = _DEFINE_RE.match(line)
        if not m:
            continue
        name, macro_args, value, comment = m.groups()
        comment = (comment or "").strip()
        units = None
        um = re.search(r"~\s*([^\s*]+(?:/[^\s*]+)*)\s*$", comment)
        if um:
            units = um.group(1)
        entries.append(fact({
            "name": name, "value": value.strip(), "comment": comment or None, "units": units,
            "is_function_like_macro": macro_args is not None,
            "macro_args": macro_args.strip("()") if macro_args else None,
        }, CONSTANTS_H, i))
    return {
        "pack": "vic", "catalog": "constants",
        "generator": "tools/extract_pack.py --pack vic constants", "generator_version": GENERATOR_VERSION,
        "scope": SCOPE, "count": len(entries), "constants": entries,
        "note": "vic_physical_constants.h is compiled into the binary (not a runtime "
                "file), so every entry here is driver: both and cannot be overridden "
                "by a global/model-parameters file at run time -- contrast with "
                "catalogs/model_parameters.yaml, whose keys ARE runtime-configurable "
                "via the model parameters file read by get_parameters.c. `units` is a "
                "best-effort parse of a trailing '~ UNIT' comment convention this "
                "header mostly follows, not present on every line -- null where absent, "
                "never guessed. is_function_like_macro=true (e.g. C_TO_F) means `value` "
                "is a C expression IN TERMS OF `macro_args`, not a constant scalar -- "
                "independent review C12: catalogued as a plain constant before, with no indication "
                "it takes an argument.",
    }


# --------------------------------------------------------------------------------------
# model_parameters: the runtime-configurable model parameters file (get_parameters.c /
# initialize_parameters.c) -- reuses the same key-block parser as global_parameters,
# since get_parameters.c is written in the identical strcasecmp(optstr)-chain style.
# --------------------------------------------------------------------------------------

GET_PARAMETERS_C = "vic/drivers/shared_all/src/get_parameters.c"
INIT_PARAMETERS = "vic/drivers/shared_all/src/initialize_parameters.c"


def cmd_model_parameters(root):
    defaults = parse_struct_defaults(root, INIT_PARAMETERS, "both")
    keys = parse_key_blocks(root, GET_PARAMETERS_C, "both")
    for e in keys:
        default_info = defaults.get(e.get("assigned_field")) if e.get("assigned_field") else None
        e["default_in_code"] = default_info["value"] if default_info else None
        e["default_where"] = (where(INIT_PARAMETERS, default_info["line"], driver="both")
                               if default_info else None)
    constraints = parse_validation_constraints(root, GET_PARAMETERS_C, "both")
    return {
        "pack": "vic", "catalog": "model_parameters",
        "generator": "tools/extract_pack.py --pack vic model-parameters",
        "generator_version": GENERATOR_VERSION, "scope": SCOPE,
        "count": len(keys), "keys": keys, "constraints": constraints,
        "note": "The VIC model (constants) parameters file is read by get_parameters() "
                "in this same source file (shared_all, driver: both) -- a SEPARATE, "
                "optional runtime file from the compiled-in physical constants in "
                "catalogs/constants.yaml. `constraints` are validate_parameters()'s "
                "range checks (same file), reusing the same leaf-condition, "
                "indent<=8 heuristic as catalogs/global_parameters.yaml.",
    }


# --------------------------------------------------------------------------------------
# forcing: accepted forcing variable types, per driver (classic column-based vs image
# NetCDF-variable-based), cross-referenced against the shared master enum's inline
# units comment (vic_driver_shared_all.h).
# --------------------------------------------------------------------------------------

GET_FORCE_TYPE_C = "vic/drivers/classic/src/get_force_type.c"
SET_FORCE_TYPE_C = "vic/drivers/shared_image/src/set_force_type.c"
_FORCE_TYPE_RE = re.compile(
    r'(?:else\s+if|if)\s*\(\s*strcasecmp\(\s*"([A-Z0-9_]+)"\s*,\s*optstr\s*\)\s*==\s*0\s*\)\s*\{\s*\n?\s*'
    r'type\s*=\s*(\w+)\s*;')


def parse_forcing_type_enum(root):
    lines = read_lines(root / HDR)
    start = None
    for i in range(1, len(lines)):
        if lines[i] and "Forcing Variable Types" in lines[i]:
            start = i
            break
    return {e["name"]: e for e in parse_enum_block(lines, start or 1, "", "N_FORCING_TYPES")} if start else {}


def parse_forcing_types(root, rel_path, driver):
    lines = read_lines(root / rel_path)
    entries = []
    for i in range(1, len(lines)):
        line = lines[i]
        if line is None or "strcasecmp" not in line:
            continue
        blob = merged_block(lines, i, 6)
        m = _FORCE_TYPE_RE.search(blob)
        if not m or not blob.lstrip().startswith(("if", "else")):
            m2 = _FORCE_TYPE_RE.match(line + "\n" + (lines[i + 1] or "") if i + 1 < len(lines) else line)
            m = m or m2
        if not m:
            continue
        entries.append(fact({"name": m.group(1), "enum_const": m.group(2)}, rel_path, i, driver=driver))
    return entries


VIC_FORCE_CLASSIC = "vic/drivers/classic/src/vic_force.c"
VIC_FORCE_IMAGE = "vic/drivers/image/src/vic_force.c"
_FORCING_DATA_ASSIGN_RE = re.compile(
    r'^\s*force\[\w+\]\.(\w+)\[\w+\]\s*=\s*forcing_data\[(\w+)\]\[\w+\]\s*(.*?);\s*$')
_TYPE_VARNAME_RE = re.compile(r'param_set\s*\.\s*TYPE\s*\[\s*(\w+)\s*\]\s*\.\s*varname')
_DVAR_ASSIGN_RE = re.compile(r'^\s*force\[\w+\]\.(\w+)\[\w+\]\s*=\s*(.*?dvar\[\w+\].*?)\s*;\s*$')
_SCALE_RE = re.compile(r'([*/])\s*([A-Za-z_][\w.]*)')
# A unit conversion applied to an already-stored force-struct field, anywhere in
# vic_force.c, as a compound assignment (`force[i].pressure[j] *= PA_PER_KPA;`). The
# image driver stores every NetCDF value unchanged at the read and converts kPa -> Pa in
# a separate "Convert forcings into what we need" loop further down the same file, so a
# scan of the read LINE alone reports no conversion where one exists (and the chain then
# reads as though VIC consumes kPa). Matching only a compound assignment keeps the
# sub-step aggregation writes (`force[rec].prec[NR] = average(...) * NF;`) out: those
# change the sampling, not the unit.
_COMPOUND_SCALE_RE = re.compile(
    r'^\s*force\[\w+\]\.(\w+)\[\w+\]\s*([*/])=\s*([A-Za-z_][\w.]*)\s*;\s*$')


def _preceding_comment(lines, i):
    """The nearest non-blank line at or above i-1 that is a bare `// ...` comment (the
    internal-unit annotation VIC's own forcing-read code consistently places right
    above the read it describes), or None."""
    for j in range(i - 1, max(0, i - 4), -1):
        ln = lines[j]
        if ln is None or not ln.strip():
            continue
        s = ln.strip()
        if s.startswith("//"):
            return s.lstrip("/").strip()
        return None
    return None


def _later_field_scales(lines):
    """{force-struct field name: (op_const_list, line)} for every unit conversion
    applied to that field by a compound assignment anywhere in this vic_force.c, after
    the value was stored. Only the LAST such conversion for a field is kept, since that
    is the one that fixes the internal unit."""
    out = {}
    for i in range(1, len(lines)):
        line = lines[i]
        if line is None:
            continue
        m = _COMPOUND_SCALE_RE.match(line)
        if m:
            field, op, const = m.groups()
            out[field] = ([f"{op}{const}"], i)
    return out


_VEG_HIST_ASSIGN_RE = re.compile(
    r'^\s*veg_hist\[\w+\]\[\w+\]\.(\w+)\[\w+\]\s*=\s*'
    r'((?=.*(?:veg_hist_data\[|dvar\[)).*?);\s*$', re.S)


def parse_veg_hist_chain(lines, rel_path, type_names):
    """The three vegetation-history forcing types (ALBEDO, LAI, FCANOPY) are read by the
    same vic_force.c as the meteorological ones, but into the per-vegetation-tile
    `veg_hist` array rather than the `force` struct, so a scan for `force[...]`
    assignments alone leaves their chain blank and the catalog cannot say whether
    anything scales them. A veg_hist field is matched to its forcing type by name (field
    `LAI` -> type `LAI`); a field with no type of that name is ignored rather than
    guessed. The assignment may wrap onto the next line, so lines are joined until the
    statement's own semicolon.

    Only an assignment whose right-hand side is the FORCING source (`veg_hist_data[...]`
    in classic, the NetCDF scatter buffer `dvar[...]` in image) counts: both drivers
    first fill the same three veg_hist fields from the monthly climatology in
    `veg_con[...]`, and matching those instead would cite the climatology default as
    though it were the forcing read."""
    out = {}
    for i in range(1, len(lines)):
        line = lines[i]
        if line is None or "veg_hist[" not in line:
            continue
        stmt, j = line, i
        while ";" not in stmt and j + 1 < len(lines) and lines[j + 1] is not None:
            j += 1
            stmt += " " + lines[j].strip()
        m = _VEG_HIST_ASSIGN_RE.match(stmt)
        if not m:
            continue
        field, rhs = m.groups()
        type_name = field.upper()
        if type_name not in type_names or type_name in out:
            continue
        scale = _SCALE_RE.findall(rhs)
        out[type_name] = {
            "internal_unit_comment": _preceding_comment(lines, i),
            "read_scale": [f"{op}{val}" for op, val in scale] or None,
            "read_where": {"file": rel_path, "line": i},
            "read_note": (
                "a vegetation-history forcing: read into the per-vegetation-tile "
                f"veg_hist array at {rel_path}:{i}, not into the force struct the other "
                "forcing types use, and only when this driver's own *_SRC option selects "
                "the vegetation-history source"),
        }
    return out


def _merge_later_scale(chain, field, later, src_file):
    """Fold a later whole-file conversion for `field` into that type's read chain.
    `read_scale`/`read_where`/`internal_unit_comment` then describe the line that
    actually sets the internal unit, and `read_note` keeps the store line visible so the
    two-step path is not lost."""
    if field not in later:
        return chain
    scales, line = later[field]
    chain["read_note"] = (
        f"the forcing value is stored unchanged at {src_file}:{chain['read_where']['line']}; "
        f"the {' '.join(scales)} conversion that sets the internal unit is applied to the "
        f"stored field in a later loop at :{line}, not on the read line")
    chain["read_scale"] = (chain["read_scale"] or []) + scales
    chain["read_where"] = {"file": src_file, "line": line}
    chain["internal_unit_comment"] = chain["later_scale_comment"]
    return chain


def parse_read_unit_chain_classic(root):
    """For each forcing TYPE read in classic's vic_force.c: the code comment naming the
    internal unit right above the read, and any `* CONST`/`/ CONST` scale factor applied
    between the raw forcing_data[] value and the internal force struct field -- the
    mechanical "unit on file -> conversion on read -> internal unit" chain the independent review
    asked every forcing type be checked against (not just CATM/CHANNEL_IN). A conversion
    applied to the stored field further down the same file (see `_later_field_scales`)
    counts as part of the same chain, so `read_scale: null` means "no conversion found
    anywhere in vic_force.c", not merely "none on the read line"."""
    lines = read_lines(root / VIC_FORCE_CLASSIC)
    later = _later_field_scales(lines)
    out = {}
    for i in range(1, len(lines)):
        line = lines[i]
        if line is None:
            continue
        m = _FORCING_DATA_ASSIGN_RE.match(line)
        if not m:
            continue
        field, type_name, rest = m.groups()
        scale = _SCALE_RE.findall(rest) if rest else []
        chain = {
            "internal_unit_comment": _preceding_comment(lines, i),
            "read_scale": [f"{op}{val}" for op, val in scale] or None,
            "read_where": {"file": VIC_FORCE_CLASSIC, "line": i},
            "read_note": None,
            "later_scale_comment": (_preceding_comment(lines, later[field][1])
                                     if field in later else None),
        }
        out[type_name] = _merge_later_scale(chain, field, later, VIC_FORCE_CLASSIC)
    return out


def parse_read_unit_chain_image(root):
    """Same as parse_read_unit_chain_classic, for the image driver's vic_force.c: the
    TYPE name comes from the preceding get_scatter_nc_field_* call's
    `param_set.TYPE[X].varname` argument, and the assignment (a few lines later) is
    matched by its `dvar[...]` right-hand side instead of a `forcing_data[TYPE]`
    subscript (image reads through a scatter buffer, not a shared forcing_data array)."""
    lines = read_lines(root / VIC_FORCE_IMAGE)
    later = _later_field_scales(lines)
    out = {}
    pending_type = None
    pending_type_line = None
    for i in range(1, len(lines)):
        line = lines[i]
        if line is None:
            continue
        tm = _TYPE_VARNAME_RE.search(line)
        if tm:
            pending_type, pending_type_line = tm.group(1), i
            continue
        if pending_type:
            dm = _DVAR_ASSIGN_RE.match(line)
            if dm:
                field, rest = dm.groups()
                scale = _SCALE_RE.findall(rest)
                chain = {
                    "internal_unit_comment": _preceding_comment(lines, pending_type_line),
                    "read_scale": [f"{op}{val}" for op, val in scale] or None,
                    "read_where": {"file": VIC_FORCE_IMAGE, "line": i},
                    "read_note": None,
                    "later_scale_comment": (_preceding_comment(lines, later[field][1])
                                             if field in later else None),
                }
                out[pending_type] = _merge_later_scale(chain, field, later, VIC_FORCE_IMAGE)
                pending_type = None
    return out


def cmd_forcing(root):
    enum_meta = parse_forcing_type_enum(root)
    classic = parse_forcing_types(root, GET_FORCE_TYPE_C, "classic")
    image = parse_forcing_types(root, SET_FORCE_TYPE_C, "image")
    read_chain = {"classic": parse_read_unit_chain_classic(root),
                  "image": parse_read_unit_chain_image(root)}
    type_names = {e["name"] for e in enum_meta.values()} | set(enum_meta)
    for driver, rel in (("classic", VIC_FORCE_CLASSIC), ("image", VIC_FORCE_IMAGE)):
        for name, chain in parse_veg_hist_chain(read_lines(root / rel), rel, type_names).items():
            read_chain[driver].setdefault(name, chain)
    entries = []
    for driver_entries, driver in ((classic, "classic"), (image, "image")):
        for e in driver_entries:
            meta = enum_meta.get(e["enum_const"], {})
            comment = meta.get("comment", "")
            units = None
            um = re.search(r"\[([^\]]*)\]\s*$", comment)
            if um:
                units = um.group(1)
            e["units"] = units
            e["description"] = comment or None
            e["file_format"] = ("ASCII/binary column (classic, positional -- column "
                                 "order in the forcing file is the ORDER these "
                                 "FORCE_TYPE lines appear in the global parameter "
                                 "file, not fixed by name)" if driver == "classic" else
                                 "NetCDF variable (image -- bound to an arbitrary "
                                 "NetCDF variable name given as this FORCE_TYPE "
                                 "line's second token; that name is free-form, not "
                                 "part of the type vocabulary itself)")
            chain = read_chain[driver].get(e["enum_const"])
            if chain:
                e["internal_unit_comment"] = chain["internal_unit_comment"]
                e["read_scale"] = chain["read_scale"]
                e["read_where"] = where(chain["read_where"]["file"], chain["read_where"]["line"], driver=driver)
                e["read_note"] = chain["read_note"]
            else:
                e["internal_unit_comment"] = None
                e["read_scale"] = None
                e["read_where"] = None
                e["read_note"] = None
            entries.append(e)

    # Two units the independent review found the declared `units` (from the enum's own trailing
    # comment / get_force_type.c) contradicts what the code actually does on read and
    # report: neither has any scale factor in vic_force.c (checked above -- read_scale
    # is null for both in both drivers), so the type's OWN declared unit is corrected
    # here rather than left to read as agreeing with the code.
    for e in entries:
        if e["enum_const"] == "CATM":
            # The first token of `units` is the unit the FILE must hold (CHANNEL_IN's
            # sibling entry sets that convention). CATM carries no conversion anywhere
            # in either vic_force.c -- asserted here, so a future pin that adds one can
            # never leave this hand-written correction standing unnoticed -- therefore
            # the file value IS the internal value, and put_data.c:137's division by
            # PPM_to_MIXRATIO (1.0e-6) to report OUT_CATM in ppm proves that internal
            # value is a mixing ratio, not ppm.
            if e["read_scale"] is not None:
                raise AssertionError(
                    "CATM now carries a conversion in vic_force.c "
                    f"({e['read_scale']} at {e['read_where']}); the hand-written units "
                    "correction below assumes there is none -- re-derive it from the "
                    "new code before regenerating")
            e["units"] = "mixing ratio (fraction) = ppm x 1e-6 (file and internal " \
                          "force struct value, unchanged on read); " \
                          "get_force_type.c:48's own comment and " \
                          "docs/Documentation/Drivers/Classic/ForcingData.md both say " \
                          "[ppm], which is wrong by 1e6 -- put_data.c:137 divides the " \
                          "stored value by PPM_to_MIXRATIO (1.0e-6) to report OUT_CATM " \
                          "in ppm, and calc_surf_energy_bal.c:188 reads the same stored " \
                          "field with the comment \"CO2 mixing ratio\", so a file " \
                          "written in ppm is silently 1e6 too large"
            e["units_note_where"] = where("vic/drivers/shared_all/src/put_data.c", 137, driver="both")
        elif e["enum_const"] == "CHANNEL_IN":
            e["units"] = "mm depth over the grid cell (file and internal force " \
                          "struct value, unchanged on read); converted to m3 only at " \
                          "the point of use in the lake water balance " \
                          "(soil_con->cell_area / MM_PER_M)"
            e["units_note_where"] = where("vic/vic_run/src/vic_run.c", 418, driver="both")

    return {
        "pack": "vic", "catalog": "forcing",
        "generator": "tools/extract_pack.py --pack vic forcing", "generator_version": GENERATOR_VERSION,
        "scope": SCOPE, "count": len(entries), "types": entries,
        "note": "Both drivers accept the same 15 short-code forcing type names (the "
                "shared enum in vic_driver_shared_all.h) via an identical "
                "strcasecmp(\"NAME\", optstr)-chain in get_force_type.c (classic) / "
                "set_force_type.c (image); the two differ only in what the matched "
                "line then binds the type to -- a positional column (classic) or an "
                "explicit NetCDF variable name (image), not in the vocabulary of "
                "accepted type names itself. `required` set (which types a run must "
                "supply) and the VIC-5-no-longer-disaggregates-daily-forcings / "
                "forcing-timestep-vs-model-timestep rule are recorded in "
                "catalogs/global_parameters.yaml's constraints (FORCE_STEPS_PER_DAY-"
                "related keys), not duplicated here -- see known_gaps for what this "
                "catalog does not itself state about required-ness per variable "
                "(VIC's forcing requirements are combinatorial -- e.g. either PREC or "
                "its equivalents, either SWDOWN/LWDOWN or elements to derive them -- "
                "and are not encoded as a simple per-type required flag in this "
                "parser; recorded as a known gap rather than guessed). `units` is the "
                "TYPE's own declared unit (get_force_type.c/the enum comment), except "
                "for CATM and CHANNEL_IN, corrected here because the code's actual "
                "read/consumption unit disagrees (independent review C1/C2) -- see "
                "`units_note_where`. `internal_unit_comment`/`read_scale`/`read_where` "
                "are the mechanical unit-on-file -> conversion-on-read -> internal-unit "
                "chain for EVERY type in both drivers: `internal_unit_comment` is the "
                "code's own comment immediately above the read (vic_force.c), "
                "`read_scale` lists any `* CONST`/`/ CONST` applied to the value on the "
                "read line OR to the stored field by a later compound assignment "
                "anywhere in the same vic_force.c (null means no conversion was found "
                "anywhere in that file, not merely none on the read line -- the image "
                "driver converts pressure and vapour pressure to Pa in a separate loop "
                "well below the read, and `read_note` names both lines when the chain "
                "has two steps), and `read_where` cites the line that sets the internal "
                "unit. The three vegetation-history types (ALBEDO, LAI, FCANOPY) are "
                "read into the per-vegetation-tile veg_hist array rather than the force "
                "struct, and their own `read_note` says so and cites the forcing read, "
                "not the monthly-climatology default both drivers write to the same "
                "fields first. A type never read in vic_force.c at all (SKIP, the "
                "column-placeholder type) carries null in all four -- reported, not "
                "guessed.",
    }


# --------------------------------------------------------------------------------------
# parameters: classic soil/veg/veglib file column layout, image NetCDF parameter
# variable names, and the ARNO<->NIJSSEN2001 baseflow conversion.
# --------------------------------------------------------------------------------------

READ_SOILPARAM_C = "vic/drivers/classic/src/read_soilparam.c"
READ_VEGPARAM_C = "vic/drivers/classic/src/read_vegparam.c"
READ_VEGLIB_C = "vic/drivers/classic/src/read_veglib.c"
VIC_INIT_C = "vic/drivers/shared_image/src/vic_init.c"

_SOIL_COL_ERR_RE = re.compile(r'log_err\(\s*"Can\'t find values for')
_SOIL_COL_LAYER_RE = re.compile(r'for layer\s*%\w+', re.I)


def cmd_parameters(root):
    # -- Classic soil parameter file column order (in read order; the log_err
    # "Can't find values for <NAME> in soil file" strewn through read_soilparam.c's
    # strtok chain is a de-facto column-name marker for every field it reads). --
    soil_lines = read_lines(root / READ_SOILPARAM_C)
    stacks = c_if_stack_by_line(soil_lines, 1, len(soil_lines) - 1)
    soil_columns = []
    # The file's true FIRST column is a run-cell flag, read by a standalone
    # fscanf("%d", &flag) BEFORE the per-line fgets/strtok chain the log_err-marker
    # sweep below finds -- so it carries no "Can't find values for..." message and was
    # missed entirely by that sweep alone (independent review C5: every catalogued column was
    # off by one, and the count one short). Detected directly by its own distinct
    # pattern, not hand-inserted.
    _run_cell_re = re.compile(r'fscanf\(\s*soilparam\s*,\s*"%d"\s*,\s*&flag\s*\)')
    for i in range(1, len(soil_lines)):
        line = soil_lines[i]
        if line is not None and _run_cell_re.search(line):
            soil_columns.append(fact({
                "column": "RUN CELL FLAG", "per_layer": False, "gate": [],
            }, READ_SOILPARAM_C, i, driver="classic"))
            break
    for i in range(1, len(soil_lines)):
        line = soil_lines[i]
        if line is None or not _SOIL_COL_ERR_RE.search(line):
            continue
        blob = merged_block(soil_lines, i, 5)
        msg = _blob_message(blob)
        if not msg:
            continue
        m = re.search(r"Can't find values for (.*?) in(?: the)? soil file", msg)
        col_name = m.group(1).strip() if m else msg
        per_layer = bool(_SOIL_COL_LAYER_RE.search(col_name))
        col_name = _SOIL_COL_LAYER_RE.sub("", col_name).strip()
        # The raw if-stack includes the read loop's own per-column error checks
        # ('token == NULL') and the whole-record wrapper ('!(*MODEL_DONE) && ...'),
        # neither of which is an option gate -- keep only conditions that actually
        # reference an options.FIELD (ORGANIC_FRACT/SPATIAL_FROST/JULY_TAVG_SUPPLIED
        # and similar), which is what "optional column" means here.
        option_gate = [c for c in stacks.get(i, []) if c and "options." in c]
        soil_columns.append(fact({
            "column": col_name, "per_layer": per_layer,
            "gate": option_gate,
        }, READ_SOILPARAM_C, i, driver="classic"))

    # ARNO<->NIJSSEN2001 baseflow parameter conversion (read_soilparam.c).
    baseflow_conversion = []
    for i in range(1, len(soil_lines)):
        line = soil_lines[i]
        if line is None:
            continue
        if re.search(r"options\.BASEFLOW\s*==\s*NIJSSEN2001", line):
            blob = merged_block(soil_lines, i, 15)
            body, _ = matching_delim_text(blob, "{", "}", from_index=0)
            baseflow_conversion.append(fact({
                "topic": "baseflow_nijssen2001_to_arno_conversion",
                "statement": "When BASEFLOW==NIJSSEN2001, the d1/d2/d3/d4 parameters "
                              "read from the soil file are converted in place to the "
                              "ARNO Ds/Dsmax/Ws/c parameters vic_run itself uses.",
                "code": re.sub(r"\s+", " ", (body or "")).strip()[:600],
            }, READ_SOILPARAM_C, i, driver="classic"))

    # -- Classic veg param / veg library: option-gated leading skip counts and
    # sequential fscanf column reads (lighter-weight extraction: gate citations only,
    # not a full column-by-column layout -- see known_gaps). --
    vegparam_lines = read_lines(root / READ_VEGPARAM_C)
    vegparam_gates = []
    for i in range(1, len(vegparam_lines)):
        line = vegparam_lines[i]
        if line is None:
            continue
        if re.search(r"options\.VEGPARAM_(LAI|ALB|FCAN)", line):
            vegparam_gates.append(fact({"text": line.strip()}, READ_VEGPARAM_C, i, driver="classic"))

    veglib_lines = read_lines(root / READ_VEGLIB_C)
    veglib_gates = []
    for i in range(1, len(veglib_lines)):
        line = veglib_lines[i]
        if line is None:
            continue
        if re.search(r"options\.(CARBON|VEGLIB_PHOTO|VEGLIB_FCAN)\b", line):
            veglib_gates.append(fact({"text": line.strip()}, READ_VEGLIB_C, i, driver="classic"))

    # -- Image NetCDF parameter variable reads (vic_init.c): get_scatter_nc_field_*
    # calls map a NetCDF variable name to an internal soil_con/veg_con struct field
    # via the copy loop immediately following the read call. --
    image_lines = read_lines(root / VIC_INIT_C)
    image_stacks = c_if_stack_by_line(image_lines, 1, len(image_lines) - 1)
    # The call opener and the quoted NetCDF variable-name argument are not always on
    # the same source line (uncrustify wraps a long call onto a continuation line) --
    # matched below against a few merged lines starting at the call opener, not
    # against a single line, so a wrapped call site is not silently missed (independent review
    # C4: bulk_density_org/bulk_density_comb/max_snow_distrib_slope were missed this
    # way -- their name literal is the first token of the continuation line).
    nc_field_open_re = re.compile(r'get_scatter_nc_field_(double|int|float)\s*\(')
    nc_field_name_re = re.compile(r'"([A-Za-z0-9_]+)"')
    struct_field_re = re.compile(r'=\s*\(\w+\)\s*\w+\[\w+\]\s*;')
    assign_field_re = re.compile(r'(\w+)\[\w+\]\s*\.\s*(\w+)\s*=')
    image_params = []
    for i in range(1, len(image_lines)):
        line = image_lines[i]
        if line is None:
            continue
        om = nc_field_open_re.search(line)
        if not om:
            continue
        blob = merged_block(image_lines, i, 5)
        nm = nc_field_name_re.search(blob[om.start():])
        if not nm:
            continue
        nc_type, nc_name = om.group(1), nm.group(1)
        # The internal struct field this variable is copied into is set by a
        # `<struct>[i].<field> = (type) <dvar-name>[i];` line within the next ~6
        # lines (the read call's own copy loop) -- best-effort, not guaranteed for
        # every call site (see known_gaps).
        internal_field = None
        for j in range(i, min(i + 8, len(image_lines))):
            l2 = image_lines[j]
            if l2 is None:
                continue
            fm = assign_field_re.search(l2)
            if fm:
                internal_field = f"{fm.group(1)}.{fm.group(2)}"
                break
        image_params.append(fact({
            "nc_variable": nc_name, "nc_type": nc_type, "internal_field": internal_field,
            "gate": [c for c in image_stacks.get(i, []) if c],
        }, VIC_INIT_C, i, driver="image"))

    # run_cell and Nveg are required image PARAMETER-file variables, but read outside
    # vic_init.c (in get_global_domain.c, via get_nc_field_* not get_scatter_nc_field_*
    # -- a different function name the scan above does not match), so the sweep above
    # alone misses both (independent review C6). Scanned directly here by the same literal-name
    # call pattern, restricted to the two call sites that read from the PARAMETER file
    # (param_nc_nameid / nc_nameid inside add_nveg_to_global_domain), not the domain
    # file's own lat/lon/mask/area/frac (a separate, already-declared known_gap).
    domain_file = "vic/drivers/shared_image/src/get_global_domain.c"
    domain_lines = read_lines(root / domain_file)
    param_field_re = re.compile(r'get_nc_field_(int|double|float)\(\s*\w*nameid\s*,\s*"(run_cell|Nveg)"')
    for i in range(1, len(domain_lines)):
        line = domain_lines[i]
        if line is None:
            continue
        m = param_field_re.search(line)
        if m:
            nc_type, nc_name = m.groups()
            image_params.append(fact({
                "nc_variable": nc_name, "nc_type": nc_type, "internal_field": None,
                "gate": [], "required": True,
            }, domain_file, i, driver="image"))

    entries_count = (len(soil_columns) + len(baseflow_conversion) + len(vegparam_gates)
                      + len(veglib_gates) + len(image_params))
    return {
        "pack": "vic", "catalog": "parameters",
        "generator": "tools/extract_pack.py --pack vic parameters", "generator_version": GENERATOR_VERSION,
        "scope": SCOPE, "count": entries_count,
        "classic_soil_columns": soil_columns,
        "classic_baseflow_conversion": baseflow_conversion,
        "classic_vegparam_option_gates": vegparam_gates,
        "classic_veglib_option_gates": veglib_gates,
        "image_netcdf_parameters": image_params,
        "note": "classic_soil_columns is in READ order (the file's actual column "
                "order), derived from read_soilparam.c's own "
                "'Can't find values for <NAME> in soil file' log_err markers, one per "
                "strtok column; per_layer=true columns repeat options.Nlayer times "
                "consecutively at that position. classic_vegparam_option_gates/"
                "classic_veglib_option_gates are gate citations only (VEGPARAM_LAI/"
                "VEGPARAM_ALB/VEGPARAM_FCAN extra lines per veg tile; CARBON/"
                "VEGLIB_PHOTO/VEGLIB_FCAN extra columns), not a full column-by-column "
                "layout -- see known_gaps. image_netcdf_parameters' internal_field is "
                "best-effort (the copy-loop assignment within a few lines of the read "
                "call); null where not found near the call site, never guessed.",
    }


# --------------------------------------------------------------------------------------
# state: STATE_* restart variables (image driver; state_metadata.c uses the identical
# strcpy(state_metadata[STATE_X].field, "value") shape as history_metadata.c) plus the
# writing-run-vs-reading-run consistency checks in vic_restore.c.
# --------------------------------------------------------------------------------------

_STATE_DIMID_RE = re.compile(r"nc\s*->\s*(\w+)_dimid")
_STATE_NC_DIMS_RE = re.compile(r"nc\s*->\s*nc_vars\s*\[\s*i\s*\]\s*\.\s*nc_dims\s*=\s*(\d+)\s*;")


def parse_state_dimensions(root):
    """set_nc_state_var_info's SECOND `switch (i) { case STATE_X: ... nc_dims = N;
    nc_dimids[...] = nc->X_dimid; ... break; }` block (vic_store.c): the state
    NetCDF file's per-variable rank and dimension-name list, the structured
    counterpart of catalogs/outputs.yaml's own `nelem` -- this catalog previously
    carried no shape information at all (independent review C16). Case groups (multiple `case
    STATE_X:` labels sharing one dims block) all get the same dims/dimid list, same
    pattern as parse_default_aggtype_switch. A STATE_* not covered by any case here is
    handled by set_nc_state_var_info_rout_extension (the routing-extension's own state,
    out of this pack's scope) -- left with dims=None rather than guessed."""
    start, end = find_function_body(read_lines(root / VIC_STORE), "set_nc_state_var_info")
    if start is None:
        return {}
    lines = read_lines(root / VIC_STORE)
    # The function's SECOND `switch (i) {` is the dims switch (the first sets nc_type).
    switch_starts = [i for i in range(start, end + 1)
                      if lines[i] and re.match(r"\s*switch\s*\(\s*i\s*\)\s*\{", lines[i])]
    if len(switch_starts) < 2:
        return {}
    sw_start = switch_starts[1]
    case_re = re.compile(r"^\s*case\s+(STATE_\w+)\s*:\s*$")
    pending = []
    result = {}
    for i in range(sw_start, end + 1):
        line = lines[i]
        if line is None:
            continue
        cm = case_re.match(line)
        if cm:
            pending.append((cm.group(1), i))
            continue
        dm = _STATE_NC_DIMS_RE.search(line)
        if dm and pending:
            dims_n = int(dm.group(1))
            # Collect the dimid names from this same case-group's block (from the
            # first pending case's line to the next 'break;').
            block_start = pending[0][1]
            block_end = i
            for j in range(i, min(i + 20, end + 1)):
                if lines[j] and re.match(r"\s*break\s*;", lines[j]):
                    block_end = j
                    break
            dimid_names = []
            for j in range(block_start, block_end + 1):
                if lines[j]:
                    dimid_names += _STATE_DIMID_RE.findall(lines[j])
            for name, case_line in pending:
                result[name] = {"nc_dims": dims_n, "dim_names": dimid_names, "line": case_line}
            pending = []
    return result


def cmd_state(root):
    hdr_lines = read_lines(root / HDR)
    state_start = None
    for i in range(1, len(hdr_lines)):
        if hdr_lines[i] and "STATE_SOIL_MOISTURE" in hdr_lines[i]:
            state_start = i
            break
    if state_start is None:
        sys.exit("ERROR: could not locate STATE_* enum in " + HDR)
    enum_entries = parse_enum_block(hdr_lines, state_start, "STATE_", "N_STATE_VARS")

    state_lines = read_lines(root / STATE_META)
    meta_start, meta_end = find_function_body(state_lines, "set_state_meta_data_info")
    if meta_start is None:
        sys.exit("ERROR: could not locate set_state_meta_data_info in " + STATE_META)
    meta = parse_metadata_strcpy_block(state_lines, meta_start, meta_end, "state_metadata", "STATE_")

    def resolve(m_dict, field, _depth=0):
        val = m_dict.get(field)
        if isinstance(val, dict) and "same_as" in val and _depth < 4:
            ref = val["same_as"]
            resolved, _ = resolve(meta.get(ref["variable"], {}), ref["field"], _depth + 1)
            return resolved
        return val if isinstance(val, str) else None

    dims = parse_state_dimensions(root)
    variables = []
    for e in enum_entries:
        name = e["name"]
        m = meta.get(name, {})
        entry = fact({
            "name": name,
            "long_name": resolve(m, "long_name"),
            "standard_name": resolve(m, "standard_name"),
            "units": resolve(m, "units"),
            "description": resolve(m, "description"),
            "header_comment": e["comment"] or None,
        }, STATE_META, (m.get("_lines", {}) or {}).get("varname", e["line"]), driver="image")
        # header_comment is the enum's OWN doxygen comment in vic_driver_shared_all.h
        # (HDR), not state_metadata.c -- a separate citation, not folded into `where`
        # (independent review C11: it was previously attributed only to state_metadata.c).
        entry["header_comment_where"] = where(HDR, e["line"], driver="image")
        d = dims.get(name)
        if d:
            entry["nc_dims"] = d["nc_dims"]
            entry["nc_dim_names"] = d["dim_names"]
            entry["dims_where"] = where(VIC_STORE, d["line"], driver="image")
        else:
            entry["nc_dims"] = None
            entry["nc_dim_names"] = None
            entry["dims_where"] = None
        variables.append(entry)

    # vic_restore.c's cross-run consistency checks: dimension comparisons between the
    # state file and the currently-configured run, each a "does/do not match" log_err.
    restore_lines = read_lines(root / VIC_RESTORE)
    checks = []
    for i in range(1, len(restore_lines)):
        line = restore_lines[i]
        if line is None or "log_err(" not in line:
            continue
        blob = merged_block(restore_lines, i, 6)
        msg = _blob_message(blob)
        if msg and ("does not match" in msg or "do not match" in msg):
            checks.append(fact({"message": msg}, VIC_RESTORE, i, driver="image"))

    return {
        "pack": "vic", "catalog": "state",
        "generator": "tools/extract_pack.py --pack vic state", "generator_version": GENERATOR_VERSION,
        "scope": SCOPE, "count": len(variables),
        "variables": variables,
        "consistency_checks": checks,
        "consistency_checks_count": len(checks),
        "note": "STATE_* variable metadata (state_metadata.c's set_state_meta_data_info) "
                "and NetCDF shape (vic_store.c's set_nc_state_var_info, `nc_dims`/"
                "`nc_dim_names`/`dims_where`) for the IMAGE driver's state file only "
                "(the file this catalog reads lives under drivers/shared_image, not "
                "shared_all -- `scope` names both drivers because the pinned commit as "
                "a whole covers both, not because this catalog's own content does; the "
                "classic driver's own state-file writer/reader has no equivalent "
                "metadata table and was not reached by this extraction pass, see "
                "known_gaps). `header_comment` is the STATE_* enum's own doxygen "
                "comment in vic_driver_shared_all.h -- `header_comment_where` cites "
                "that file, separate from `where` (state_metadata.c). `count` is the "
                "number of `variables` entries only, matching every other catalog's own "
                "convention; `consistency_checks_count` is the separate count of "
                "`consistency_checks` entries (do not add the two together -- they are "
                "different lists, not one). consistency_checks are the dimension/option "
                "cross-checks vic_restore.c runs between the state file being read and "
                "the currently-configured run (grid size, veg classes, snow bands, "
                "soil layers, frost areas, soil nodes, lake nodes, soil node depths) "
                "before accepting it -- these are the options that MUST match between "
                "the writing and reading run.",
    }


# --------------------------------------------------------------------------------------
# CLI wiring
# --------------------------------------------------------------------------------------

CATALOGS = {
    "outputs": cmd_outputs,
    "global-parameters": cmd_global_parameters,
    "options": cmd_options,
    "constants": cmd_constants,
    "model-parameters": cmd_model_parameters,
    "forcing": cmd_forcing,
    "parameters": cmd_parameters,
    "state": cmd_state,
}
FILENAME = {
    "outputs": "outputs.yaml",
    "global-parameters": "global_parameters.yaml",
    "options": "options.yaml",
    "constants": "constants.yaml",
    "model-parameters": "model_parameters.yaml",
    "forcing": "forcing.yaml",
    "parameters": "parameters.yaml",
    "state": "state.yaml",
}


def write_yaml(obj, out_path, command_name):
    header = [
        f"Generated by tools/extract_pack.py --pack vic {command_name} -- do not hand-edit.",
        f"Regenerate: python3 tools/extract_pack.py --pack vic {command_name} "
        f"--source-root <pinned-VIC-checkout> --out {out_path.name}",
        f"Source commit: vic@{VIC_COMMIT} (tag {VIC_TAG}); sample data {SAMPLE_DATA_COMMIT}.",
    ]
    _common.write_yaml(obj, out_path, header)
