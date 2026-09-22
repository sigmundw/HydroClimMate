"""extractors/mizuroute.py -- mechanical, deterministic extractor module for the
mizuRoute knowledge pack's catalogs, dispatched by tools/extract_pack.py --pack
mizuroute. Every function here reads the pinned mizuRoute source tree given by
--source-root and returns one catalog's data (see SCHEMA.md). Nothing here is
hand-typed: each fact is produced by a regex/parse pass over the actual Fortran
source, and carries `where` = {file, line, commit} pointing at the exact source
line(s) it came from, plus a `runmode` field (standalone | cesm-coupling | both)
stating which run mode(s) the fact applies to.

Pinned source: mizuRoute tag v3.1.1, commit 28514dea (see version_scope in pack.yaml).
Scope: the standalone driver (route/build/src/standalone/route_runoff.f90) is primary;
cime/coupled facts are carried only where the pinned code itself branches on
globalData's `runMode`. CODE WINS over docs/ -- any docs/ text read here is
cross-reference only, and a disagreement between docs/ and code is recorded as a
fact (see each catalog's `documented_but_not_parsed` / `doc_disagreements`), never
silently resolved.

No mizuRoute input or output data exists anywhere reachable by this pack except the
two sample control files shipped in the checkout (route/settings/SAMPLE.control and
SAMPLE-coupled.control). Every fact therefore starts `evidence: source_read`; a
control-key fact whose key one of those two sample control files actually uses is
upgraded to `confirmed_in_sample_input`. Nothing in this pack may ever carry
`observed_in_output` or `both`, since no model output exists to observe against.

Source-root layout expected (matches the pinned mizuRoute checkout):
  <root>/route/build/src/public_var.f90              (control variables, defaults, constants)
  <root>/route/build/src/read_control.f90            (control-file tag parser, unit conversion)
  <root>/route/build/src/var_lookup.f90              (named-variable index structures)
  <root>/route/build/src/popMetadat.f90              (name/description/units/dims metadata)
  <root>/route/build/src/globalData.f90              (runtime globals, routing parameters)
  <root>/route/build/src/dataTypes.f90               (RCHPRP reach-parameter type)
  <root>/route/build/src/init_model_data.f90         (routing-method object dispatch)
  <root>/route/build/src/histVars_data.f90           (history accumulation/reset; method->variable map)
  <root>/route/build/src/write_simoutput_pio.f90     (history file naming, output alarms)
  <root>/route/build/src/write_restart_pio.f90       (restart file naming, restart alarm)
  <root>/route/build/src/read_streamSeg.f90          (river-network read; required-variable promotion)
  <root>/route/build/src/read_param.f90              (spatially constant parameter namelist)
  <root>/route/build/src/process_param.f90           (basin UH and Saint-Venant UH construction)
  <root>/route/build/src/process_ntopo.f90           (derived reach parameters)
  <root>/route/build/src/domain_decomposition.f90    (MPI/OpenMP decomposition)
  <root>/route/build/src/standalone/read_runoff.f90  (runoff input reading)
  <root>/route/build/src/standalone/read_remap.f90   (remapping file reading)
  <root>/route/build/src/standalone/get_basin_runoff.f90 (forcing scale/offset, time mapping)
  <root>/route/build/Makefile                        (build requirements)
  <root>/route/settings/SAMPLE.control               (sample control file, standalone)
  <root>/route/settings/SAMPLE-coupled.control       (sample control file, coupled)
  <root>/docs/source/users_guide/*.rst               (in-repo docs, cross-reference only)
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import _miniyaml  # noqa: E402,F401  (imported for parity with the other extractors)
sys.path.insert(0, str(Path(__file__).resolve().parent))
import _common  # noqa: E402

GENERATOR_VERSION = "1.0.0"
# Canonical short form: `git rev-parse --short=8` in the pinned checkout.
MIZU_COMMIT = "28514dea"
MIZU_TAG = "v3.1.1"
SCOPE = (f"mizuRoute {MIZU_COMMIT} (tag {MIZU_TAG}); standalone driver route_runoff; "
         f"cesm-coupling noted only where the code branches on runMode")

PACK = "mizuroute"
SOURCE_COMMITS = {"mizuroute": MIZU_COMMIT}

read_lines = _common.read_lines
relpath = _common.relpath

# --------------------------------------------------------------------------------------
# Source paths (relative to --source-root), one constant per file this extractor reads.
# --------------------------------------------------------------------------------------
SRC = "route/build/src"
STA = "route/build/src/standalone"

PUBLIC_VAR = f"{SRC}/public_var.f90"
READ_CONTROL = f"{SRC}/read_control.f90"
VAR_LOOKUP = f"{SRC}/var_lookup.f90"
POP_METADAT = f"{SRC}/popMetadat.f90"
GLOBAL_DATA = f"{SRC}/globalData.f90"
DATA_TYPES = f"{SRC}/dataTypes.f90"
INIT_MODEL = f"{SRC}/init_model_data.f90"
HIST_VARS = f"{SRC}/histVars_data.f90"
WRITE_SIMOUT = f"{SRC}/write_simoutput_pio.f90"
WRITE_RESTART = f"{SRC}/write_restart_pio.f90"
READ_STREAMSEG = f"{SRC}/read_streamSeg.f90"
READ_PARAM = f"{SRC}/read_param.f90"
PROCESS_PARAM = f"{SRC}/process_param.f90"
PROCESS_NTOPO = f"{SRC}/process_ntopo.f90"
DOMAIN_DECOMP = f"{SRC}/domain_decomposition.f90"
MPI_PROCESS = f"{SRC}/mpi_process.f90"
BASE_ROUTE = f"{SRC}/base_route.f90"
LAKE_ROUTE = f"{SRC}/lake_route.f90"
READ_RUNOFF = f"{STA}/read_runoff.f90"
READ_REMAP = f"{STA}/read_remap.f90"
GET_BASIN_RUNOFF = f"{STA}/get_basin_runoff.f90"
ROUTE_RUNOFF = f"{STA}/route_runoff.f90"
MAKEFILE = "route/build/Makefile"
SAMPLE_CONTROLS = ("route/settings/SAMPLE.control", "route/settings/SAMPLE-coupled.control")
DOCS_DIR = "docs/source/users_guide"


# --------------------------------------------------------------------------------------
# Generic Fortran-source helpers. None of this is mizuRoute-specific in shape; it stays
# local to this module because no second Fortran free-form pack needs it yet.
# --------------------------------------------------------------------------------------

def strip_comment(line):
    """Split a free-form Fortran line into (code, comment), honouring single-quoted
    string literals so a `!` inside a literal is not mistaken for a comment start."""
    in_str = False
    for i, ch in enumerate(line):
        if ch == "'":
            in_str = not in_str
        elif ch == "!" and not in_str:
            return line[:i], line[i + 1:].strip()
    return line, None


def squeeze(text):
    """Collapse all runs of whitespace; used to normalize a Fortran expression that the
    source spaces out for column alignment (e.g. `meta_SEG    (ixSEG%length   )%varName`)."""
    return re.sub(r"\s+", "", text or "")


def where(rel_path, line, runmode="both"):
    return {"file": rel_path, "line": line, "commit": f"mizuroute@{MIZU_COMMIT}",
            "runmode": runmode}


def fact(payload, rel_path, line, runmode="both", evidence="source_read"):
    out = dict(payload)
    out["where"] = where(rel_path, line, runmode)
    out["evidence"] = evidence
    out["scope"] = SCOPE
    return out


def find_block(lines, start_pat, end_pat, after=1):
    """First [start, end] 1-indexed line pair whose lines match the two regexes."""
    start = None
    for i in range(after, len(lines)):
        if lines[i] is None:
            continue
        if start is None:
            if re.search(start_pat, lines[i]):
                start = i
        elif re.search(end_pat, lines[i]):
            return start, i
    return (start, len(lines) - 1) if start is not None else (None, None)


_CASE_LABEL_RE = re.compile(r"case\s*\((?P<labels>[^)]*)\)", re.IGNORECASE)
_QUOTED_RE = re.compile(r"'([^']*)'")


def _longest_message(candidates):
    """The longest quoted literal that reads as an error message rather than as a
    Fortran format string or a single identifier: it has to contain a space."""
    msgs = [c for c in candidates if " " in c.strip() and len(c.strip()) > 10]
    return max(msgs, key=len) if msgs else None


def scan_all_select_cases(lines, anchor):
    """Every `select case(<anchor>)` block in the file, in source order."""
    target = squeeze(anchor)
    out = []
    at = 1
    while True:
        hit = None
        for i in range(at, len(lines)):
            if lines[i] is None:
                continue
            code, _ = strip_comment(lines[i])
            if target in squeeze(code):
                hit = i
                break
        if hit is None:
            return out
        out.append(scan_select_case(lines, anchor, start_at=hit))
        at = hit + 1


def scan_select_case(lines, anchor, start_at=1):
    """Walk the `select case(<anchor>)` block that begins at the first line containing
    `anchor` and return {labels, default_message, select_line, cases:[{labels, line,
    action}]}. `anchor` is matched literally after whitespace-squeezing, so the caller
    may write the select expression exactly as the source does, spacing aside."""
    target = squeeze(anchor)
    sel_line = None
    for i in range(start_at, len(lines)):
        if lines[i] is None:
            continue
        code, _ = strip_comment(lines[i])
        if target in squeeze(code):
            sel_line = i
            break
    if sel_line is None:
        sys.exit(f"ERROR: could not locate select block for anchor {anchor!r}")
    cases = []
    default_message = None
    default_line = None
    for i in range(sel_line + 1, len(lines)):
        if lines[i] is None:
            break
        code, _ = strip_comment(lines[i])
        squeezed = squeeze(code)
        if squeezed.lower().startswith("endselect") or squeezed.lower().startswith("end select"):
            break
        if re.match(r"^\s*end\s*select", code, re.IGNORECASE):
            break
        if re.match(r"^\s*case\s*default", code, re.IGNORECASE):
            default_line = i
            # The default branch's own error text may continue on the next lines.
            blob = " ".join(
                (strip_comment(lines[j])[0] or "") for j in range(i, min(i + 4, len(lines)))
                if lines[j] is not None)
            default_message = _longest_message(_QUOTED_RE.findall(blob))
            continue
        m = re.match(r"^\s*case\s*\(", code, re.IGNORECASE)
        if m:
            labmatch = _CASE_LABEL_RE.search(code)
            if not labmatch:
                continue
            raw = labmatch.group("labels")
            labels = _QUOTED_RE.findall(raw)
            if not labels:
                labels = [t.strip() for t in raw.split(",") if t.strip()]
            action = code[labmatch.end():].lstrip(" ;").strip()
            if not action:
                # A `case(...)` arm whose statement is on the following line(s): take the
                # first non-blank line of the arm, which is what the arm actually does.
                for j in range(i + 1, min(i + 4, len(lines))):
                    if lines[j] is None:
                        break
                    nxt, _ = strip_comment(lines[j])
                    if nxt.strip():
                        if not re.match(r"^\s*case\b", nxt, re.IGNORECASE):
                            action = re.sub(r"\s+", " ", nxt.strip())
                        break
            cases.append({"labels": labels, "line": i, "action": action or None})
    return {"select_line": sel_line, "cases": cases,
            "default_message": default_message, "default_line": default_line}


# --------------------------------------------------------------------------------------
# public_var.f90: control variables, their declared type, default and trailing comment.
# --------------------------------------------------------------------------------------

_DECL_RE = re.compile(
    r"^\s*(?P<type>(?:character|integer|real|logical)\s*(?:\([^)]*\))?)"
    r"\s*,(?P<attrs>[^:]*?)::\s*(?P<name>\w+)\s*=\s*(?P<default>.+?)\s*$",
    re.IGNORECASE)


def parse_public_var(root):
    """Every `<type>, [parameter,] public :: name = default ! comment` declaration in
    public_var.f90, with the most recent comment-only heading line as its `section`."""
    lines = read_lines(root / PUBLIC_VAR)
    out = {}
    order = []
    section = None
    for i in range(1, len(lines)):
        if lines[i] is None:
            continue
        code, comment = strip_comment(lines[i])
        if not code.strip():
            if comment:
                head = comment.strip().strip("-").strip()
                if head and len(head) <= 80:
                    section = head
            continue
        m = _DECL_RE.match(code)
        if not m:
            continue
        name = m.group("name")
        attrs = m.group("attrs").lower()
        out[name] = {
            "name": name,
            "fortran_type": re.sub(r"\s+", "", m.group("type")),
            "is_parameter": "parameter" in attrs,
            "default_literal": m.group("default").strip(),
            "declaration_comment": comment,
            "section": section,
            "line": i,
        }
        order.append(name)
    return out, order


_MISSING_SENTINELS = ("charMissing", "realMissing", "integerMissing", "floatMissing")


def _requiredness(default_literal):
    """A control variable initialised to one of public_var's own missing-value sentinels
    has no usable default, so the control file must set it; anything else has one."""
    if default_literal in _MISSING_SENTINELS:
        return "must_be_set_in_control_file"
    return "optional_has_default"


# --------------------------------------------------------------------------------------
# read_control.f90: the control-file tag table (the big select/case on `trim(cName)`).
# --------------------------------------------------------------------------------------

_CTL_CASE_RE = re.compile(r"^\s*case\s*\(\s*'<(?P<key>\w+)>'\s*\)\s*;?\s*(?P<body>.*)$",
                          re.IGNORECASE)
_READ_RE = re.compile(r"read\s*\(\s*cData\s*,\s*\*\s*,\s*iostat\s*=\s*io_error\s*\)\s*(?P<t>.+)$",
                      re.IGNORECASE)
_ASSIGN_RE = re.compile(r"^(?P<t>.+?)=\s*trim\s*\(\s*cData\s*\)\s*$", re.IGNORECASE)
_META_RE = re.compile(r"^meta_(?P<struct>\w+)\((?:ix)(?P<ix>\w+)%(?P<member>\w+)\)%(?P<field>varFile|varName)$")


def parse_control_keys_table(root):
    """Every `case('<tag>')` arm of read_control.f90's control-file tag select, with the
    variable (or metadata field) it writes and the arm's own trailing comment."""
    lines = read_lines(root / READ_CONTROL)
    start, end = find_block(lines, r"select\s+case\s*\(\s*trim\s*\(\s*cName\s*\)\s*\)",
                            r"^\s*end\s*select")
    if start is None:
        sys.exit("ERROR: could not locate the control-file tag select in " + READ_CONTROL)
    entries = []
    section = None
    for i in range(start + 1, end + 1):
        if lines[i] is None:
            continue
        code, comment = strip_comment(lines[i])
        if not code.strip():
            if comment:
                head = comment.strip().strip("-").strip()
                if head and len(head) <= 90 and not head.startswith("if "):
                    section = head
            continue
        m = _CTL_CASE_RE.match(code)
        if not m:
            continue
        body = m.group("body").strip().rstrip(";").strip()
        target, read_form = None, None
        rm = _READ_RE.search(body)
        if rm:
            target, read_form = squeeze(rm.group("t")), "list_directed_read"
        else:
            am = _ASSIGN_RE.match(body)
            if am:
                target, read_form = squeeze(am.group("t")), "trim_assignment"
        entry = {"key": m.group("key"), "assigns_to": target, "read_form": read_form,
                 "case_comment": comment, "section": section, "line": i}
        if target:
            mm = _META_RE.match(target)
            if mm:
                entry["metadata_target"] = {
                    "structure": f"meta_{mm.group('struct')}",
                    "member": mm.group("member"),
                    "field": mm.group("field"),
                }
        entries.append(entry)
    default_msg = None
    for i in range(start, end + 1):
        if lines[i] is not None and re.match(r"^\s*case\s+default", lines[i], re.IGNORECASE):
            blob = " ".join((strip_comment(lines[j])[0] or "")
                            for j in range(i, min(i + 4, len(lines))) if lines[j] is not None)
            default_msg = _longest_message(_QUOTED_RE.findall(blob))
            break
    return entries, default_msg, (start, end)


# --------------------------------------------------------------------------------------
# Allowed-value sets: each is a `select case` (or, for ro_time_stamp, an explicit
# equality chain) elsewhere in the code that constrains one control variable's value.
# --------------------------------------------------------------------------------------

_ALLOWED_SPECS = [
    # (control variable, file, select anchor, note)
    ("units_qsim_length", READ_CONTROL, "select case(trim(cLength))",
     "length part of <units_qsim>, the text before the '/'"),
    ("units_qsim_time", READ_CONTROL, "select case(trim(cTime))",
     "time part of <units_qsim>, the text after the '/'"),
    ("units_cc_mass", READ_CONTROL, "select case(trim(cMass))",
     "mass part of <units_cc>, read only when <tracer> is true"),
    ("outputFrequency", READ_CONTROL, "select case(trim(outputFrequency))",
     "a literal keyword, otherwise parsed as a positive integer number of simulation steps"),
    ("newFileFrequency", WRITE_SIMOUT, "select case(trim(newFileFrequency))",
     "history file-rollover keyword, used to build the file-name time stamp"),
    ("restart_write", WRITE_RESTART, "select case(lower(trim(restart_write)))",
     "restart write keyword; matched case-insensitively via ascii_utils lower()"),
]


def parse_allowed_values(root):
    """One allowed-value set per constrained control variable, read from the select
    block that actually constrains it (not from any doc list)."""
    out = {}
    for name, rel, anchor, note in _ALLOWED_SPECS:
        lines = read_lines(root / rel)
        start_at = 1
        if name == "units_cc_mass":
            pass
        blk = scan_select_case(lines, anchor, start_at=start_at)
        values = []
        for c in blk["cases"]:
            values.append({"values": c["labels"], "action": c["action"],
                           "where": where(rel, c["line"])})
        out[name] = {"variable": name, "note": note, "values": values,
                     "rejection_message": blk["default_message"],
                     "where": where(rel, blk["select_line"])}
    # The second `select case(trim(cTime))` in read_control.f90 constrains the solute
    # mass-flux time unit, not the runoff one; find it after the first.
    lines = read_lines(root / READ_CONTROL)
    first = out["units_qsim_time"]["where"]["line"]
    blk = scan_select_case(lines, "select case(trim(cTime))", start_at=first + 1)
    out["units_cc_time"] = {
        "variable": "units_cc_time",
        "note": "time part of <units_cc>, read only when <tracer> is true",
        "values": [{"values": c["labels"], "action": c["action"],
                    "where": where(READ_CONTROL, c["line"])} for c in blk["cases"]],
        "rejection_message": blk["default_message"],
        "where": where(READ_CONTROL, blk["select_line"]),
    }
    # ro_time_stamp is constrained by an explicit equality chain, not a select.
    for i in range(1, len(lines)):
        if lines[i] is None:
            continue
        code, _ = strip_comment(lines[i])
        if "ro_time_stamp)=='start'" in squeeze(code):
            vals = _QUOTED_RE.findall(code)
            blob = " ".join((strip_comment(lines[j])[0] or "")
                            for j in range(i, min(i + 6, len(lines))) if lines[j] is not None)
            errs = [s for s in _QUOTED_RE.findall(blob) if "must be" in s]
            out["ro_time_stamp"] = {
                "variable": "ro_time_stamp",
                "note": "checked by an explicit equality chain, not a select block",
                "values": [{"values": vals, "action": None, "where": where(READ_CONTROL, i)}],
                "rejection_message": errs[0] if errs else None,
                "where": where(READ_CONTROL, i),
            }
            break
    return out


# The allowed-value set that applies to each control key, by the variable the key writes.
_ALLOWED_FOR_KEY = {
    "units_qsim": ["units_qsim_length", "units_qsim_time"],
    "units_cc": ["units_cc_mass", "units_cc_time"],
    "outputFrequency": ["outputFrequency"],
    "newFileFrequency": ["newFileFrequency"],
    "restart_write": ["restart_write"],
    "ro_time_stamp": ["ro_time_stamp"],
}


# --------------------------------------------------------------------------------------
# read_control.f90's post-loop consistency constraints (each its own error message).
# --------------------------------------------------------------------------------------

def parse_control_constraints(root, table_end):
    """Every explicit post-parse rejection in read_control.f90 after the tag loop: the
    error text the model prints and the source line that raises it."""
    lines = read_lines(root / READ_CONTROL)
    out = []
    for i in range(table_end, len(lines)):
        if lines[i] is None:
            continue
        code, _ = strip_comment(lines[i])
        if "message" not in code or "err=" not in " ".join(
                (strip_comment(lines[j])[0] or "") for j in range(i, min(i + 3, len(lines)))
                if lines[j] is not None):
            continue
        msg = _longest_message(_QUOTED_RE.findall(code))
        if not msg:
            continue
        out.append(fact({"message": msg}, READ_CONTROL, i))
    return out


# --------------------------------------------------------------------------------------
# Sample control files and in-repo docs (cross-reference only; code wins).
# --------------------------------------------------------------------------------------

_SAMPLE_KEY_RE = re.compile(r"^\s*<(?P<key>\w+)>\s+(?P<value>\S.*?)\s*(?:!(?P<comment>.*))?$")


def parse_sample_controls(root):
    """{sample file name: {key: {value, line}}} for the two shipped sample control
    files, parsed by read_control.f90's own line grammar (`<tag> value ! comment`)."""
    out = {}
    for rel in SAMPLE_CONTROLS:
        path = root / rel
        if not path.is_file():
            continue
        keys = {}
        lines = read_lines(path)
        for i in range(1, len(lines)):
            if lines[i] is None or not lines[i].strip() or lines[i].lstrip().startswith("!"):
                continue
            m = _SAMPLE_KEY_RE.match(lines[i])
            if m:
                keys[m.group("key")] = {"value": m.group("value").strip(), "line": i}
        out[Path(rel).name] = keys
    return out


_DOC_TABLE_RE = re.compile(r"^\s*\*\s*-\s*``<(?P<key>\w+)>``\s*$")
_DOC_EXAMPLE_RE = re.compile(r"^\s{0,4}<(?P<key>\w+)>\s+\S")


def parse_doc_keys(root):
    """Control keys the in-repo docs present as real keys: a `list-table` row cell of the
    form ``<key>``, or a line of an embedded example control file. Section labels and
    prose placeholders are not matched by either form, so they never enter this set.
    A doc-table row also carries the documented type and default, taken from the two
    cells that follow it, purely for cross-reference -- code wins on any disagreement."""
    docs = root / DOCS_DIR
    found = {}
    if not docs.is_dir():
        return found
    for path in sorted(docs.glob("*.rst")):
        rel = relpath(root, path)
        lines = read_lines(path)
        for i in range(1, len(lines)):
            if lines[i] is None:
                continue
            m = _DOC_TABLE_RE.match(lines[i])
            if m:
                cells = []
                for j in range(i + 1, min(i + 4, len(lines))):
                    if lines[j] is None:
                        break
                    cm = re.match(r"^\s*-\s*(.*?)\s*$", lines[j])
                    if not cm:
                        break
                    cells.append(cm.group(1))
                rec = found.setdefault(m.group("key"), {"doc_where": where(rel, i),
                                                        "doc_type": None,
                                                        "doc_default": None,
                                                        "doc_forms": []})
                rec["doc_forms"].append("table_row")
                if len(cells) >= 2 and rec["doc_type"] is None:
                    rec["doc_type"] = cells[0] or None
                    rec["doc_default"] = cells[1] or None
                continue
            m = _DOC_EXAMPLE_RE.match(lines[i])
            if m:
                rec = found.setdefault(m.group("key"), {"doc_where": where(rel, i),
                                                        "doc_type": None,
                                                        "doc_default": None,
                                                        "doc_forms": []})
                if "example_control_file" not in rec["doc_forms"]:
                    rec["doc_forms"].append("example_control_file")
    for rec in found.values():
        rec["doc_forms"] = sorted(set(rec["doc_forms"]))
    return found


# --------------------------------------------------------------------------------------
# popMetadat.f90 metadata tables.
# --------------------------------------------------------------------------------------

_VAR_INFO_RE = re.compile(
    r"^\s*meta_(?P<struct>\w+)\s*\(\s*ix(?P<ix>\w+)%(?P<member>\w+)\s*\)\s*=\s*var_info\s*\("
    r"\s*'(?P<name>[^']*)'\s*,\s*'(?P<desc>[^']*)'\s*,\s*'(?P<unit>[^']*)'\s*,"
    r"\s*ixDims%(?P<dim>\w+)\s*,\s*\.(?P<varfile>true|false)\.\s*\)", re.IGNORECASE)

_INIT_RE = re.compile(
    r"^\s*call\s+meta_(?P<struct>\w+)\s*\(\s*ix(?P<ix>\w+)%(?P<member>\w+)\s*\)\s*%init\s*\("
    r"\s*'(?P<name>[^']*)'\s*,\s*'(?P<desc>[^']*)'\s*,\s*'(?P<unit>[^']*)'\s*,"
    r"\s*(?P<nctype>\w+)\s*,\s*\[(?P<dims>[^\]]*)\]\s*,\s*\.(?P<varfile>true|false)\.\s*\)",
    re.IGNORECASE)


def parse_var_info(root):
    """Every `meta_X(ixY%member) = var_info(name, desc, unit, ixDims%dim, varFile)` call
    in popMetadat.f90 -- the river-network (input) metadata tables."""
    lines = read_lines(root / POP_METADAT)
    out = []
    for i in range(1, len(lines)):
        if lines[i] is None:
            continue
        code, _ = strip_comment(lines[i])
        m = _VAR_INFO_RE.match(code)
        if m:
            out.append({"structure": f"meta_{m.group('struct')}",
                        "member": m.group("member"),
                        "default_varname": m.group("name"),
                        "description": m.group("desc"),
                        "units": m.group("unit"),
                        "dimension": m.group("dim"),
                        "read_by_default": m.group("varfile").lower() == "true",
                        "line": i})
    return out


def parse_init_meta(root):
    """Every `call meta_X(ixY%member)%init(name, desc, unit, nctype, [dims], writeOut)`
    call in popMetadat.f90 -- the history-output and restart metadata tables."""
    lines = read_lines(root / POP_METADAT)
    out = []
    for i in range(1, len(lines)):
        if lines[i] is None:
            continue
        code, _ = strip_comment(lines[i])
        m = _INIT_RE.match(code)
        if m:
            dims = [squeeze(d).split("%")[-1] for d in m.group("dims").split(",") if d.strip()]
            out.append({"structure": f"meta_{m.group('struct')}",
                        "member": m.group("member"),
                        "name": m.group("name"),
                        "long_name": m.group("desc"),
                        "units": m.group("unit"),
                        "netcdf_type": m.group("nctype"),
                        "dimensions": dims,
                        "default_write": m.group("varfile").lower() == "true",
                        "line": i})
    return out


# --------------------------------------------------------------------------------------
# var_lookup.f90 index structures (member -> its own declaration comment).
# --------------------------------------------------------------------------------------

_ILOOK_MEMBER_RE = re.compile(r"^\s*integer\(i4b\)\s*::\s*(?P<member>\w+)\s*=\s*integerMissing",
                              re.IGNORECASE)


def parse_var_lookup(root):
    """{iLook_<NAME>: {member: {comment, line}}} for every index structure."""
    lines = read_lines(root / VAR_LOOKUP)
    out = {}
    current = None
    for i in range(1, len(lines)):
        if lines[i] is None:
            continue
        code, comment = strip_comment(lines[i])
        m = re.match(r"^\s*type,\s*public\s*::\s*(iLook_\w+)", code, re.IGNORECASE)
        if m:
            current = m.group(1)
            out[current] = {}
            continue
        if re.match(r"^\s*endtype", code, re.IGNORECASE):
            current = None
            continue
        if current:
            mm = _ILOOK_MEMBER_RE.match(code)
            if mm:
                text = (comment or "").strip()
                text = re.sub(r"^\d+\.\s*", "", text)
                out[current][mm.group("member")] = {"comment": text or None, "line": i}
    return out


# --------------------------------------------------------------------------------------
# CATALOG a: control_keys
# --------------------------------------------------------------------------------------

def cmd_control_keys(root):
    pv, _ = parse_public_var(root)
    table, default_msg, (tstart, tend) = parse_control_keys_table(root)
    allowed = parse_allowed_values(root)
    samples = parse_sample_controls(root)
    doc_keys = parse_doc_keys(root)
    constraints = parse_control_constraints(root, tend)

    keys = []
    parsed_names = set()
    for e in table:
        parsed_names.add(e["key"])
        target = e["assigns_to"]
        decl = pv.get(target) if target else None
        runmode = "cesm-coupling" if (e.get("section") or "").lower().startswith("cesm") else "both"
        payload = {
            "key": e["key"],
            "section_in_parser": e["section"],
            "assigns_to": target,
            "read_form": e["read_form"],
            "meaning": e["case_comment"] or (decl or {}).get("declaration_comment"),
            "declaration_comment": (decl or {}).get("declaration_comment"),
            "fortran_type": (decl or {}).get("fortran_type"),
            "default_literal": (decl or {}).get("default_literal"),
            "requiredness": (_requiredness(decl["default_literal"]) if decl
                             else "set_by_this_key_only"),
        }
        if e.get("metadata_target"):
            payload["metadata_target"] = e["metadata_target"]
            payload["requiredness"] = "optional_has_default"
            payload["default_literal"] = None
            payload["fortran_type"] = ("logical(lgt)"
                                       if e["metadata_target"]["field"] == "varFile"
                                       else "character(*)")
        if decl:
            payload["declared_where"] = where(PUBLIC_VAR, decl["line"])
        names = _ALLOWED_FOR_KEY.get(target or "", [])
        if names:
            payload["allowed_values"] = [allowed[n] for n in names if n in allowed]
        in_samples = sorted(s for s, ks in samples.items() if e["key"] in ks)
        payload["used_in_sample_control_files"] = in_samples
        if in_samples:
            payload["sample_values"] = [
                {"file": s, "value": samples[s][e["key"]]["value"],
                 "line": samples[s][e["key"]]["line"]} for s in in_samples]
        doc = doc_keys.get(e["key"])
        payload["documented_in_docs"] = bool(doc)
        if doc:
            payload["doc_type"] = doc["doc_type"]
            payload["doc_default"] = doc["doc_default"]
            payload["doc_forms"] = doc["doc_forms"]
            payload["doc_where"] = doc["doc_where"]
        evidence = "confirmed_in_sample_input" if in_samples else "source_read"
        keys.append(fact(payload, READ_CONTROL, e["line"], runmode=runmode, evidence=evidence))

    documented_not_parsed = []
    for name in sorted(set(doc_keys) - parsed_names):
        d = doc_keys[name]
        documented_not_parsed.append(fact(
            {"key": name, "doc_forms": d["doc_forms"], "doc_type": d["doc_type"],
             "doc_default": d["doc_default"],
             "consequence": "read_control.f90 has no case for this tag, so a control "
                            "file containing it is rejected by the case-default arm"},
            d["doc_where"]["file"], d["doc_where"]["line"]))

    sample_not_parsed = []
    for sname, ks in samples.items():
        for k, v in sorted(ks.items()):
            if k not in parsed_names:
                sample_not_parsed.append(fact(
                    {"key": k, "sample_file": sname, "sample_value": v["value"],
                     "consequence": "read_control.f90 has no case for this tag, so this "
                                    "sample control file as shipped is rejected by the "
                                    "case-default arm"},
                    [r for r in SAMPLE_CONTROLS if Path(r).name == sname][0], v["line"]))

    return {
        "pack": PACK, "catalog": "control_keys",
        "generator": "tools/extract_pack.py --pack mizuroute control-keys",
        "generator_version": GENERATOR_VERSION, "scope": SCOPE,
        "entries_key": "keys", "entry_kind": "mizuRoute control-file key",
        "count": len(keys),
        "keys": keys,
        "unrecognized_key_message": default_msg,
        "post_parse_constraints": constraints,
        "post_parse_constraints_count": len(constraints),
        "documented_but_not_parsed": documented_not_parsed,
        "documented_but_not_parsed_count": len(documented_not_parsed),
        "in_sample_but_not_parsed": sample_not_parsed,
        "in_sample_but_not_parsed_count": len(sample_not_parsed),
        "note": "Every control-file tag read_control.f90's own select on trim(cName) "
                "accepts, in source order. `assigns_to` is the public_var.f90 variable "
                "(or popMetadat.f90 metadata field) the arm writes; `fortran_type` and "
                "`default_literal` come from that variable's own declaration in "
                "public_var.f90, and `requiredness` is derived from it mechanically: a "
                "variable initialised to one of public_var's missing-value sentinels "
                "(charMissing/realMissing/integerMissing) has no usable default and must "
                "be set. A key whose arm writes a metadata %varFile/%varName field has no "
                "public_var default of its own; its effective default is the value "
                "popMetadat.f90 sets (see catalogs/outputs.yaml and "
                "catalogs/network_inputs.yaml). `allowed_values` is present only for the "
                "variables the code actually constrains, and is read from the select "
                "block that constrains them. A tag NOT in this list is not merely "
                "ignored: read_control.f90's case-default arm aborts the run "
                "(`unrecognized_key_message`). `documented_but_not_parsed` and "
                "`in_sample_but_not_parsed` are the doc-vs-code and sample-vs-code "
                "disagreements this pass found; code wins, and "
                "curated/disagreements_overlay.yaml records each one re-checked at "
                "source. `count` counts `keys` only.",
    }


# --------------------------------------------------------------------------------------
# CATALOG b: routing_methods
# --------------------------------------------------------------------------------------

_METHOD_PARAM_RE = re.compile(
    r"^\s*integer\(i4b\)\s*,\s*parameter\s*,\s*public\s*::\s*(?P<name>\w+)\s*=\s*(?P<value>\d+)\s*$",
    re.IGNORECASE)


def _routing_method_ids(root):
    """The routing-method id constants, from public_var.f90's own `! routing methods`
    block (between nRouteMethods and the next section heading)."""
    lines = read_lines(root / PUBLIC_VAR)
    start, _ = find_block(lines, r"!\s*routing methods\s*$", r"^\s*!\s*-{5,}")
    ids = []
    for i in range(start + 1, len(lines)):
        if lines[i] is None:
            break
        code, comment = strip_comment(lines[i])
        if not code.strip():
            if comment and comment.strip().startswith("-"):
                break
            continue
        m = _METHOD_PARAM_RE.match(code)
        if not m:
            break
        ids.append({"constant": m.group("name"), "value": int(m.group("value")),
                    "comment": (comment or "").strip() or None, "line": i})
    return [d for d in ids if d["constant"] != "nRouteMethods"]


def _method_classes(root):
    """routing-method constant -> the routing class init_model_data.f90 allocates for it,
    and the module that class comes from (its own USE line in the same subroutine)."""
    lines = read_lines(root / INIT_MODEL)
    use_map = {}
    for i in range(1, len(lines)):
        if lines[i] is None:
            continue
        code, _ = strip_comment(lines[i])
        m = re.match(r"^\s*USE\s+(?P<mod>\w+)\s*,\s*ONLY\s*:\s*(?P<sym>\w+_rch)\s*$",
                     code.strip(), re.IGNORECASE)
        if m:
            use_map[m.group("sym")] = {"module": m.group("mod"), "line": i}
    blk = scan_select_case(lines, "select case (routeMethods(ix))")
    out = {}
    for c in blk["cases"]:
        const = c["labels"][0] if c["labels"] else None
        cls = None
        for j in range(c["line"], min(c["line"] + 3, len(lines))):
            if lines[j] is None:
                continue
            code, _ = strip_comment(lines[j])
            m = re.search(r"allocate\s*\(\s*(?P<cls>\w+_rch)\s*::", code)
            if m:
                cls = m.group("cls")
                out[const] = {"class": cls, "allocate_line": j,
                              "module": (use_map.get(cls) or {}).get("module"),
                              "use_line": (use_map.get(cls) or {}).get("line")}
                break
    return out


_MODULE_FILES = {
    "accum_runoff_module": f"{SRC}/accum_runoff.f90",
    "irf_route_module": f"{SRC}/irf_route.f90",
    "kwt_route_module": f"{SRC}/kwt_route.f90",
    "kw_route_module": f"{SRC}/kwe_route.f90",
    "mc_route_module": f"{SRC}/mc_route.f90",
    "dfw_route_module": f"{SRC}/dfw_route.f90",
}


def _module_file_map(root):
    """Confirm each routing module's file by reading the MODULE statement out of it,
    rather than trusting the name-to-file guess above."""
    out = {}
    for mod, rel in _MODULE_FILES.items():
        path = root / rel
        if not path.is_file():
            continue
        lines = read_lines(path)
        for i in range(1, min(len(lines), 10)):
            if lines[i] is None:
                continue
            m = re.match(r"^\s*MODULE\s+(\w+)\s*$", lines[i], re.IGNORECASE)
            if m and m.group(1) == mod:
                out[mod] = {"file": rel, "line": i}
                break
    return out


def _method_history_variables(root):
    """routing-method constant -> the ixRFLX history variables histVars_data.f90's own
    read_restart select assigns for it (discharge / volume / height / flood volume /
    inflow / solute), which is the code's own method-to-output-variable map."""
    lines = read_lines(root / HIST_VARS)
    blk = scan_select_case(lines, "select case(routeMethods(ixRoute))")
    out = {}
    for idx, c in enumerate(blk["cases"]):
        const = c["labels"][0] if c["labels"] else None
        end = (blk["cases"][idx + 1]["line"] if idx + 1 < len(blk["cases"])
               else (blk["default_line"] or c["line"] + 1))
        assigns = []
        for j in range(c["line"], end):
            if lines[j] is None:
                continue
            code, _ = strip_comment(lines[j])
            m = re.match(r"^\s*(?P<slot>ix\w+)\s*=\s*ixRFLX%(?P<var>\w+)\s*$", code.strip())
            if m:
                assigns.append({"role": m.group("slot"), "variable": m.group("var"),
                                "line": j})
        out[const] = assigns
    return out


_HIST_ROLE_LABEL = {
    "ixFlow": "discharge at reach outlet",
    "ixVol": "water volume in reach or lake",
    "ixWaterH": "water height from reach bottom",
    "ixFloodV": "water volume in floodplain",
    "ixInflow": "inflow from upstream reaches or lakes",
    "ixSoluteFlux": "routed solute mass flux",
    "ixSoluteMass": "routed solute mass",
}


def _rchprp_fields(root):
    """The field names of the reach-parameter derived type RCHPRP, read from its own
    declaration in dataTypes.f90."""
    dt = read_lines(root / DATA_TYPES)
    s, e = find_block(dt, r"type,\s*public\s*::\s*RCHPRP", r"end\s+type\s+RCHPRP")
    fields = {}
    for i in range(s + 1, e):
        if dt[i] is None:
            continue
        code, comment = strip_comment(dt[i])
        m = _RCHPRP_RE.match(code)
        if m:
            fields[m.group("name")] = {"comment": comment, "line": i}
    return fields


def _routing_parameter_uses(root):
    """Reach-parameter (RCHPRP) fields each routing module names textually, whether
    through the RPARAM_in array or through the dummy argument its own private routine
    binds it to -- matched against the type's actual field list, not a guess."""
    fields = _rchprp_fields(root)
    pat = re.compile(r"%\s*(" + "|".join(sorted(fields, key=len, reverse=True)) + r")\b")
    out = {}
    for mod, rel in _MODULE_FILES.items():
        path = root / rel
        if not path.is_file():
            continue
        lines = read_lines(path)
        seen = {}
        for i in range(1, len(lines)):
            if lines[i] is None:
                continue
            code, _ = strip_comment(lines[i])
            for m in pat.finditer(code):
                seen.setdefault(m.group(1), i)
        out[mod] = [{"parameter": k, "units_and_meaning": fields[k]["comment"],
                     "where": where(rel, v)} for k, v in sorted(seen.items())]
    return out


def cmd_routing_methods(root):
    ids = _routing_method_ids(root)
    classes = _method_classes(root)
    modfiles = _module_file_map(root)
    histmap = _method_history_variables(root)
    paruse = _routing_parameter_uses(root)
    initlines = read_lines(root / INIT_MODEL)

    methods = []
    for d in ids:
        const = d["constant"]
        cls = classes.get(const) or {}
        mod = cls.get("module")
        mf = modfiles.get(mod) or {}
        hist = histmap.get(const) or []
        payload = {
            "name": const,
            "route_opt_digit": str(d["value"]),
            "meaning": d["comment"],
            "implementing_class": cls.get("class"),
            "implementing_module": mod,
            "history_variables": [
                {"role": h["role"], "role_meaning": _HIST_ROLE_LABEL.get(h["role"]),
                 "variable": h["variable"], "where": where(HIST_VARS, h["line"])}
                for h in hist],
            "reach_parameters_used": paruse.get(mod, []),
        }
        if mf:
            payload["implemented_in"] = where(mf["file"], mf["line"])
        if cls.get("allocate_line"):
            payload["selected_at"] = where(INIT_MODEL, cls["allocate_line"])
        methods.append(fact(payload, PUBLIC_VAR, d["line"]))

    # route_opt is a digit string, split one digit per method by nr_utils char2int.
    lines = read_lines(root / READ_CONTROL)
    char2int_line = None
    for i in range(1, len(lines)):
        if lines[i] is not None and "char2int(trim(routOpt)" in squeeze(lines[i]):
            char2int_line = i
            break
    blk = scan_select_case(lines, "select case(routeMethods(iRoute))")

    # Lake routing is not a route_opt digit: it is a per-reach branch inside main_route.
    lake_lines = read_lines(root / LAKE_ROUTE)
    lake_pub = None
    for i in range(1, len(lake_lines)):
        if lake_lines[i] is not None and re.match(r"^\s*public::lake_route\s*$", lake_lines[i]):
            lake_pub = i
            break
    # lake_route.f90 has several selects on the same expression (a debug print, the
    # cold-start volume initialisation, and the outflow dispatch); the dispatch is the
    # one with the most branches, chosen by count rather than by source order.
    lake_models = max(scan_all_select_cases(lake_lines,
                                            "select case(NETOPO_in(segIndex)%LakeModelType)"),
                      key=lambda b: len(b["cases"]))
    lake_consts = {}
    for i in range(1, len(lake_lines)):
        if lake_lines[i] is None:
            continue
        code, _ = strip_comment(lake_lines[i])
        m = re.match(r"^\s*integer\(i4b\)\s*,\s*parameter\s*::\s*(?P<n>\w+)\s*=\s*(?P<v>\d+)\s*$",
                     code, re.IGNORECASE)
        if m:
            lake_consts[m.group("n")] = {"value": int(m.group("v")), "line": i}

    extras = [fact({
        "name": "lake_route",
        "route_opt_digit": None,
        "meaning": "per-reach lake/reservoir outflow, applied instead of channel routing "
                   "when the reach is flagged as a lake and <is_lake_sim> is true; it is "
                   "not selected by a <route_opt> digit",
        "implementing_module": "lake_route_module",
        "implemented_in": where(LAKE_ROUTE, lake_pub or 1),
        "lake_model_types": [
            {"constant": c["labels"][0] if c["labels"] else None,
             "lakeModelType_value": (lake_consts.get(c["labels"][0], {}).get("value")
                                     if c["labels"] else None),
             "declared_where": (where(LAKE_ROUTE, lake_consts[c["labels"][0]]["line"])
                                if c["labels"] and c["labels"][0] in lake_consts else None),
             "where": where(LAKE_ROUTE, c["line"])}
            for c in lake_models["cases"]],
        "lake_model_rejection_message": lake_models["default_message"],
    }, LAKE_ROUTE, lake_pub or 1)]

    return {
        "pack": PACK, "catalog": "routing_methods",
        "generator": "tools/extract_pack.py --pack mizuroute routing-methods",
        "generator_version": GENERATOR_VERSION, "scope": SCOPE,
        "entries_key": "methods", "entry_kind": "mizuRoute routing method",
        "count": len(methods),
        "methods": methods,
        "non_route_opt_methods": extras,
        "route_opt_grammar": fact({
            "control_key": "route_opt",
            "statement": "the value is a digit STRING, split into one routing method id "
                         "per digit by nr_utils char2int (invalid_value=0), so 135 turns "
                         "on three methods at once; each digit is then matched against "
                         "the routing-method id constants",
            "rejection_message": blk["default_message"],
        }, READ_CONTROL, char2int_line or blk["select_line"]),
        "note": "Every routing method the pinned code implements, keyed by the "
                "<route_opt> digit that selects it. `implementing_class` is the class "
                "init_model_data.f90 allocates into globalData's rch_routes container "
                "for that digit, and every class extends base_route_rch's deferred "
                "`route` binding (route/build/src/base_route.f90). `history_variables` "
                "is the code's own method-to-output-variable map, read from "
                "histVars_data.f90's select on routeMethods. `reach_parameters_used` "
                "lists only RPARAM fields the routing module itself names textually: a "
                "method that reaches its parameters through a called helper (e.g. the "
                "hydraulic-geometry routines) shows fewer here than it uses -- see "
                "catalogs/parameters.yaml. Lake routing and the tracer/data-assimilation "
                "paths are not <route_opt> digits and are listed under "
                "`non_route_opt_methods`. `count` counts `methods` only.",
    }


# --------------------------------------------------------------------------------------
# CATALOG c: network_inputs
# --------------------------------------------------------------------------------------

_PROMOTE_RE = re.compile(
    r"^\s*meta_(?P<struct>\w+)\s*\(\s*ix(?P<ix>\w+)%(?P<member>\w+)\s*\)\s*%varFile\s*=\s*"
    r"\.(?P<val>true|false)\.", re.IGNORECASE)


def _varfile_promotions(root):
    """Every `meta_X(ixY%member)%varFile = .true./.false.` in read_streamSeg.f90, with
    the innermost enclosing `if (...)` condition text -- the code's own statement of
    which river-network variables become required under which option."""
    lines = read_lines(root / READ_STREAMSEG)
    out = {}
    stack = []  # (indent, condition text, line)
    for i in range(1, len(lines)):
        if lines[i] is None:
            continue
        code, _ = strip_comment(lines[i])
        if not code.strip():
            continue
        indent = len(code) - len(code.lstrip())
        while stack and indent <= stack[-1][0]:
            stack.pop()
        m = re.match(r"^\s*if\s*\((?P<cond>.*)\)\s*then\s*$", code, re.IGNORECASE)
        if m:
            stack.append((indent, m.group("cond").strip(), i))
            continue
        mm = _PROMOTE_RE.match(code)
        if mm:
            key = (f"meta_{mm.group('struct')}", mm.group("member"))
            out.setdefault(key, []).append({
                "sets_varFile_to": mm.group("val").lower() == "true",
                "condition": " and ".join(c[1] for c in stack) or None,
                "where": where(READ_STREAMSEG, i),
            })
    return out


_REMAP_CASE_RE = re.compile(
    r"^\s*case\s*\(\s*(?P<n>\d+)\s*\)\s*;\s*call\s+get_nc\s*\(\s*fname\s*,\s*(?P<var>\w+)\s*,"
    r"\s*remap_data_in%(?P<field>\w+)\s*,\s*1\s*,\s*(?P<len>\w+)", re.IGNORECASE)


def cmd_network_inputs(root):
    vinfo = parse_var_info(root)
    lookup = parse_var_lookup(root)
    table, _, _ = parse_control_keys_table(root)
    promotions = _varfile_promotions(root)
    pv, _ = parse_public_var(root)

    rename_by_member = {}
    for e in table:
        mt = e.get("metadata_target")
        if mt and mt["field"] == "varName":
            rename_by_member[(mt["structure"], mt["member"])] = e

    struct_to_ilook = {
        "meta_HRU": "iLook_HRU", "meta_HRU2SEG": "iLook_HRU2SEG", "meta_SEG": "iLook_SEG",
        "meta_NTOPO": "iLook_NTOPO", "meta_PFAF": "iLook_PFAF",
    }

    variables = []
    for v in vinfo:
        key = (v["structure"], v["member"])
        ren = rename_by_member.get(key)
        il = lookup.get(struct_to_ilook.get(v["structure"], ""), {}).get(v["member"], {})
        proms = promotions.get(key, [])
        payload = {
            "name": v["default_varname"],
            "structure": v["structure"],
            "member": v["member"],
            "description": v["description"],
            "units": v["units"],
            "dimension": v["dimension"],
            "read_by_default": v["read_by_default"],
            "rename_key": (f"<{ren['key']}>" if ren else None),
            "rename_key_where": (where(READ_CONTROL, ren["line"]) if ren else None),
            "index_comment": il.get("comment"),
            "conditionally_required": [
                {"sets_read_to": p["sets_varFile_to"], "condition": p["condition"],
                 "where": p["where"]} for p in proms],
        }
        if il.get("line"):
            payload["index_where"] = where(VAR_LOOKUP, il["line"])
        variables.append(fact(payload, POP_METADAT, v["line"]))

    # Runoff/forcing input file conventions.
    runoff_keys = []
    for name in ("fname_qsim", "vname_qsim", "vname_evapo", "vname_precip", "vname_solute",
                 "vname_time", "vname_hruid", "dname_time", "dname_hruid", "dname_xlon",
                 "dname_ylat", "units_qsim", "units_cc", "dt_ro", "input_fillvalue",
                 "ro_time_units", "ro_calendar", "ro_time_stamp", "runoffMin"):
        d = pv.get(name)
        if not d:
            continue
        e = next((x for x in table if x["assigns_to"] == name), None)
        runoff_keys.append(fact({
            "variable": name,
            "control_key": (f"<{e['key']}>" if e else None),
            "meaning": d["declaration_comment"],
            "fortran_type": d["fortran_type"],
            "default_literal": d["default_literal"],
            "requiredness": _requiredness(d["default_literal"]),
        }, PUBLIC_VAR, d["line"]))

    rl = read_lines(root / READ_RUNOFF)
    runoff_facts = []
    for pat, statement in (
        (r"existAttr\s*=\s*check_attr\s*\(\s*fname\s*,\s*var_name\s*,\s*'_FillValue'\s*\)",
         "the forcing variable's own _FillValue attribute is used when present; when it "
         "is absent the control value <input_fillvalue> is used instead, and a warning "
         "is printed if that was left at realMissing"),
        (r"allocate\s*\(\s*sim\s*\(\s*nSpace\(2\)\s*,\s*nSpace\(1\)\s*\)",
         "a 2D (grid) forcing variable is held as sim2d(xlon, ylat): the array is "
         "allocated x-fastest from the y (dname_ylat) and x (dname_xlon) dimension "
         "lengths, so the NetCDF variable is read as (lon, lat, time)"),
        (r"if\s*\(abs\(0\._dp\s*-\s*sumWeights\)<verySmall\)",
         "when a simulation step spans several forcing steps the value is a "
         "weight-averaged mean over the overlapped forcing steps, fill-valued forcing "
         "steps are skipped, and the result is realMissing if every overlapped step was "
         "fill-valued"),
    ):
        for i in range(1, len(rl)):
            if rl[i] is None:
                continue
            if re.search(pat, rl[i]):
                runoff_facts.append(fact({"statement": statement}, READ_RUNOFF, i))
                break

    gl = read_lines(root / GET_BASIN_RUNOFF)
    for pat, statement in (
        (r"call\s+scale_forcing\s*\(\s*runoff_data,\s*scale_factor_runoff,\s*offset_value_runoff\)",
         "runoff is scaled and offset as scale*value+offset using <scale_factor_runoff> "
         "and <offset_value_runoff>; a scale left at realMissing behaves as 1.0 and an "
         "offset left at realMissing behaves as 0.0"),
        (r"call\s+scale_forcing\s*\(\s*runoff_data,\s*-1\._dp,\s*0\._dp\)",
         "<is_Ep_upward_negative> flips the sign of the evaporation input before "
         "<scale_factor_Ep>/<offset_value_Ep> are applied"),
        (r"runoff_data%basinRunoff\s*=\s*0\._dp",
         "a <scale_factor_runoff> of zero (with a zero or unset offset) suppresses the "
         "runoff read entirely and sets basin runoff to zero, rather than reading and "
         "multiplying by zero"),
    ):
        for i in range(1, len(gl)):
            if gl[i] is None:
                continue
            if re.search(pat, gl[i]):
                runoff_facts.append(fact({"statement": statement}, GET_BASIN_RUNOFF, i))
                break

    # Unit conversion of runoff to reach inflow.
    prl = read_lines(root / f"{SRC}/process_remap.f90")
    for i in range(1, len(prl)):
        if prl[i] is None:
            continue
        if "time_conv*length_conv" in squeeze(prl[i]):
            runoff_facts.append(fact({
                "statement": "the only place the runoff unit conversion is applied: "
                             "reach lateral inflow = sum over contributing HRUs of "
                             "hruWeight * basinRunoff * time_conv * length_conv, with "
                             "the two factors set from <units_qsim> in read_control.f90; "
                             "basinRunoff is therefore a depth per time in the units the "
                             "control file declares, and the reach inflow the routing "
                             "sees is in m3/s only after this line",
            }, f"{SRC}/process_remap.f90", i))
            break

    # Remapping file variables.
    rml = read_lines(root / READ_REMAP)
    remap_vars = []
    for i in range(1, len(rml)):
        if rml[i] is None:
            continue
        code, comment = strip_comment(rml[i])
        m = _REMAP_CASE_RE.match(code)
        if m:
            varname = m.group("var")
            d = pv.get(varname)
            e = next((x for x in table if x["assigns_to"] == varname), None)
            remap_vars.append(fact({
                "control_variable": varname,
                "control_key": (f"<{e['key']}>" if e else None),
                "default_name": (d or {}).get("default_literal", "").strip("'") or None,
                "meaning": (d or {}).get("declaration_comment"),
                "target_field": m.group("field"),
                "length_dimension": m.group("len"),
                "read_case_index": int(m.group("n")),
            }, READ_REMAP, i))
    remap_gate = None
    for i in range(1, len(rml)):
        if rml[i] is None:
            continue
        if "nSpatial(2)==integerMissing.and.iVar>=5" in squeeze(strip_comment(rml[i])[0]):
            remap_gate = fact({
                "statement": "the remapping file's i_index/j_index variables are read "
                             "only when the runoff input is a 2D grid, and qhruid only "
                             "when it is a 1D HRU vector; the gate is the runoff file's "
                             "own second spatial dimension, not a control key",
            }, READ_REMAP, i)
            break

    return {
        "pack": PACK, "catalog": "network_inputs",
        "generator": "tools/extract_pack.py --pack mizuroute network-inputs",
        "generator_version": GENERATOR_VERSION, "scope": SCOPE,
        "entries_key": "variables", "entry_kind": "mizuRoute river-network input variable",
        "count": len(variables),
        "variables": variables,
        "runoff_input_keys": runoff_keys,
        "runoff_input_keys_count": len(runoff_keys),
        "runoff_input_conventions": runoff_facts,
        "remap_variables": remap_vars,
        "remap_variables_count": len(remap_vars),
        "remap_gate": remap_gate,
        "note": "The river-network topology NetCDF variables popMetadat.f90 declares, "
                "one entry per metadata slot. `name` is the DEFAULT NetCDF variable name; "
                "`rename_key` is the control-file tag that overrides it. "
                "`read_by_default` is popMetadat.f90's own varFile flag, which is exactly "
                "the flag read_streamSeg.f90 tests before reading a variable, so it is "
                "the required/optional switch: true means the run reads it from the "
                "network file. `conditionally_required` records every place "
                "read_streamSeg.f90's mod_meta_varFile raises (or lowers) that flag at "
                "run time, with the enclosing condition verbatim -- that is how the lake "
                "parameter families and the hydraulic-geometry variables become required. "
                "A variable whose flag is false is never read and is instead computed (see "
                "catalogs/parameters.yaml) or left unused. `dimension` is the ixDims "
                "member the metadata names (hru, seg, upHRU, upSeg, upAll, uh, pfaf). "
                "`count` counts `variables` only; the runoff and remapping lists are "
                "separate and counted separately.",
    }


# --------------------------------------------------------------------------------------
# CATALOG d: outputs
# --------------------------------------------------------------------------------------

def _hist_buffer_behaviour(root):
    """For each histVars field: whether aggregate() accumulates or overwrites it, and
    whether finalize() divides by the sample count. This, not a comment, is what makes a
    history variable an interval mean or an end-of-interval snapshot."""
    lines = read_lines(root / HIST_VARS)
    agg_s, agg_e = find_block(lines, r"SUBROUTINE\s+aggregate\s*\(", r"END\s+SUBROUTINE\s+aggregate")
    fin_s, fin_e = find_block(lines, r"SUBROUTINE\s+finalize\s*\(", r"END\s+SUBROUTINE\s+finalize")
    ref_s, ref_e = find_block(lines, r"SUBROUTINE\s+refresh\s*\(", r"END\s+SUBROUTINE\s+refresh")
    out = {}
    for i in range(agg_s, agg_e + 1):
        if lines[i] is None:
            continue
        code, _ = strip_comment(lines[i])
        m = re.match(r"^\s*this%(?P<f>\w+)\s*\([^)]*\)\s*=\s*(?P<rhs>.+)$", code)
        if not m:
            continue
        f, rhs = m.group("f"), squeeze(m.group("rhs"))
        rec = out.setdefault(f, {})
        rec["aggregate_line"] = i
        rec["accumulates"] = rhs.startswith(f"this%{f}(")
        rec["aggregate_rhs"] = m.group("rhs").strip()
    for i in range(fin_s, fin_e + 1):
        if lines[i] is None:
            continue
        code, _ = strip_comment(lines[i])
        m = re.match(r"^\s*this%(?P<f>\w+)\s*=\s*(?P<rhs>.+)$", code)
        if not m:
            continue
        f = m.group("f")
        rec = out.setdefault(f, {})
        rec["finalize_line"] = i
        rec["divided_by_nt"] = "real(this%nt" in squeeze(m.group("rhs"))
        rec["finalize_rhs"] = m.group("rhs").strip()
    for i in range(ref_s, ref_e + 1):
        if lines[i] is None:
            continue
        code, _ = strip_comment(lines[i])
        m = re.search(r"this%(?P<f>\w+)\s*=\s*0\._dp", code)
        if m:
            out.setdefault(m.group("f"), {})["reset_line"] = i
    return out


def _kind_of(behaviour):
    """Closed vocabulary for a mizuRoute history variable's time meaning, derived only
    from the accumulate/divide pattern the code actually uses."""
    if not behaviour:
        return "undetermined", "no aggregate/finalize handling found for this buffer"
    acc = behaviour.get("accumulates")
    div = behaviour.get("divided_by_nt")
    if acc and div:
        return ("interval_mean",
                "accumulated every simulation step in aggregate() and divided by the "
                "sample count nt in finalize(), so the written value is the mean over "
                "the output interval")
    if acc and not div:
        return ("interval_sum",
                "accumulated every simulation step in aggregate() and NOT divided by the "
                "sample count in finalize()")
    if not acc and not div:
        return ("instantaneous_end_of_interval",
                "overwritten (not accumulated) at every simulation step in aggregate() "
                "and left unchanged by finalize(), so the written value is the value at "
                "the LAST simulation step of the output interval, not a mean over it")
    return ("undetermined",
            "overwritten in aggregate() but divided by the sample count in finalize()")


_RFLX_BUFFER_DIRECT = {
    "basRunoff": "basRunoff", "instRunoff": "instRunoff", "dlayRunoff": "dlayRunoff",
}
_ROLE_BUFFER = {
    "ixFlow": "discharge", "ixVol": "volume", "ixWaterH": "waterHeight",
    "ixFloodV": "floodVolume", "ixInflow": "inflow",
    "ixSoluteFlux": "solute_flux", "ixSoluteMass": "solute_mass",
}


def cmd_outputs(root):
    meta = parse_init_meta(root)
    lookup = parse_var_lookup(root)
    table, _, _ = parse_control_keys_table(root)
    behaviour = _hist_buffer_behaviour(root)
    histmap = _method_history_variables(root)

    member_to_buffer = dict(_RFLX_BUFFER_DIRECT)
    member_to_method = {}
    for const, assigns in histmap.items():
        for a in assigns:
            member_to_buffer.setdefault(a["variable"], _ROLE_BUFFER.get(a["role"]))
            member_to_method.setdefault(a["variable"], []).append(const)

    switch_by_member = {}
    for e in table:
        mt = e.get("metadata_target")
        if mt and mt["field"] == "varFile" and mt["structure"] in ("meta_rflx", "meta_hflx"):
            switch_by_member.setdefault(mt["member"], []).append(e)

    # read_control.f90's post-loop forcing of these switches (floodplain off, method off,
    # outputInflow on, tracer off): the code's own statement of when a switch is overridden.
    rc = read_lines(root / READ_CONTROL)
    overrides = {}
    stack = []
    for i in range(1, len(rc)):
        if rc[i] is None:
            continue
        code, _ = strip_comment(rc[i])
        if not code.strip():
            continue
        indent = len(code) - len(code.lstrip())
        while stack and indent <= stack[-1][0]:
            stack.pop()
        m = re.match(r"^\s*if\s*\((?P<cond>.*)\)\s*then\s*$", code, re.IGNORECASE)
        if m:
            stack.append((indent, m.group("cond").strip(), i))
            continue
        m = re.match(r"^\s*case\s*\((?P<c>\w+)\)\s*$", code)
        if m:
            stack = [(indent, f"routing method {m.group('c')} selected/not selected", i)]
            continue
        mm = re.match(r"^\s*meta_rflx\s*\(\s*ixRFLX%(?P<member>\w+)\s*\)\s*%varFile\s*=\s*"
                      r"\.(?P<val>true|false)\.", code, re.IGNORECASE)
        if mm:
            overrides.setdefault(mm.group("member"), []).append({
                "forced_to": mm.group("val").lower() == "true",
                "condition": " and ".join(c[1] for c in stack) or None,
                "where": where(READ_CONTROL, i),
            })

    variables = []
    for m in meta:
        if m["structure"] not in ("meta_rflx", "meta_hflx"):
            continue
        member = m["member"]
        buf = member_to_buffer.get(member)
        beh = behaviour.get(buf) if buf else None
        kind, kind_evidence = _kind_of(beh)
        ilook = "iLook_RFLX" if m["structure"] == "meta_rflx" else "iLook_HFLX"
        il = lookup.get(ilook, {}).get(member, {})
        switches = switch_by_member.get(member, [])
        payload = {
            "name": m["name"],
            "member": member,
            "structure": m["structure"],
            "long_name": m["long_name"],
            "units": m["units"],
            "netcdf_type": m["netcdf_type"],
            "dimensions": m["dimensions"],
            "default_write": m["default_write"],
            "control_keys": [f"<{e['key']}>" for e in switches],
            "control_keys_where": [where(READ_CONTROL, e["line"]) for e in switches],
            "history_buffer": buf,
            "kind": kind,
            "kind_evidence": kind_evidence,
            "produced_by_methods": sorted(set(member_to_method.get(member, []))),
            "index_comment": il.get("comment"),
            "forced_by_code": [
                {"forced_to": o["forced_to"], "condition": o["condition"], "where": o["where"]}
                for o in overrides.get(member, [])],
        }
        if beh:
            for k, lk in (("aggregate_line", "accumulated_where"),
                          ("finalize_line", "finalized_where"),
                          ("reset_line", "reset_where")):
                if beh.get(k):
                    payload[lk] = where(HIST_VARS, beh[k])
            payload["aggregate_expression"] = beh.get("aggregate_rhs")
        if il.get("line"):
            payload["index_where"] = where(VAR_LOOKUP, il["line"])
        variables.append(fact(payload, POP_METADAT, m["line"]))

    # File naming and time stamping.
    ws = read_lines(root / WRITE_SIMOUT)
    naming = []
    for i in range(1, len(ws)):
        if ws[i] is None:
            continue
        code, _ = strip_comment(ws[i])
        m = re.search(r"write\((?P<v>hfileout(?:_gage)?)\s*,\s*'\(a\)'\)\s*(?P<expr>.+)$", code)
        if m:
            rm = "cesm-coupling" if ".mizuroute.h" in code else "standalone"
            naming.append(fact({
                "target": m.group("v"),
                "pattern": re.sub(r"\s+", " ", m.group("expr").strip()),
            }, WRITE_SIMOUT, i, runmode=rm))
    stamp_block = scan_select_case(ws, "select case(trim(newFileFrequency))")
    stamps = [fact({"newFileFrequency": c["labels"],
                    "time_string_construction": c["action"] or "see the following lines"},
                   WRITE_SIMOUT, c["line"]) for c in stamp_block["cases"]]
    timing = []
    for pat, statement in (
        (r"timeVar_local\s*=\s*timeVar/sec2tunit",
         "the time variable written to history is the simulation time converted to the "
         "history file's own time unit by sec2tunit"),
        (r"if\s*\(hVars%nt\s*==\s*alarmFrequency\)",
         "a numeric <outputFrequency> counts SIMULATION STEPS accumulated in the buffer, "
         "not elapsed time: the write fires when the buffer has nt == outputFrequency "
         "samples"),
        (r"histTimeStamp_offset\s*=\s*\(hVars%timeVar\(2\)\s*-\s*hVars%timeVar\(1\)\)",
         "in cesm-coupling mode the history time stamp offset is overwritten with half "
         "the width of the accumulation window, so the stamp is the window midpoint; in "
         "standalone mode the control value <histTimeStamp_offset> is used as given"),
        (r"call\s+hVars%refresh\(\)",
         "the history buffers are zeroed and the sample count reset only after a write, "
         "so the interval a record covers is the span since the previous record"),
    ):
        for i in range(1, len(ws)):
            if ws[i] is None:
                continue
            if re.search(pat, ws[i]):
                rm = "cesm-coupling" if "cesm" in statement else "both"
                timing.append(fact({"statement": statement}, WRITE_SIMOUT, i, runmode=rm))
                break

    return {
        "pack": PACK, "catalog": "outputs",
        "generator": "tools/extract_pack.py --pack mizuroute outputs",
        "generator_version": GENERATOR_VERSION, "scope": SCOPE,
        "entries_key": "variables", "entry_kind": "mizuRoute history output variable",
        "count": len(variables),
        "variables": variables,
        "file_naming": naming,
        "file_time_stamp": stamps,
        "output_timing": timing,
        "note": "Every history-file variable popMetadat.f90 declares, reach fluxes "
                "(meta_rflx, dimension seg x time) and HRU fluxes (meta_hflx, hru x time). "
                "`kind` is NOT taken from any comment: it is derived from what "
                "histVars_data.f90 actually does to the variable's buffer -- accumulated "
                "in aggregate() and divided by the sample count in finalize() gives "
                "interval_mean; overwritten in aggregate() and untouched by finalize() "
                "gives instantaneous_end_of_interval. `kind_evidence` states which of the "
                "two it was, and `accumulated_where`/`finalized_where`/`reset_where` cite "
                "the lines. `default_write` is popMetadat.f90's own writeOut flag; "
                "`control_keys` is the control tag(s) that set it, and `forced_by_code` is "
                "every place read_control.f90 overrides it after the control file was read "
                "(a routing method not selected, floodplain off, outputInflow on, tracer "
                "off) -- a switch set to true in the control file does NOT guarantee the "
                "variable is written. A variable with no `control_keys` entry cannot be "
                "switched on from the control file at all at this commit. `count` counts "
                "`variables` only.",
    }


# --------------------------------------------------------------------------------------
# CATALOG e: restart
# --------------------------------------------------------------------------------------

_RESTART_STRUCTS = ("meta_kwt", "meta_kw", "meta_dw", "meta_mc", "meta_irf",
                    "meta_irf_bas", "meta_bas_solute", "meta_basinQ", "meta_solute")
_RESTART_OWNER = {
    "meta_kwt": "kinematicWaveTracking", "meta_kw": "kinematicWave",
    "meta_dw": "diffusiveWave", "meta_mc": "muskingumCunge",
    "meta_irf": "impulseResponseFunc",
    "meta_irf_bas": "basin (hillslope) IRF routing, gated by <doesBasinRoute>",
    "meta_bas_solute": "basin (hillslope) tracer routing, gated by <tracer>",
    "meta_basinQ": "all routing methods (reach inflow from the local basin)",
    "meta_solute": "tracer transport, gated by <tracer>",
}


def cmd_restart(root):
    meta = parse_init_meta(root)
    lookup = parse_var_lookup(root)
    ilook_for = {"meta_kwt": "iLook_KWT", "meta_kw": "iLook_KW", "meta_dw": "iLook_DW",
                 "meta_mc": "iLook_MC", "meta_irf": "iLook_IRF",
                 "meta_irf_bas": "iLook_IRFbas", "meta_bas_solute": "iLook_basTracer",
                 "meta_basinQ": "iLook_basinQ", "meta_solute": "iLook_tracer"}
    variables = []
    for m in meta:
        if m["structure"] not in _RESTART_STRUCTS:
            continue
        il = lookup.get(ilook_for.get(m["structure"], ""), {}).get(m["member"], {})
        payload = {
            "name": m["name"],
            "member": m["member"],
            "structure": m["structure"],
            "belongs_to": _RESTART_OWNER.get(m["structure"]),
            "long_name": m["long_name"],
            "units": m["units"],
            "netcdf_type": m["netcdf_type"],
            "dimensions": m["dimensions"],
            "written_by_default": m["default_write"],
            "index_comment": il.get("comment"),
        }
        if il.get("line"):
            payload["index_where"] = where(VAR_LOOKUP, il["line"])
        variables.append(fact(payload, POP_METADAT, m["line"]))

    wr = read_lines(root / WRITE_RESTART)
    alarm = scan_select_case(wr, "select case(lower(trim(restart_write)))")
    frequency = [fact({"restart_write": c["labels"], "fires_when": c["action"]},
                      WRITE_RESTART, c["line"]) for c in alarm["cases"]]
    naming = []
    for i in range(1, len(wr)):
        if wr[i] is None:
            continue
        code, _ = strip_comment(wr[i])
        m = re.search(r"write\(fname,\s*fmtYMDS\)\s*(?P<expr>.+)$", code)
        if m:
            rm = "cesm-coupling" if "mizuroute.r." in code else "standalone"
            naming.append(fact({"pattern": re.sub(r"\s+", " ", m.group("expr").strip())},
                               WRITE_RESTART, i, runmode=rm))
    timing = []
    for pat, statement in (
        (r"call\s+restart_fname\(rfileout,\s*nextTimeStep",
         "the restart file is stamped with the NEXT simulation time step, not the "
         "current one, so a restart written at the end of a step carries the time of the "
         "step it resumes at"),
        (r"dropDatetime\s*=\s*datetime\(dropDatetime%year\(\),\s*dropDatetime%month\(\),\s*restart_day",
         "<restart_day> replaces the day of the drop-off datetime, and is clamped down "
         "to the last day of the month when the month is shorter"),
    ):
        for i in range(1, len(wr)):
            if wr[i] is None:
                continue
            if re.search(pat, squeeze(wr[i]) if "restart_fname" not in pat else wr[i]):
                timing.append(fact({"statement": statement}, WRITE_RESTART, i))
                break

    return {
        "pack": PACK, "catalog": "restart",
        "generator": "tools/extract_pack.py --pack mizuroute restart",
        "generator_version": GENERATOR_VERSION, "scope": SCOPE,
        "entries_key": "variables", "entry_kind": "mizuRoute restart variable",
        "count": len(variables),
        "variables": variables,
        "write_frequency": frequency,
        "rejection_message": alarm["default_message"],
        "file_naming": naming,
        "restart_timing": timing,
        "note": "Every restart-file variable popMetadat.f90 declares, grouped by the "
                "routing method or component that owns it (`belongs_to`). "
                "`written_by_default` is the metadata's own writeOut flag; a qerror_* "
                "variable is declared false and is written only when the "
                "streamflow-modification (data-assimilation) path is active. Restart "
                "variables have no per-variable control key: the whole file is gated by "
                "<restart_write> (see `write_frequency`, whose keywords are matched "
                "case-insensitively) and <restart_date>/<restart_month>/<restart_day>/"
                "<restart_hour>. Dimension names are the ixStateDims members "
                "(seg, hru, time, tbound, wave, mol_kw, mol_mc, mol_dw, tdh_irf, tdh, "
                "nchars, hist_fil). `count` counts `variables` only.",
    }


# --------------------------------------------------------------------------------------
# CATALOG f: parameters
# --------------------------------------------------------------------------------------

_NAMELIST_RE = re.compile(r"^\s*namelist\s*/(?P<group>\w+)/(?P<vars>[\w,\s]+)", re.IGNORECASE)
_GLOBAL_DECL_RE = re.compile(
    r"^\s*(?P<type>(?:real|integer|logical|character)\s*\([^)]*\))\s*,"
    r"(?P<attrs>[^:]*?)::\s*(?P<name>\w+)\s*(?:=\s*(?P<default>[^!]+?))?\s*$",
    re.IGNORECASE)
_RCHPRP_RE = re.compile(
    r"^\s*(?P<type>(?:real|integer|logical)\s*\([^)]*\))\s*::\s*(?P<name>\w+)\s*$",
    re.IGNORECASE)


def _global_decls(root):
    lines = read_lines(root / GLOBAL_DATA)
    out = {}
    for i in range(1, len(lines)):
        if lines[i] is None:
            continue
        code, comment = strip_comment(lines[i])
        m = _GLOBAL_DECL_RE.match(code)
        if m and "public" in m.group("attrs").lower():
            out[m.group("name")] = {
                "fortran_type": re.sub(r"\s+", "", m.group("type")),
                "default_literal": (m.group("default") or "").strip() or None,
                "comment": comment, "line": i}
    return out


def cmd_parameters(root):
    rp = read_lines(root / READ_PARAM)
    gdecl = _global_decls(root)
    groups = []
    for i in range(1, len(rp)):
        if rp[i] is None:
            continue
        code, comment = strip_comment(rp[i])
        m = _NAMELIST_RE.match(code)
        if not m:
            continue
        members = []
        for v in [x.strip() for x in m.group("vars").split(",") if x.strip()]:
            g = gdecl.get(v, {})
            members.append(fact({
                "parameter": v,
                "fortran_type": g.get("fortran_type"),
                "default_literal": g.get("default_literal"),
                "meaning": g.get("comment"),
                "requiredness": ("must_be_set_in_namelist" if g.get("default_literal") is None
                                 else "optional_has_default"),
                "declared_where": where(GLOBAL_DATA, g["line"]) if g.get("line") else None,
            }, GLOBAL_DATA, g.get("line") or i))
        groups.append(fact({
            "group": m.group("group"),
            "purpose": comment,
            "parameters": members,
            "parameters_count": len(members),
        }, READ_PARAM, i))

    # Spatially constant parameters that are NOT in any namelist group but are still
    # globalData routing parameters with their own defaults.
    namelist_members = {p["parameter"] for g in groups for p in g["parameters"]}
    extra = []
    for name in ("dscale", "floodplainSlope", "high_depth"):
        g = gdecl.get(name)
        if g and name not in namelist_members:
            extra.append(fact({
                "parameter": name,
                "fortran_type": g["fortran_type"],
                "default_literal": g["default_literal"],
                "meaning": g["comment"],
                "requiredness": "compiled_in_no_control_key",
            }, GLOBAL_DATA, g["line"]))

    # Reach parameter structure (RCHPRP) fields.
    dt = read_lines(root / DATA_TYPES)
    s, e = find_block(dt, r"type,\s*public\s*::\s*RCHPRP", r"end\s+type\s+RCHPRP")
    reach = []
    for i in range(s + 1, e):
        if dt[i] is None:
            continue
        code, comment = strip_comment(dt[i])
        m = _RCHPRP_RE.match(code)
        if m:
            reach.append(fact({
                "field": m.group("name"),
                "fortran_type": re.sub(r"\s+", "", m.group("type")),
                "meaning": comment,
            }, DATA_TYPES, i))

    # How the reach parameters are filled: either copied from the network file or derived.
    pn = read_lines(root / PROCESS_NTOPO)
    derivations = []
    for i in range(1, len(pn)):
        if pn[i] is None:
            continue
        code, comment = strip_comment(pn[i])
        m = re.match(r"^\s*structSEG\(iSeg\)%var\(ixSEG%(?P<member>\w+)\)%dat\(1\)\s*=\s*"
                     r"(?P<expr>.+?)\s*$", code)
        if m:
            derivations.append(fact({
                "network_variable": m.group("member"),
                "computed_as": re.sub(r"\s+", " ", m.group("expr").strip()),
                "meaning": comment,
            }, PROCESS_NTOPO, i))
            continue
        m = re.match(r"^\s*RPARAM_in\(iSeg\)%(?P<f>\w+)\s*=\s*(?P<expr>.+?)\s*$", code)
        if m:
            derivations.append(fact({
                "reach_parameter": m.group("f"),
                "assigned_from": re.sub(r"\s+", " ", m.group("expr").strip()),
                "meaning": comment,
            }, PROCESS_NTOPO, i))

    # Basin and channel unit hydrographs.
    pp = read_lines(root / PROCESS_PARAM)
    uh = []
    for pat, statement in (
        (r"cumprob\s*=\s*gammp\(fshape,\s*X_VALUE\)",
         "the basin (hillslope) unit hydrograph is a two-parameter gamma distribution "
         "with shape fshape and time scale tscale, evaluated at multiples of the "
         "simulation time step; the number of bins is chosen so the cumulative "
         "probability lands between 0.99 and 0.999"),
        (r"FRAC_FUTURE\(:\)\s*=\s*FRAC_FUTURE\(:\)\s*/\s*SUM\(FRAC_FUTURE\(:\)\)",
         "the basin unit-hydrograph ordinates are renormalised to sum to exactly 1, so "
         "truncating the histogram does not lose water"),
        (r"H\s*=\s*1\.0_dp/\(2\.0_dp\*sqrt\(pi\*diff\*sec\)\)",
         "the channel IRF unit hydrograph is the Saint-Venant/Lohmann (1996) solution "
         "with celerity velo [m/s] and diffusivity diff [m2/s], built on a fixed 1-hour "
         "internal step (dTUH) over at most 240 hours and then aggregated to the "
         "simulation time step"),
    ):
        for i in range(1, len(pp)):
            if pp[i] is None:
                continue
            if re.search(pat, squeeze(pp[i]) if "FRAC_FUTURE" in pat else pp[i]):
                uh.append(fact({"statement": statement}, PROCESS_PARAM, i))
                break

    # One flat, name-keyed list so every parameter -- namelist, compiled-in, or a field
    # of the per-reach parameter structure -- answers a single-name lookup.
    parameters = []
    for g in groups:
        for m in g["parameters"]:
            e = dict(m)
            e["name"] = e.pop("parameter")
            e["parameter_kind"] = "spatially_constant_namelist_parameter"
            e["namelist_group"] = g["group"]
            parameters.append(e)
    for m in extra:
        e = dict(m)
        e["name"] = e.pop("parameter")
        e["parameter_kind"] = "compiled_in_routing_parameter"
        e["namelist_group"] = None
        parameters.append(e)
    for m in reach:
        e = dict(m)
        e["name"] = e.pop("field")
        e["parameter_kind"] = "per_reach_parameter_structure_field"
        e["namelist_group"] = None
        parameters.append(e)

    return {
        "pack": PACK, "catalog": "parameters",
        "generator": "tools/extract_pack.py --pack mizuroute parameters",
        "generator_version": GENERATOR_VERSION, "scope": SCOPE,
        "entries_key": "parameters", "entry_kind": "mizuRoute parameter",
        "count": len(parameters),
        "parameters": parameters,
        "namelist_groups": groups,
        "namelist_groups_count": len(groups),
        "reach_parameter_derivations": derivations,
        "reach_parameter_derivations_count": len(derivations),
        "unit_hydrographs": uh,
        "note": "The spatially constant parameters read from the namelist named by "
                "<param_nml> (read_param.f90 reads all three groups unconditionally, so "
                "the namelist must contain HSLOPE, IRF_UH and KWT even for a run that "
                "uses only one of them), plus the per-reach parameter structure RCHPRP "
                "and how each of its fields is filled. A namelist parameter has NO "
                "compiled-in default: fshape, tscale, velo, diff, mann_n and wscale are "
                "declared in globalData.f90 without an initialiser, so their value comes "
                "only from the namelist. `compiled_in_parameters` are the routing "
                "parameters that do have a compiled default and no control key or "
                "namelist entry at all. `reach_parameter_derivations` are the "
                "process_ntopo.f90 lines that fill a reach parameter, including the "
                "hydraulic-geometry relations used when the network file does not supply "
                "width/depth/Manning n (see catalogs/network_inputs.yaml's "
                "`conditionally_required`). `parameters` is the flat, name-keyed list of "
                "all three parameter kinds (`parameter_kind`); `namelist_groups` is the "
                "same namelist parameters grouped as read_param.f90 reads them. `count` "
                "counts `parameters` only.",
    }


# --------------------------------------------------------------------------------------
# CATALOG g: constants (and the unit/time conventions)
# --------------------------------------------------------------------------------------

def cmd_constants(root):
    pv, order = parse_public_var(root)
    allowed = parse_allowed_values(root)
    constants = []
    for name in order:
        d = pv[name]
        if not d["is_parameter"]:
            continue
        constants.append(fact({
            "name": name,
            "fortran_type": d["fortran_type"],
            "value_literal": d["default_literal"],
            "meaning": d["declaration_comment"],
            "section": d["section"],
        }, PUBLIC_VAR, d["line"]))

    conversions = []
    for key in ("units_qsim_length", "units_qsim_time", "units_cc_mass", "units_cc_time"):
        a = allowed.get(key)
        if not a:
            continue
        conversions.append(fact({
            "quantity": key,
            "note": a["note"],
            "factors": [{"accepted_units": v["values"], "sets": v["action"],
                         "where": v["where"]} for v in a["values"]],
            "rejection_message": a["rejection_message"],
        }, a["where"]["file"], a["where"]["line"]))

    rc = read_lines(root / READ_CONTROL)
    time_facts = []
    for needle, statement, runmode in (
        ("if(dt>86400._dp)then",
         "the simulation time step <dt_qsim> must be at most 86400 s (one day)", "both"),
        ("if(mod(86400._dp,dt)>0._dp)then",
         "86400 s must be an exact multiple of <dt_qsim>", "both"),
        ("if(mod(86400._dp,real(nOutFreq,kind=dp)*dt)>0._dp)then",
         "when <outputFrequency> is numeric, 86400 s must be an exact multiple of "
         "<outputFrequency> x <dt_qsim>", "both"),
        ("calendar used for simulation and history output is the same as runoff input",
         "the calendar used for the simulation and for the history output is the "
         "calendar of the runoff input; a <ro_calendar> given in the control file is "
         "overwritten by the one read from the runoff file", "standalone"),
        ("time_unit for history files will be the same as runoff input",
         "the history file time unit defaults to the runoff input's time unit; "
         "<time_units> overrides it for the history files only", "standalone"),
    ):
        target = squeeze(needle)
        for i in range(1, len(rc)):
            if rc[i] is None:
                continue
            if target in squeeze(rc[i]):
                time_facts.append(fact({"statement": statement}, READ_CONTROL, i,
                                        runmode=runmode))
                break

    # Calendars the datetime class accepts.
    dtl = read_lines(root / f"{SRC}/datetime_data.f90")
    cal = None
    for i in range(1, len(dtl)):
        if dtl[i] is None:
            continue
        code, _ = strip_comment(dtl[i])
        if re.search(r"select\s+case\s*\(\s*trim\s*\(.*calendar.*\)\s*\)", code, re.IGNORECASE):
            blk = scan_select_case(dtl, code.strip(), start_at=i)
            cal = fact({
                "accepted_calendars": [c["labels"] for c in blk["cases"]],
                "rejection_message": blk["default_message"],
            }, f"{SRC}/datetime_data.f90", blk["select_line"])
            break

    return {
        "pack": PACK, "catalog": "constants",
        "generator": "tools/extract_pack.py --pack mizuroute constants",
        "generator_version": GENERATOR_VERSION, "scope": SCOPE,
        "entries_key": "constants", "entry_kind": "mizuRoute internal constant",
        "count": len(constants),
        "constants": constants,
        "unit_conversions": conversions,
        "time_step_and_calendar": time_facts,
        "calendar_support": cal,
        "note": "Every compile-time constant public_var.f90 declares as "
                "`parameter, public`, with its own declaration comment as the meaning and "
                "its `section` from the nearest heading comment above it. "
                "`unit_conversions` is the complete set of runoff and solute unit strings "
                "read_control.f90 accepts and the factor each one sets; the factors are "
                "applied once, in process_remap.f90's reach-inflow sum (see "
                "catalogs/network_inputs.yaml), converting depth-per-time to m3/s. "
                "`count` counts `constants` only.",
    }


# --------------------------------------------------------------------------------------
# CATALOG h: parallelism (what is distributed, what is not)
# --------------------------------------------------------------------------------------

def _first_match(lines, pattern, rel, statement, runmode="both"):
    for i in range(1, len(lines)):
        if lines[i] is None:
            continue
        if re.search(pattern, lines[i]):
            return fact({"statement": statement}, rel, i, runmode=runmode)
    return None


def cmd_parallelism(root):
    dd = read_lines(root / DOMAIN_DECOMP)
    mp = read_lines(root / MPI_PROCESS)
    pv, _ = parse_public_var(root)
    gd = _global_decls(root)
    facts = []
    for lines, rel, pattern, statement in (
        (dd, DOMAIN_DECOMP, r"SUBROUTINE\s+mpi_domain_decomposition\s*\(",
         "the MPI decomposition splits the network into a mainstem held by the root "
         "process and tributary sub-basins distributed across the other processes"),
        (dd, DOMAIN_DECOMP, r"maxSegs\s*=\s*nSeg/nDivs",
         "the tributary-size threshold used to cut the network into domains is the "
         "reach count divided by the number of divisions, computed at run time -- not "
         "public_var's compile-time maxSegs, which is the OpenMP threshold"),
        (dd, DOMAIN_DECOMP, r"if\s*\(nUpSeg\s*>\s*maxSegs\)\s*majorMainstem\(iSeg\)\s*=\s*\.true\.",
         "a reach with more upstream reaches than the threshold is marked mainstem; "
         "everything else belongs to a tributary domain"),
        (dd, DOMAIN_DECOMP, r"SUBROUTINE\s+omp_domain_decomposition\s*\(",
         "a second, independent OpenMP decomposition runs inside each MPI domain; it is "
         "selected by a `method` argument, not by a control key"),
        (dd, DOMAIN_DECOMP, r"USE\s+pfafstetter_module",
         "the decomposition uses Pfafstetter codes to find tributary outlets, so a "
         "network without a usable pfafCode variable falls back on the other "
         "decomposition path"),
        (mp, MPI_PROCESS, r"SUBROUTINE\s+mpi_route\s*\(",
         "routing itself is distributed: each process routes its own tributary reaches, "
         "then the tributary outlet flows are gathered and the root process routes the "
         "mainstem serially"),
    ):
        f = _first_match(lines, pattern, rel, statement)
        if f:
            facts.append(f)

    limits = []
    for name in ("maxSegs", "maxLevel", "MAXQPAR", "root", "maxPfafLen", "pfafMissing"):
        d = pv.get(name)
        if d:
            limits.append(fact({
                "name": name, "value_literal": d["default_literal"],
                "meaning": d["declaration_comment"],
                "is_compile_time_parameter": d["is_parameter"],
            }, PUBLIC_VAR, d["line"]))
    for name in ("pio_numiotasks", "pio_rearranger", "pio_root", "pio_stride"):
        g = gd.get(name)
        if g:
            limits.append(fact({
                "name": name, "value_literal": g["default_literal"],
                "meaning": g["comment"], "is_compile_time_parameter": False,
            }, GLOBAL_DATA, g["line"]))

    return {
        "pack": PACK, "catalog": "parallelism",
        "generator": "tools/extract_pack.py --pack mizuroute parallelism",
        "generator_version": GENERATOR_VERSION, "scope": SCOPE,
        "entries_key": "facts", "entry_kind": "mizuRoute parallelism fact",
        "count": len(facts),
        "facts": facts,
        "limits_and_settings": limits,
        "limits_and_settings_count": len(limits),
        "note": "What the pinned code parallelises and what it does not, as facts with "
                "citations rather than as advice. The decomposition is two-level: an MPI "
                "split into a root-held mainstem plus distributed tributaries, and an "
                "OpenMP split inside each. Of the settings listed, only <maxPfafLen> and "
                "<pfafMissing> are control keys; maxSegs, maxLevel, MAXQPAR and root are "
                "compile-time parameters, and the pio_* values are globalData defaults "
                "with no control key at this commit (<pio_netcdf_format> and "
                "<pio_netcdf_type> are the only PIO control keys). `count` counts `facts` "
                "only.",
    }


# --------------------------------------------------------------------------------------
# CATALOG i: build
# --------------------------------------------------------------------------------------

def cmd_build(root):
    lines = read_lines(root / MAKEFILE)
    facts = []
    required = []
    for i in range(1, len(lines)):
        if lines[i] is None:
            continue
        m = re.match(r"^\s*\$\(error\s+(?P<msg>[^)]*)\)", lines[i])
        if m:
            required.append(fact({"error_message": m.group("msg").strip()}, MAKEFILE, i))
    settings = []
    for i in range(1, len(lines)):
        if lines[i] is None:
            continue
        code, comment = strip_comment_hash(lines[i])
        m = re.match(r"^(?P<name>[A-Za-z_][A-Za-z0-9_]*)\s*=\s*(?P<val>.*?)\s*$", code)
        if m and m.group("name") in (
                "FC", "FC_EXE", "EXE", "MODE", "isOpenMP", "isPIO", "isGPTL",
                "PIO_FILESYSTEM_HINTS", "F_MASTER", "NCDF_PATH", "NCDF_C_PATH",
                "NCDF_FORTRAN_PATH", "PNETCDF_PATH", "PIO_PATH", "LIBOPENMP"):
            settings.append(fact({
                "setting": m.group("name"),
                "shipped_value": m.group("val") or None,
                "meaning": comment,
            }, MAKEFILE, i))
    flags = []
    for i in range(1, len(lines)):
        if lines[i] is None:
            continue
        m = re.match(r"^\s*FLAGS(?:_OMP)?\s*\+?=\s*(?P<val>.+?)\s*$", lines[i])
        if m:
            ctx = None
            for j in range(i - 1, max(i - 6, 0), -1):
                if lines[j] is None:
                    continue
                cm = re.match(r'^\s*ifeq\s+"\$\((?P<v>\w+)\)"\s+"(?P<val>\w+)"', lines[j])
                if cm:
                    ctx = f"{cm.group('v')}={cm.group('val')}"
                    break
            flags.append(fact({"context": ctx, "flags": m.group("val")}, MAKEFILE, i))
    for pat, statement in (
        (r"VERSION\s*=\s*\$\(shell git describe --tag\)",
         "the executable's reported version, branch and hash are taken from git at "
         "compile time via -DVERSION/-DBRANCH/-DHASH; built by this Makefile outside a "
         "git working tree the shell commands return nothing and the three are written "
         "as empty strings, since every compiler arm passes the macros regardless -- "
         "the globalData initialiser 'undefined' survives only in a binary built "
         "without those -D flags"),
        (r"ifeq\s+\"\$\(isPIO\)\"\s+\"yes\"",
         "PIO is optional at build time (isPIO), but every history and restart write in "
         "the pinned code goes through pio_utils, so the build shipped with isPIO=yes is "
         "the supported path"),
    ):
        f = _first_match(lines, pat, MAKEFILE, statement)
        if f:
            facts.append(f)

    return {
        "pack": PACK, "catalog": "build",
        "generator": "tools/extract_pack.py --pack mizuroute build",
        "generator_version": GENERATOR_VERSION, "scope": SCOPE,
        "entries_key": "settings", "entry_kind": "mizuRoute build setting",
        "count": len(settings),
        "settings": settings,
        "must_be_set": required,
        "must_be_set_count": len(required),
        "compiler_flags": flags,
        "compiler_flags_count": len(flags),
        "build_facts": facts,
        "note": "What route/build/Makefile requires, as facts. `must_be_set` are the "
                "variables the Makefile itself aborts on when they are empty; `settings` "
                "are the user-configurable variables with the value the pinned checkout "
                "ships (an empty shipped value means the user must fill it in). "
                "`compiler_flags` lists each FLAGS assignment with the compiler/mode "
                "combination that selects it. NetCDF (C and Fortran) is unconditional; "
                "MPI is reached through the compiler wrapper named in FC_EXE; PIO, "
                "PnetCDF, GPTL and OpenMP are switched by isPIO/isGPTL/isOpenMP. This "
                "pack never builds or runs the model: these are read facts. `count` "
                "counts `settings` only.",
    }


def strip_comment_hash(line):
    """Makefile comment split (`#`), returning (code, comment)."""
    idx = line.find("#")
    if idx < 0:
        return line, None
    return line[:idx], line[idx + 1:].strip()


# --------------------------------------------------------------------------------------
# Validation: parse both sample control files with the extracted control-key catalog.
# --------------------------------------------------------------------------------------

def VALIDATION(root):
    """Confront the extracted control-key catalog with the two sample control files the
    pinned checkout ships -- the only mizuRoute input this pack can reach. Counts only:
    no paths outside the checkout, no run identifiers. There is no model output anywhere
    reachable by this pack, so nothing here is or can be observed_in_output/both."""
    table, _, _ = parse_control_keys_table(root)
    allowed = parse_allowed_values(root)
    parsed = {e["key"]: e for e in table}
    samples = parse_sample_controls(root)
    report = {
        "note": "parsed against the two sample control files shipped in the pinned "
                "checkout (route/settings/) -- control-file facts only; no model output "
                "exists anywhere reachable by this pack, so nothing here is or can be "
                "`observed_in_output`/`both`.",
    }
    for sname, keys in sorted(samples.items()):
        unrecognized, out_of_set = [], []
        for k, v in sorted(keys.items()):
            if k not in parsed:
                unrecognized.append(k)
                continue
            target = parsed[k]["assigns_to"]
            for aname in _ALLOWED_FOR_KEY.get(target or "", []):
                a = allowed.get(aname)
                if not a:
                    continue
                accepted = {lab for entry in a["values"] for lab in entry["values"]}
                value = v["value"].split("/")[0] if aname.endswith("_length") else v["value"]
                if aname.endswith("_time") and "/" in v["value"]:
                    value = v["value"].split("/", 1)[1]
                if aname == "outputFrequency" and value.isdigit():
                    continue
                if value not in accepted:
                    out_of_set.append({"key": k, "value": v["value"],
                                       "constraint": aname, "accepted": sorted(accepted)})
        report[sname] = {
            "n_distinct_keys_in_sample_file": len(keys),
            "n_recognized_by_catalog": len(keys) - len(unrecognized),
            "keys_in_sample_not_in_catalog": unrecognized,
            "values_outside_the_catalogued_allowed_set": out_of_set,
        }
    doc_keys = parse_doc_keys(root)
    report["docs_cross_reference"] = {
        "n_control_keys_parsed_by_code": len(parsed),
        "n_control_keys_presented_as_keys_in_docs": len(doc_keys),
        "documented_but_not_parsed": sorted(set(doc_keys) - set(parsed)),
        "parsed_but_not_documented_count": len(set(parsed) - set(doc_keys)),
    }
    return report


# --------------------------------------------------------------------------------------
# CLI wiring
# --------------------------------------------------------------------------------------

CATALOGS = {
    "control-keys": cmd_control_keys,
    "routing-methods": cmd_routing_methods,
    "network-inputs": cmd_network_inputs,
    "outputs": cmd_outputs,
    "restart": cmd_restart,
    "parameters": cmd_parameters,
    "constants": cmd_constants,
    "parallelism": cmd_parallelism,
    "build": cmd_build,
}
FILENAME = {
    "control-keys": "control_keys.yaml",
    "routing-methods": "routing_methods.yaml",
    "network-inputs": "network_inputs.yaml",
    "outputs": "outputs.yaml",
    "restart": "restart.yaml",
    "parameters": "parameters.yaml",
    "constants": "constants.yaml",
    "parallelism": "parallelism.yaml",
    "build": "build.yaml",
}


def write_yaml(obj, out_path, command_name):
    header = [
        f"Generated by tools/extract_pack.py --pack mizuroute {command_name} -- do not hand-edit.",
        f"Regenerate: python3 tools/extract_pack.py --pack mizuroute {command_name} "
        f"--source-root <pinned-mizuRoute-checkout> --out {out_path.name}",
        f"Source commit: mizuroute@{MIZU_COMMIT} (tag {MIZU_TAG}).",
    ]
    _common.write_yaml(obj, out_path, header)
