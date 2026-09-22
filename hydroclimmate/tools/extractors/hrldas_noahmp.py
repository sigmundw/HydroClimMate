"""extractors/hrldas_noahmp.py -- mechanical, deterministic extractor module for the
hrldas-noahmp knowledge pack's catalogs, dispatched by tools/extract_pack.py (the CLI
entry point; run `python3 tools/extract_pack.py <command> --source-root ROOT --out ...`,
or `--pack hrldas-noahmp` explicitly -- this is the default pack, so every pre-existing
invocation of extract_pack.py is unchanged and regenerates this pack's catalogs
byte-identically). Every function here reads the pinned HRLDAS/Noah-MP source tree given
by --source-root and returns one catalog's data (see SCHEMA.md). Nothing here is
hand-typed: each fact is produced by a regex/parse pass over the actual source files, and
carries `where` = {file, line, commit} pointing at the exact source line(s) it came from.

Every helper and cmd_* function below is pack-specific, hrldas-noahmp extraction logic
only; write_yaml keeps this pack's own generated-file header text, so its catalogs
regenerate byte-identically run after run. tools/extract_pack.py owns argument parsing
and the shared write_json/main entry point for every pack; this module owns none of that,
only what to extract and how.

Pure stdlib (re, json, pathlib, hashlib) -- no numpy/netCDF4 needed to run these; that
dependency is confined to validate_catalogs.py, which confronts the output of these
extractors against real files.

Source-root layout expected (matches the pinned checkout used to build this pack):
  <root>/hrldas/IO_code/module_NoahMP_hrldas_driver.F   (LDASOUT/RESTART registration,
                                                           land_driver_exe / lsm_restart)
  <root>/hrldas/IO_code/module_hrldas_netcdf_io.F       (add_to_output*/add_to_restart*,
                                                           dimension/fill mechanics)
  <root>/hrldas/run/README.namelist
  <root>/noahmp/drivers/hrldas/NoahmpReadNamelistMod.F90
  <root>/noahmp/drivers/hrldas/ConfigVarInTransferMod.F90
  <root>/noahmp/src/*.F90                               (physics option dispatch)
  <root>/noahmp/src/ConstantDefineMod.F90
  <root>/noahmp/parameters/NoahmpTable.TBL
  <root>/hrldas/run/URBPARM*.TBL
  <root>/urban/wrf/module_sf_urban.F, NoahmpUrbanDriverMainMod.F

Catalog files (catalogs/*.yaml) are strict-subset YAML, human-readable but generated --
never hand-edit them (see hydroclimmate/tools/_miniyaml.py and SCHEMA.md). Only
catalogs/MANIFEST.json (generator, source commits, per-file counts and sha256) stays JSON,
since it is a machine-only build artifact, not a layer a person or agent reads.
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import _miniyaml  # noqa: E402
sys.path.insert(0, str(Path(__file__).resolve().parent))
import _common  # noqa: E402

GENERATOR_VERSION = "1.0.0"
# Canonical short form for both commits is `git rev-parse --short=8` in the pinned
# checkout: both hashes are 8 hex characters, used consistently everywhere in this pack.
HRLDAS_COMMIT = "d9f5b205"
NOAHMP_COMMIT = "9fbe6724"
SCOPE = f"HRLDAS {HRLDAS_COMMIT} + noahmp {NOAHMP_COMMIT}"

PACK = "hrldas-noahmp"
SOURCE_COMMITS = {"hrldas": HRLDAS_COMMIT, "noahmp": NOAHMP_COMMIT}


# --------------------------------------------------------------------------------------
# Generic helpers
# --------------------------------------------------------------------------------------

def read_lines(path):
    """1-indexed lines: lines[1] is the file's first line."""
    text = path.read_text(encoding="utf-8", errors="replace")
    return [None] + text.split("\n")


def strip_conditional_branches(lines, exclude_defines=("MPP_LAND", "_PARALLEL_")):
    """Return a copy of `lines` (same 1-indexing) with the branch of every
    #ifdef/#ifndef this pack's build path does not compile blanked to None, so a
    line-scanning regex pass never sees it. Single-level (non-nested) #ifdef/#else/
    #endif blocks only -- the only shape these HRLDAS I/O files actually use (checked
    by inspection). Preprocessor directive lines themselves are also blanked.
    Without this, a regex scan double-counts every field guarded by
    '#ifdef MPP_LAND ... #else ... #endif' (XLAT/XLONG were each counted 3x in
    catalogs/setup.yaml before this was fixed)."""
    out = list(lines)
    mode_stack = []  # 'skip' or 'keep', one entry per open #if*/#endif level
    ifdef_re = re.compile(r'^#\s*ifdef\s+(\w+)')
    ifndef_re = re.compile(r'^#\s*ifndef\s+(\w+)')
    for i in range(1, len(lines)):
        line = lines[i]
        if line is None:
            continue
        s = line.strip()
        m = ifdef_re.match(s)
        if m:
            mode_stack.append("skip" if m.group(1) in exclude_defines else "keep")
            out[i] = None
            continue
        m = ifndef_re.match(s)
        if m:
            mode_stack.append("keep" if m.group(1) in exclude_defines else "skip")
            out[i] = None
            continue
        if s.startswith("#else"):
            if mode_stack:
                mode_stack[-1] = "keep" if mode_stack[-1] == "skip" else "skip"
            out[i] = None
            continue
        if s.startswith("#endif"):
            if mode_stack:
                mode_stack.pop()
            out[i] = None
            continue
        if mode_stack and mode_stack[-1] == "skip":
            out[i] = None
    return out


def where(rel_path, line, commit_repo="hrldas"):
    commit = HRLDAS_COMMIT if commit_repo == "hrldas" else NOAHMP_COMMIT
    return {"file": rel_path, "line": line, "commit": f"{commit_repo}@{commit}"}


def fact(extra, rel_path, line, commit_repo="hrldas", evidence="source_read"):
    d = dict(extra)
    d["where"] = where(rel_path, line, commit_repo)
    d["evidence"] = evidence
    d["scope"] = SCOPE
    return d


def relpath(root, path):
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def slice_subroutine(lines, start_pat, end_pat, from_line=1):
    """Return (start_idx, end_idx) 1-indexed inclusive for the first subroutine whose
    header matches start_pat (searched from from_line) ending at the first line
    matching end_pat at or after that start."""
    start = None
    for i in range(from_line, len(lines)):
        if lines[i] is not None and re.search(start_pat, lines[i], re.I):
            start = i
            break
    if start is None:
        return None, None
    end = None
    for i in range(start + 1, len(lines)):
        if lines[i] is not None and re.search(end_pat, lines[i], re.I):
            end = i
            break
    return start, end


IF_OPEN = re.compile(r"^\s*(?:[A-Za-z_][A-Za-z0-9_]*\s*:\s*)?if\s*\((.*)\)\s*then\s*(!.*)?$", re.I)
IF_CLOSE = re.compile(r"^\s*end\s*if\b", re.I)


def if_stack_by_line(lines, start, end):
    """Map line number -> list of currently-open 'if (...) then' condition strings,
    for lines start..end inclusive. Single-line 'if (...) call x' statements (no
    'then') never open a block and are not tracked here."""
    stack = []
    out = {}
    for i in range(start, end + 1):
        line = lines[i]
        if line is None:
            out[i] = list(stack)
            continue
        m = IF_OPEN.match(line)
        if m:
            out[i] = list(stack)
            stack.append(m.group(1).strip())
            continue
        if IF_CLOSE.match(line):
            out[i] = list(stack)
            if stack:
                stack.pop()
            continue
        out[i] = list(stack)
    return out


def sha256_of(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def join_continuations(lines):
    """Merge Fortran free-form '&' line continuations. Returns a dict mapping the
    starting line number of each (possibly multi-line) statement to its merged text,
    for lines that are themselves continuations of a previous line."""
    merged = {}
    i = 1
    n = len(lines)
    while i < n:
        line = lines[i]
        if line is None:
            i += 1
            continue
        buf = line
        start = i
        while buf.rstrip().endswith("&") and i + 1 < n:
            i += 1
            nxt = lines[i] or ""
            buf = buf.rstrip()[:-1] + " " + nxt.strip()
        if i != start:
            merged[start] = buf
        i += 1
    return merged


# --------------------------------------------------------------------------------------
# Layer-tag -> netCDF dimension name tables, transcribed verbatim from the nf90_def_dim
# calls in module_hrldas_netcdf_io.F (see file:line evidence attached to each use).
# --------------------------------------------------------------------------------------

# add_to_output_3d's snow_or_soil tag -> LDASOUT dimension name (prepare_output_file_seq,
# module_hrldas_netcdf_io.F:3142-3144; SOIL/SNOW confirmed again at prepare_output_file_mpp
# 3025-3027, RADN tag maps to rad_num).
OUTPUT_LAYER_DIM = {
    "SOIL": ("soil_layers_stag", 3142),
    "SNOW": ("snow_layers", 3143),
    "RADN": ("rad_num", 3144),
}

# add_to_restart_3d's layers tag -> RESTART dimension name (module_hrldas_netcdf_io.F
# nf90_def_dim block, lines 3730-3749).
RESTART_LAYER_DIM = {
    "SOIL": ("soil_layers_stag", 3734),
    "SNOW": ("snow_layers", 3735),
    "SOSN": ("sosn_layers", 3736),
    "RADN": ("rad_layers", 3738),
    "UBHI": ("ubhi_layers", 3739),
    "UZRD": ("uzrd_layers", 3740),
    "UZWD": ("uzwd_layers", 3741),
    "UBGD": ("ubgd_layers", 3742),
    "UBZD": ("ubzd_layers", 3743),
    "UZDF": ("uzdf_layers", 3744),
    "UBBD": ("ubbd_layers", 3745),
    "UBWD": ("ubwd_layers", 3746),
    "UGBD": ("ugbd_layers", 3747),
    "UFBD": ("ufbd_layers", 3748),
    "ZGRD": ("zgrd_layers", 3749),
}

NETCDF_IO = "hrldas/IO_code/module_hrldas_netcdf_io.F"

# nf90_def_var dim argument order as written at the two variable-defining routines that
# every add_to_output/add_to_restart call eventually reaches (module_hrldas_netcdf_io.F).
DIM_ORDER_2D = ["west_east", "south_north", "Time"]           # make_var_att_2d:def_var
DIM_ORDER_3D = ["west_east", "<layer-dim>", "south_north", "Time"]  # make_var_att_3d:def_var


# --------------------------------------------------------------------------------------
# outputs / restart: driver-array kind classification (accumulation/reset search)
# --------------------------------------------------------------------------------------

KIND_EVIDENCE_FILES = [
    "hrldas/IO_code/module_NoahMP_hrldas_driver.F",
    "hrldas/IO_code/module_hrldas_netcdf_io.F",
    "noahmp/drivers/hrldas/NoahmpIOVarInitMod.F90",
    "noahmp/drivers/hrldas/WaterVarOutTransferMod.F90",
    "noahmp/drivers/hrldas/EnergyVarOutTransferMod.F90",
    "noahmp/drivers/hrldas/ForcingVarOutTransferMod.F90",
    "noahmp/drivers/hrldas/BiochemVarOutTransferMod.F90",
]


def classify_kind(root, array_name):
    """Mechanical kind classification for a NoahmpIO% field, scoped to
    KIND_EVIDENCE_FILES (the HRLDAS driver/IO modules and the NoahmpIO transfer/init
    modules that populate NoahmpIO% fields from the physics). This is a deliberate scope
    restriction: the internal physics arrays inside noahmp/src use different local
    names, and tracing every one of those is out of mechanical reach at this pass.
    Within scope:
      - reset_evidence: a line 'NAME = 0' (or '= 0.0') found in an *Init* module (a
        one-time initialization at run start, not a per-step reset) is recorded but does
        NOT by itself imply a periodic reset.
      - accumulate_evidence: a self-referencing line 'NAME(...) = NAME(...) + ...'
        (accumulation).
      - overwrite_evidence: a non-self-referencing plain assignment 'NAME(...) = ...'
        found only in a *Transfer* module copying a physics flux/state into NoahmpIO%NAME
        every call (characteristic of an instantaneous or interval-mean field).
    Returns (kind, evidence_dict).
    """
    name_pat = re.compile(r"(?<![A-Za-z0-9_])" + re.escape(array_name) + r"(?![A-Za-z0-9_])")
    self_assign_pat = re.compile(
        r"(?<![A-Za-z0-9_])" + re.escape(array_name) + r"\s*(\([^)]*\))?\s*=\s*"
        r"(?:NoahmpIO\s*%\s*)?" + re.escape(array_name) + r"\s*(\([^)]*\))?\s*\+", re.I)
    reset_pat = re.compile(
        r"(?<![A-Za-z0-9_])" + re.escape(array_name) + r"\s*(\([^)]*\))?\s*=\s*0\.?0?\b", re.I)
    plain_assign_pat = re.compile(
        r"(?<![A-Za-z0-9_])" + re.escape(array_name) + r"\s*(\([^)]*\))?\s*=\s*(?!0\.?0?\b)", re.I)

    do_loop_re = re.compile(r"^\s*do\s+\w+\s*=", re.I)
    enddo_re = re.compile(r"^\s*end\s*do\b", re.I)

    accumulate_evidence = None
    reset_init_evidence = None
    reset_other_evidence = None
    overwrite_evidence = None

    for relf in KIND_EVIDENCE_FILES:
        p = root / relf
        if not p.is_file():
            continue
        lines = read_lines(p)
        is_init_file = "Init" in relf
        for i in range(1, len(lines)):
            line = lines[i]
            if line is None or not name_pat.search(line):
                continue
            if "add_to_output" in line or "add_to_restart" in line:
                continue  # registration calls, not an assignment site
            if self_assign_pat.search(line) and accumulate_evidence is None:
                accumulate_evidence = {"file": relf, "line": i, "text": line.strip()}
                continue
            if reset_pat.search(line):
                if is_init_file and reset_init_evidence is None:
                    reset_init_evidence = {"file": relf, "line": i, "text": line.strip()}
                elif not is_init_file and reset_other_evidence is None:
                    reset_other_evidence = {"file": relf, "line": i, "text": line.strip()}
                continue
            if plain_assign_pat.search(line) and "Transfer" in relf and overwrite_evidence is None:
                overwrite_evidence = {"file": relf, "line": i, "text": line.strip()}

    evidence = {
        "accumulate": accumulate_evidence,
        "reset_at_init": reset_init_evidence,
        "reset_elsewhere": reset_other_evidence,
        "overwrite_in_transfer": overwrite_evidence,
    }
    if (accumulate_evidence and reset_other_evidence
            and accumulate_evidence["file"] == reset_other_evidence["file"]):
        # 'reset then accumulate' in the SAME file, close together, with a DO-loop
        # opening between the two lines and not yet closed at the accumulate line, is a
        # sum over layers within one call (do LoopInd = ...; X = 0.0 before the loop,
        # X = X + ... inside it) -- not a since-start time accumulator. Checked
        # mechanically, not special-cased by variable name.
        relf = accumulate_evidence["file"]
        lo, hi = sorted((reset_other_evidence["line"], accumulate_evidence["line"]))
        p = root / relf
        loop_lines = read_lines(p)
        depth = 0
        opened_before_accumulate = False
        for j in range(lo, hi + 1):
            ln = loop_lines[j] if j < len(loop_lines) else None
            if ln is None:
                continue
            if do_loop_re.match(ln):
                depth += 1
                if j < accumulate_evidence["line"]:
                    opened_before_accumulate = True
            elif enddo_re.match(ln):
                depth -= 1
        if opened_before_accumulate and depth > 0:
            return "layer_integrated_state", evidence
    if accumulate_evidence and reset_other_evidence:
        return "accumulated_and_reset", evidence
    if accumulate_evidence and not reset_other_evidence:
        return "accumulated_since_start", evidence
    if overwrite_evidence and not accumulate_evidence:
        # Overwritten fresh from a Transfer module every call: this is consistent with
        # either a prognostic state (e.g. SNEQV) or an instantaneous flux/rate (e.g.
        # EMISS) copied out of the physics each timestep. The mechanical pass here
        # cannot tell these apart (that would need classifying the physical quantity,
        # not just the assignment pattern) -- never guessed further than the source
        # supports.
        return "state_or_instantaneous", evidence
    if reset_init_evidence and not accumulate_evidence and not overwrite_evidence:
        return "state", evidence
    return "undetermined", evidence


# --------------------------------------------------------------------------------------
# outputs
# --------------------------------------------------------------------------------------

ADD_TO_OUTPUT_RE = re.compile(
    r'call\s+add_to_output\s*\(\s*NoahmpIO\s*%\s*([A-Za-z0-9_]+)\s*(\([^)]*\))?\s*,\s*'
    r'"([^"]*)"\s*,\s*"([^"]*)"\s*,\s*"([^"]*)"\s*(?:,\s*"([A-Z]+)")?\s*\)', re.I)

_DECL_RE = re.compile(r"^\s*(integer|real)\b[^!]*::\s*(.+?)\s*(?:!.*)?$", re.I)

# add_to_output is a Fortran generic interface that dispatches on the declared type of
# the NoahmpIO% argument -- add_to_output_2d_float -> put_var_2d (masks water-body cells
# with -1.0E33), add_to_output_2d_integer -> put_var_int (NO masking at all, checked:
# module_hrldas_netcdf_io.F:3493-3520 has no 'where'/mask block, unlike put_var_2d at
# :3453-3488). An earlier version of this extractor used the float text for every 2D
# variable regardless of dtype, contradicting the pack's own failures.md entry on
# IVGTYP/ISLTYP/ISNOW; fixed by actually resolving each variable's declared dtype.

def build_noahmpio_dtype_map(root):
    """name.upper() -> 'integer' | 'real', parsed from every `integer`/`real ::` field
    declaration in NoahmpIOVarType.F90. Some matched names are scalar config fields, not
    output arrays -- harmless, since callers only look up names that are actually used in
    an `add_to_output(NoahmpIO%NAME, ...)` call."""
    path = root / "noahmp/drivers/hrldas/NoahmpIOVarType.F90"
    dtype = {}
    if not path.is_file():
        return dtype
    for raw in path.read_text(encoding="utf-8", errors="replace").split("\n"):
        m = _DECL_RE.match(raw)
        if not m:
            continue
        kind, names_part = m.group(1).lower(), m.group(2)
        names_part = names_part.rstrip(", &").rstrip(",")
        for token in names_part.split(","):
            name = re.sub(r"\(.*", "", token).strip()
            if name and re.match(r"^[A-Za-z_]\w*$", name):
                dtype[name.upper()] = kind
    return dtype


def cmd_outputs(root):
    driver = "hrldas/IO_code/module_NoahMP_hrldas_driver.F"
    lines = read_lines(root / driver)
    start, end = slice_subroutine(lines, r"^\s*subroutine\s+land_driver_exe\b",
                                   r"^\s*end\s*subroutine\s+land_driver_exe\b")
    if start is None:
        sys.exit("ERROR: could not locate land_driver_exe in " + driver)
    stacks = if_stack_by_line(lines, start, end)
    dtype_map = build_noahmpio_dtype_map(root)

    variables = []
    for i in range(start, end + 1):
        line = lines[i]
        if line is None or "add_to_output" not in line:
            continue
        m = ADD_TO_OUTPUT_RE.search(line)
        if not m:
            continue
        array, idx_expr, name, description, units, layer_tag = m.groups()
        gating = stacks.get(i, [])
        if layer_tag:
            dims = list(DIM_ORDER_3D)
            dim_name, dim_line = OUTPUT_LAYER_DIM.get(layer_tag, (f"<unknown:{layer_tag}>", None))
            dims[1] = dim_name
            dimensionality = f"3D ({layer_tag} layer)"
        else:
            dims = list(DIM_ORDER_2D)
            dimensionality = "2D"
        kind, kind_evidence = classify_kind(root, array)
        array_dtype = dtype_map.get(array.upper())
        if layer_tag:
            fill_note = None
        elif array_dtype == "integer":
            fill_note = (
                "add_to_output dispatches this INTEGER field to add_to_output_2d_integer "
                "-> put_var_int (module_hrldas_netcdf_io.F:3493-3520), which applies NO "
                "water-body mask and writes vardata unchanged -- unlike put_var_2d for "
                "real fields (module_hrldas_netcdf_io.F:3453-3488, masks with -1.0E33 "
                "where IVGTYP==ISWATER). No _FillValue attribute is declared either way."
            )
        else:
            fill_note = (
                "add_to_output dispatches this REAL field to add_to_output_2d_float -> "
                "put_var_2d (module_hrldas_netcdf_io.F:3453-3488), which masks "
                "water-body cells (IVGTYP==ISWATER) with -1.0E33 for non-restart output "
                "writes; no _FillValue attribute is declared on the variable itself."
                + ("" if array_dtype == "real" else
                   " (dtype not resolved in NoahmpIOVarType.F90 -- assumed real, the "
                   "add_to_output default path; verify before relying on this note.)")
            )
        entry = fact({
            "name": name,
            "driver_array": f"NoahmpIO%{array}" + (idx_expr or ""),
            "description": description,
            "units": units,
            "dimensionality": dimensionality,
            "dim_order": dims,
            "gating": gating,
            "kind": kind,
            "kind_evidence": kind_evidence,
            "dtype": array_dtype,
            "fill_note": fill_note,
        }, driver, i)
        variables.append(entry)

    return {
        "pack": "hrldas-noahmp", "catalog": "outputs",
        "generator": "tools/extract_pack.py outputs", "generator_version": GENERATOR_VERSION,
        "scope": SCOPE, "count": len(variables), "variables": variables,
    }


# --------------------------------------------------------------------------------------
# restart
# --------------------------------------------------------------------------------------

ADD_TO_RESTART_RE = re.compile(
    r'call\s+add_to_restart\s*\(\s*NoahmpIO\s*%\s*([A-Za-z0-9_]+)\s*(\([^)]*\))?\s*,\s*'
    r'"([^"]*)"\s*(?:,\s*layers\s*=\s*"([A-Z]+)")?\s*\)', re.I)


def cmd_restart(root):
    driver = "hrldas/IO_code/module_NoahMP_hrldas_driver.F"
    lines = read_lines(root / driver)
    start, end = slice_subroutine(lines, r"^\s*subroutine\s+lsm_restart\b",
                                   r"^\s*end\s*subroutine\s+lsm_restart\b")
    if start is None:
        sys.exit("ERROR: could not locate lsm_restart in " + driver)
    stacks = if_stack_by_line(lines, start, end)

    variables = []
    for i in range(start, end + 1):
        line = lines[i]
        if line is None or "add_to_restart" not in line:
            continue
        m = ADD_TO_RESTART_RE.search(line)
        if not m:
            continue
        array, idx_expr, name, layer_tag = m.groups()
        gating = stacks.get(i, [])
        if layer_tag:
            dims = list(DIM_ORDER_3D)
            dim_name, dim_line = RESTART_LAYER_DIM.get(layer_tag, (f"<unknown:{layer_tag}>", None))
            dims[1] = dim_name
            dimensionality = f"3D ({layer_tag} layer)"
        else:
            dims = list(DIM_ORDER_2D)
            dimensionality = "2D"
        kind, kind_evidence = classify_kind(root, array)
        entry = fact({
            "name": name,
            "driver_array": f"NoahmpIO%{array}" + (idx_expr or ""),
            "description": None,  # add_to_restart carries no description arg at these call sites
            "units": None,        # add_to_restart's units arg is optional and not passed here
            "dimensionality": dimensionality,
            "dim_order": dims,
            "gating": gating,
            "kind": kind,
            "kind_evidence": kind_evidence,
        }, driver, i)
        variables.append(entry)

    return {
        "pack": "hrldas-noahmp", "catalog": "restart",
        "generator": "tools/extract_pack.py restart", "generator_version": GENERATOR_VERSION,
        "scope": SCOPE, "count": len(variables), "variables": variables,
    }


# --------------------------------------------------------------------------------------
# forcing (LDASIN) and setup (HRLDAS_SETUP_FILE)
# --------------------------------------------------------------------------------------

def cmd_forcing(root):
    io_file = "hrldas/IO_code/module_hrldas_netcdf_io.F"
    lines = read_lines(root / io_file)
    start, end = slice_subroutine(lines, r"^\s*subroutine\s+READFORC_HRLDAS\b",
                                   r"^\s*end\s*subroutine\s+READFORC_HRLDAS\b")
    if start is None:
        sys.exit("ERROR: could not locate READFORC_HRLDAS")

    call_re = re.compile(
        r'call\s+get_2d_netcdf\s*\(\s*trim\s*\(\s*(forcing_name_\w+)\s*\)\s*,\s*ncid\s*,\s*'
        r'nextread\s*%\s*(\w+)\s*,\s*units\s*,.*?,\s*(FATAL|NOT_FATAL)\s*,', re.I)
    literal_re = re.compile(
        r'call\s+get_2d_netcdf\s*\(\s*"([A-Za-z0-9_]+)"\s*,\s*ncid\s*,\s*'
        r'nextread\s*%\s*(\w+)\s*,\s*units\s*,.*?,\s*(FATAL|NOT_FATAL)\s*,', re.I)

    entries = []
    for i in range(start, end + 1):
        line = lines[i]
        if line is None or "get_2d_netcdf" not in line:
            continue
        m = call_re.search(line)
        if m:
            nml_key, field, req = m.groups()
            entries.append(fact({
                "role": field, "namelist_rename_key": nml_key.lower(),
                "ldasin_name_source": "namelist default (NoahmpReadNamelistMod.F90); "
                                       "renamed at run time by this namelist key",
                "required": req == "FATAL",
            }, io_file, i))
            continue
        m = literal_re.search(line)
        if m:
            varname, field, req = m.groups()
            entries.append(fact({
                "role": field, "ldasin_name": varname, "required": req == "FATAL",
            }, io_file, i))

    # AEROSOL forcing (SNICAR aerosol deposition), a separate subroutine/namelist keys.
    astart, aend = slice_subroutine(lines, r"^\s*subroutine\s+READFORC_AEROSOL\b",
                                     r"^\s*end\s*subroutine\s+READFORC_AEROSOL\b")
    if astart:
        for i in range(astart, aend + 1):
            line = lines[i]
            if line is None or "get_2d_netcdf" not in line:
                continue
            m = call_re.search(line)
            if m:
                nml_key, field, req = m.groups()
                entries.append(fact({
                    "role": field, "namelist_rename_key": nml_key.lower(),
                    "ldasin_name_source": "namelist default; aerosol forcing stream",
                    "required": req == "FATAL",
                }, io_file, i))

    # Namelist defaults for the forcing_name_* keys (what LDASIN name each maps to unless
    # overridden), read from NoahmpReadNamelistMod.F90.
    nml_file = "noahmp/drivers/hrldas/NoahmpReadNamelistMod.F90"
    nml_lines = read_lines(root / nml_file)
    default_re = re.compile(r'character\(len=256\)\s*::\s*(forcing_name_\w+)\s*=\s*"([^"]*)"', re.I)
    defaults = {}
    for i in range(1, len(nml_lines)):
        line = nml_lines[i]
        if line is None:
            continue
        m = default_re.search(line)
        if m:
            defaults[m.group(1).lower()] = fact({"key": m.group(1).lower(), "default": m.group(2)},
                                                  nml_file, i, commit_repo="noahmp")
    for e in entries:
        key = e.get("namelist_rename_key")
        if key and key in defaults:
            e["namelist_default"] = defaults[key]["default"]

    return {
        "pack": "hrldas-noahmp", "catalog": "forcing",
        "generator": "tools/extract_pack.py forcing", "generator_version": GENERATOR_VERSION,
        "scope": SCOPE, "count": len(entries), "inputs": entries,
    }


def cmd_setup(root):
    """Scans five subroutines and recognizes four call patterns, with conditional
    compilation branches stripped first (see strip_conditional_branches), so it does
    not miss a field read by a less-common call pattern (FRC_URB2D, TSK, TSLB, SMOIS,
    SNOW, SNODEP, CANWAT, DZS, VEGFRA, SHDMAX, SHDMIN, ...) and does not double/
    triple-count a field guarded by an #ifdef MPP_LAND / #else branch this build does
    not compile."""
    io_file = "hrldas/IO_code/module_hrldas_netcdf_io.F"
    raw_lines = read_lines(root / io_file)
    lines = strip_conditional_branches(raw_lines)
    entries = []

    # get_landuse_netcdf/get_soilcat_netcdf hardcode the NetCDF variable name they read
    # *inside their own body*, as a `character(...), parameter :: name = "..."` -- not
    # visible at the call site, which is why the field used to be recorded only as an
    # unresolved placeholder. Resolve it once, mechanically.
    def resolve_fixed_read_name(sub_name, fallback):
        s, e = slice_subroutine(lines, rf"^\s*subroutine\s+{sub_name}\b",
                                 rf"^\s*end\s*subroutine\s+{sub_name}\b")
        if s is None:
            return fallback
        for j in range(s, e + 1):
            ln = lines[j]
            if ln is None:
                continue
            mm = re.search(r'parameter\s*::\s*name\s*=\s*"([A-Za-z0-9_]+)"', ln, re.I)
            if mm:
                return mm.group(1)
        return fallback

    landuse_field_name = resolve_fixed_read_name(
        "get_landuse_netcdf", "(land-use category field, via get_landuse_netcdf)")
    soilcat_field_name = resolve_fixed_read_name(
        "get_soilcat_netcdf", "(soil-category field, via get_soilcat_netcdf)")

    get2d_re = re.compile(
        r'call\s+get_2d_netcdf\s*\(\s*"([A-Za-z0-9_]+)"\s*,\s*ncid\s*,.*?,\s*(FATAL|NOT_FATAL)\s*,', re.I)
    landuse_re = re.compile(r'call\s+get_landuse_netcdf\s*\(\s*ncid', re.I)
    soilcat_re = re.compile(r'call\s+get_soilcat_netcdf\s*\(\s*ncid', re.I)
    soillevel_re = re.compile(
        r'call\s+get_netcdf_soillevel\s*\(\s*"([A-Za-z0-9_]+)"\s*,\s*ncid\s*,.*?,\s*(FATAL|NOT_FATAL)\s*,', re.I)
    inline_inq_re = re.compile(r'nf90_inq_varid\s*\(\s*ncid\s*,\s*"([A-Za-z0-9_]+)"', re.I)
    name_assign_re = re.compile(r'^\s*name\s*=\s*"([A-Za-z0-9_]+)"\s*$', re.I)
    named_inq_re = re.compile(r'nf90_inq_varid\s*\(\s*ncid\s*,\s*name\s*,', re.I)
    global_att_re = re.compile(
        r'nf90_get_att\s*\(\s*ncid\s*,\s*NF90_GLOBAL\s*,\s*"([A-Za-z0-9_]+)"', re.I)

    for sub_pat, end_pat, meaning in (
        (r"^\s*subroutine\s+read_hrldas_hdrinfo\b", r"^\s*end\s*subroutine\s+read_hrldas_hdrinfo\b",
         "grid header (lat/lon, projection, land-use dataset ID)"),
        (r"^\s*subroutine\s+readland_hrldas\b", r"^\s*end\s*subroutine\s+readland_hrldas\b",
         "static land/soil fields"),
        (r"^\s*subroutine\s+readinit_hrldas\b", r"^\s*end\s*subroutine\s+readinit_hrldas\b",
         "initial state (cold start)"),
        (r"^\s*subroutine\s+READVEG_HRLDAS\b", r"^\s*end\s*subroutine\s+READVEG_HRLDAS\b",
         "vegetation fraction fields"),
        (r"^\s*subroutine\s+read_urban_map\b", r"^\s*end\s*subroutine\s+read_urban_map\b",
         "urban fraction"),
    ):
        start, end = slice_subroutine(lines, sub_pat, end_pat)
        if start is None:
            continue
        pending_name = None  # from a preceding 'name = "X"' assignment
        for i in range(start, end + 1):
            line = lines[i]
            if line is None:
                continue
            m = get2d_re.search(line)
            if m:
                varname, req = m.groups()
                entries.append(fact({
                    "field": varname, "required": req == "FATAL", "read_by": meaning,
                }, io_file, i))
                continue
            m = soillevel_re.search(line)
            if m:
                varname, req = m.groups()
                entries.append(fact({
                    "field": varname, "required": req == "FATAL",
                    "read_by": meaning + " (per soil layer, get_netcdf_soillevel)",
                }, io_file, i))
                continue
            if landuse_re.search(line):
                entries.append(fact({
                    "field": landuse_field_name, "required": True,
                    "read_by": meaning + " (via get_landuse_netcdf)",
                }, io_file, i))
                continue
            if soilcat_re.search(line):
                entries.append(fact({
                    "field": soilcat_field_name, "required": True,
                    "read_by": meaning + " (via get_soilcat_netcdf)",
                }, io_file, i))
                continue
            m = inline_inq_re.search(line)
            if m:
                entries.append(fact({
                    "field": m.group(1), "required": None,
                    "read_by": meaning + " (manual nf90_inq_varid/nf90_get_var, "
                                          "required-ness not stated by this call pattern)",
                }, io_file, i))
                continue
            m = global_att_re.search(line)
            if m:
                entries.append(fact({
                    "field": m.group(1), "required": True,
                    "read_by": meaning + " (NetCDF global attribute, not a variable -- "
                                          "nf90_get_att(ncid, NF90_GLOBAL, ...))",
                }, io_file, i))
                continue
            m = name_assign_re.match(line)
            if m:
                pending_name = (m.group(1), i)
                continue
            if pending_name and named_inq_re.search(line):
                varname, name_line = pending_name
                entries.append(fact({
                    "field": varname, "required": None,
                    "read_by": meaning + " (manual nf90_inq_varid/nf90_get_var, "
                                          "required-ness not stated by this call pattern)",
                }, io_file, name_line))
                pending_name = None

    return {
        "pack": "hrldas-noahmp", "catalog": "setup",
        "generator": "tools/extract_pack.py setup", "generator_version": GENERATOR_VERSION,
        "scope": SCOPE, "count": len(entries), "fields": entries,
    }


# --------------------------------------------------------------------------------------
# namelist
# --------------------------------------------------------------------------------------

DECL_RE = re.compile(
    r"^\s*(character\(len=\d+\)|real\(kind=kind_noahmp\)|real|integer|logical)"
    r"(?:\s*,\s*(?:dimension\([^)]*\)|parameter))*\s*::\s*([A-Za-z_][A-Za-z0-9_]*)"
    r"(?:\s*=\s*(.+?))?\s*(?:!(.*))?$", re.I)


def parse_namelist_declarations(root, nml_file):
    lines = read_lines(root / nml_file)
    start, end = slice_subroutine(lines, r"^\s*subroutine\s+NoahmpReadNamelist\b",
                                   r"^\s*namelist\s*/\s*NOAHLSM_OFFLINE\s*/", from_line=1)
    if start is None:
        sys.exit("ERROR: could not locate NoahmpReadNamelist declarations")
    decls = {}
    for i in range(start, end):
        line = lines[i]
        if line is None:
            continue
        m = DECL_RE.match(line)
        if not m:
            continue
        typ, name, default, comment = m.groups()
        decls[name.lower()] = {"type": typ.lower(), "default_in_code": default,
                                "comment": (comment or "").strip(), "line": i}
    return decls, end


def parse_namelist_statement(root, nml_file):
    """Returns (keys, conditional_keys) where conditional_keys maps key -> the #ifdef
    guard it is compiled under (e.g. 'WRF_HYDRO'), absent from the driver's ordinary
    (non-WRF_HYDRO) hrldas build path noted in pack.json's version_scope."""
    lines = read_lines(root / nml_file)
    text = "\n".join(l for l in lines[1:] if l is not None)
    m = re.search(r"namelist\s*/\s*NOAHLSM_OFFLINE\s*/(.*?)(?:\n\s*\n|!--)", text, re.S | re.I)
    if not m:
        m = re.search(r"namelist\s*/\s*NOAHLSM_OFFLINE\s*/(.*?)\n\s*!", text, re.S | re.I)
    block = m.group(1) if m else ""
    block = re.sub(r"!.*", "", block)

    conditional_keys = {}
    guard = None
    cleaned_lines = []
    for line in block.split("\n"):
        stripped = line.strip()
        if stripped.startswith("#ifdef"):
            guard = stripped.split()[-1]
            continue
        if stripped.startswith("#endif"):
            guard = None
            continue
        if stripped.startswith("#"):
            continue
        if guard:
            for tok in stripped.replace("&", ",").split(","):
                tok = tok.strip().lower()
                if tok:
                    conditional_keys[tok] = guard
        cleaned_lines.append(line)

    block = "\n".join(cleaned_lines).replace("&", " ")
    keys = [re.sub(r"\s+", " ", k).strip().lower() for k in block.split(",") if k.strip()]
    keys = [k for k in keys if k]
    return keys, conditional_keys


def parse_readme_namelist(root):
    p = root / "hrldas/run/README.namelist"
    lines = read_lines(p)
    entries = {}  # key -> {description, default, options: [{value, meaning, line}]}
    current_key = None
    key_line_re = re.compile(
        r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*(?:\(\d+\))?\s*=\s*.*?"
        r"(?:!\s*(?:\*\*\*)?\s*(.*?)\s*(?:\[default\s*=\s*(.*?)\])?\s*)?$")
    option_re = re.compile(r"^\s*!?\s*\**\s*(-?\d+)\s*(?:->|:)\s*(.+?)\s*$")
    for i in range(1, len(lines)):
        line = lines[i]
        if line is None or not line.strip():
            continue
        stripped = line.strip()
        if stripped.startswith("&") or stripped == "/":
            continue
        km = re.match(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*(?:\(\d+\))?\s*=", line)
        if km and not line.lstrip().startswith("!"):
            key = km.group(1).lower()
            current_key = key
            desc_m = re.search(r"!\s*(?:\*\*\*)?\s*(.*?)\s*(?:\[default\s*=\s*(.*?)\])?\s*$", line)
            desc, default = (desc_m.group(1), desc_m.group(2)) if desc_m else (None, None)
            entries.setdefault(key, {"description": None, "default": None, "options": [],
                                      "line": i})
            if desc:
                entries[key]["description"] = desc.strip()
            if default:
                entries[key]["default"] = default.strip()
            continue
        # continuation / option-meaning lines belong to current_key
        om = option_re.match(stripped.lstrip("!").strip() and stripped) or option_re.match(stripped)
        om = re.match(r"^!?\s*\**\s*(-?\d+)\s*(?:->|:)\s*(.+)$", stripped)
        if om and current_key:
            entries[current_key]["options"].append(
                {"value": om.group(1), "meaning": om.group(2).strip(), "line": i})
    return entries, p


def cmd_namelist(root):
    nml_file = "noahmp/drivers/hrldas/NoahmpReadNamelistMod.F90"
    decls, decl_end = parse_namelist_declarations(root, nml_file)
    keys, conditional_keys = parse_namelist_statement(root, nml_file)
    readme_entries, readme_path = parse_readme_namelist(root)
    readme_rel = relpath(root, readme_path)

    entries = []
    for key in keys:
        decl = decls.get(key)
        rd = readme_entries.get(key)
        e = {
            "key": key,
            "type": decl["type"] if decl else None,
            "default_in_code": decl["default_in_code"] if decl else None,
            "code_comment": decl["comment"] if decl else None,
            "readme_description": rd["description"] if rd else None,
            "readme_default": rd["default"] if rd else None,
            "allowed_values": rd["options"] if rd else [],
            "consumed_by": "NoahmpReadNamelistMod.NoahmpReadNamelist "
                           "(NOAHLSM_OFFLINE namelist group)",
            "documented_in_readme": rd is not None,
            "conditional_compilation": conditional_keys.get(key),
        }
        line = decl["line"] if decl else decl_end
        entries.append(fact(e, nml_file, line, commit_repo="noahmp"))

    # Flags present in README but never read as a namelist key at this commit.
    readme_only = sorted(set(readme_entries) - set(keys))
    read_but_undocumented = sorted(k for k in (set(keys) - set(readme_entries))
                                    if k not in conditional_keys)

    return {
        "pack": "hrldas-noahmp", "catalog": "namelist",
        "generator": "tools/extract_pack.py namelist", "generator_version": GENERATOR_VERSION,
        "scope": SCOPE, "count": len(entries), "options": entries,
        "documented_but_not_read": [
            fact({"key": k, "readme_description": readme_entries[k]["description"]},
                 readme_rel, readme_entries[k]["line"]) for k in readme_only],
        "read_but_undocumented_in_readme": [
            fact({"key": k}, nml_file,
                 (decls.get(k) or {}).get("line", decl_end), commit_repo="noahmp")
            for k in read_but_undocumented],
    }


# --------------------------------------------------------------------------------------
# physics options: namelist key -> IOPT_* -> Opt* -> {value: routine}
# --------------------------------------------------------------------------------------

def cmd_physics_options(root):
    """Every Opt*/SF_URBAN_PHYSICS field ConfigVarInTransferMod.F90 maps from a
    namelist key is covered (an earlier version only matched a single dispatch shape,
    'if (OptX == N) call Routine(...)', which covered 5 of the ~24 fields, and listed
    every value's every occurrence -- including inner sub-iteration re-dispatch call
    sites -- as if it were a separate meaning; both fixed here);
    'where it branches' is every comparison of that internal variable against an
    integer literal anywhere in noahmp/src/*.F90 or noahmp/drivers/hrldas/*.F90 (if/
    elseif/select-case-and-case, not just a dispatch call), grouped by value so a
    value used at more than one call site (e.g. a main dispatch plus a sub-iteration
    re-call) shows every citation without implying they are different schemes. Each
    value's scheme *name* is taken only from README.namelist's own value->meaning
    comments (already parsed per key, see parse_readme_namelist) -- mechanically
    reliable; a code-side routine name is recorded alongside when literally present in
    a matched line's 'call Routine(...)', for cross-checking, not asserted as the
    scheme name itself. Harder judgement calls (disagreements between the two, or a
    value with an inline-branching, no-named-routine scheme) belong in the curated
    curated/options_overlay.yaml, not guessed here."""
    nml_file = "noahmp/drivers/hrldas/NoahmpReadNamelistMod.F90"
    nml_lines = read_lines(root / nml_file)
    # NoahmpIO%IOPT_X = namelist_local_var  (assignment lines in NoahmpReadNamelist)
    iopt_assign_re = re.compile(r"NoahmpIO\s*%\s*(IOPT_\w+|SF_URBAN_PHYSICS)\s*=\s*([A-Za-z_]\w*)", re.I)
    iopt_to_key = {}
    for i in range(1, len(nml_lines)):
        line = nml_lines[i]
        if line is None:
            continue
        m = iopt_assign_re.search(line)
        if m:
            iopt, key = m.groups()
            iopt_to_key.setdefault(iopt.upper(), {"namelist_key": key.lower(), "line": i})
    decls, _decl_end = parse_namelist_declarations(root, nml_file)
    readme_entries, readme_path = parse_readme_namelist(root)
    readme_rel = relpath(root, readme_path)

    transfer_file = "noahmp/drivers/hrldas/ConfigVarInTransferMod.F90"
    transfer_lines = read_lines(root / transfer_file)
    opt_assign_re = re.compile(
        r"noahmp\s*%\s*config\s*%\s*nmlist\s*%\s*(Opt\w+)\s*=\s*NoahmpIO\s*%\s*(IOPT_\w+|SF_URBAN_PHYSICS)",
        re.I)
    opt_to_iopt = {}
    for i in range(1, len(transfer_lines)):
        line = transfer_lines[i]
        if line is None:
            continue
        m = opt_assign_re.search(line)
        if m:
            opt_name, iopt = m.groups()
            opt_to_iopt.setdefault(opt_name, {"iopt_field": iopt.upper(), "line": i})
    # SF_URBAN_PHYSICS never goes through an Opt* rename -- code compares
    # NoahmpIO%SF_URBAN_PHYSICS directly. Give it a synthetic "internal name" so it is
    # covered by the same branch scan as every Opt* field.
    opt_to_iopt.setdefault("SF_URBAN_PHYSICS", {"iopt_field": "SF_URBAN_PHYSICS", "line": None})

    # Every comparison of each internal option variable against an integer literal,
    # anywhere in the physics or HRLDAS driver-layer source: 'if (OptX == N)',
    # 'elseif (OptX == N)', and 'case (N)' following a 'select case (OptX)' block.
    branch_dirs = [root / "noahmp/src", root / "noahmp/drivers/hrldas"]
    branches = {opt: {} for opt in opt_to_iopt}  # opt_name -> {value: [citation, ...]}
    cmp_re = {
        opt: re.compile(r"\b" + re.escape(opt) + r"\s*==\s*(-?\d+)", re.I)
        for opt in branches
    }
    call_on_line_re = re.compile(r"\bcall\s+(\w+)", re.I)
    select_case_re = re.compile(r"select\s*case\s*\(\s*(\w+)\s*\)", re.I)
    case_re = re.compile(r"^\s*case\s*\(\s*(-?\d+)\s*\)", re.I)
    for d in branch_dirs:
        for p in sorted(d.glob("*.F90")):
            rel = relpath(root, p)
            lines = read_lines(p)
            select_target = None  # opt_name currently open in a select-case block
            for i in range(1, len(lines)):
                line = lines[i]
                if line is None:
                    continue
                sm = select_case_re.search(line)
                if sm and sm.group(1) in branches:
                    select_target = sm.group(1)
                    continue
                if select_target:
                    cm = case_re.match(line)
                    if cm:
                        branches[select_target].setdefault(cm.group(1), []).append(
                            {"file": rel, "line": i, "routine": None, "form": "select_case"})
                        continue
                    if re.match(r"^\s*end\s*select\b", line, re.I):
                        select_target = None
                        continue
                for opt, pat in cmp_re.items():
                    matches = list(pat.finditer(line))
                    if not matches:
                        continue
                    cm = call_on_line_re.search(line)
                    seen_values_this_line = set()
                    for m in matches:
                        if m.group(1) in seen_values_this_line:
                            continue  # e.g. 'if (OptX==3 .or. OptX==3)'; keep once per line
                        seen_values_this_line.add(m.group(1))
                        branches[opt].setdefault(m.group(1), []).append({
                            "file": rel, "line": i,
                            "routine": cm.group(1) if cm else None,
                            "form": "select_case" if "case" in line.lower() and select_target
                                    else ("if_call" if cm else "if"),
                        })

    options = []
    for opt_name in sorted(opt_to_iopt):
        iopt_info = opt_to_iopt[opt_name]
        key_info = iopt_to_key.get(iopt_info["iopt_field"])
        namelist_key = key_info["namelist_key"] if key_info else None
        decl = decls.get(namelist_key) if namelist_key else None
        rd = readme_entries.get(namelist_key) if namelist_key else None
        value_citations = branches.get(opt_name, {})
        code_branches = [
            {"value": v, "citations": [
                fact({"routine": c["routine"], "form": c["form"]}, c["file"], c["line"],
                     commit_repo="noahmp") for c in cites]}
            for v, cites in sorted(value_citations.items(), key=lambda kv: int(kv[0]))
        ]
        entry = {
            "internal_option_name": opt_name,
            "namelist_key": namelist_key,
            "iopt_field": iopt_info["iopt_field"],
            "default_in_code": decl["default_in_code"] if decl else None,
            "mapping_chain": {
                "namelist_to_iopt": fact({"note": "NoahmpIO%<IOPT> = <namelist local var>"},
                                          nml_file, key_info["line"] if key_info else 1,
                                          commit_repo="noahmp") if key_info else None,
                "iopt_to_internal": (
                    fact({"note": "noahmp%config%nmlist%<Opt> = NoahmpIO%<IOPT>"},
                         transfer_file, iopt_info["line"], commit_repo="noahmp")
                    if iopt_info["line"] is not None else
                    fact({"note": "compared directly as NoahmpIO%SF_URBAN_PHYSICS; "
                                   "no Opt*-renamed internal field"},
                         transfer_file, 1, commit_repo="noahmp")
                ),
            },
            "readme_values": [
                fact({"value": o["value"], "meaning": o["meaning"]}, readme_rel, o["line"])
                for o in (rd["options"] if rd else [])
            ],
            "code_branches": code_branches,
            "n_values_with_code_branch": len(code_branches),
            "n_values_in_readme": len(rd["options"]) if rd else 0,
        }
        options.append(entry)

    return {
        "pack": "hrldas-noahmp", "catalog": "physics_options",
        "generator": "tools/extract_pack.py physics-options", "generator_version": GENERATOR_VERSION,
        "scope": SCOPE, "count": len(options), "options": options,
        "note": "Covers every namelist-driven option ConfigVarInTransferMod.F90 maps to "
                "an internal Opt*/SF_URBAN_PHYSICS field (mechanical: readme_values from "
                "README.namelist's own value->meaning comments; code_branches from every "
                "'OptX == N' comparison -- if/elseif and select-case/case -- across "
                "noahmp/src and noahmp/drivers/hrldas, grouped by value with every citing "
                "file:line, not deduplicated to one). A value present in code_branches but "
                "not in readme_values, or vice versa, is a real, checkable disagreement, "
                "not an extraction gap -- see curated/options_overlay.yaml for the "
                "curated cross-check on the options that have been hand-verified. 'routine' on a "
                "citation is only the name literally following 'call' on that same line, "
                "never inferred; a branch with routine: null genuinely dispatches inline "
                "(a real finding about this codebase's dispatch style, not a shortfall).",
    }


# --------------------------------------------------------------------------------------
# constants
# --------------------------------------------------------------------------------------

CONST_RE = re.compile(
    r"real\(kind=kind_noahmp\)\s*,\s*public\s*,\s*parameter\s*::\s*"
    r"(\w+)\s*=\s*([0-9.eE+\-]+)\s*(?:!\s*(.*))?$", re.I)


def cmd_constants(root):
    p = "noahmp/src/ConstantDefineMod.F90"
    lines = read_lines(root / p)
    entries = []
    for i in range(1, len(lines)):
        line = lines[i]
        if line is None:
            continue
        m = CONST_RE.search(line)
        if not m:
            continue
        name, value, comment = m.groups()
        comment = (comment or "").strip()
        units = None
        um = re.search(r"\[([^\]]*)\]", comment)
        if um:
            units = um.group(1)
        entries.append(fact({
            "name": name, "value": value, "units": units, "comment": comment,
        }, p, i, commit_repo="noahmp"))
    return {
        "pack": "hrldas-noahmp", "catalog": "constants",
        "generator": "tools/extract_pack.py constants", "generator_version": GENERATOR_VERSION,
        "scope": SCOPE, "count": len(entries), "constants": entries,
    }


# --------------------------------------------------------------------------------------
# parameters: NoahmpTable.TBL groups + URBPARM*.TBL keys
# --------------------------------------------------------------------------------------

def parse_fortran_namelist_style_table(path):
    """Yield (group_name, body_lines_with_numbers) for each '&group ... /' block."""
    lines = read_lines(path)
    group = None
    body_start = None
    for i in range(1, len(lines)):
        line = lines[i]
        if line is None:
            continue
        gm = re.match(r"^\s*&(\w+)\s*$", line)
        if gm:
            group = gm.group(1)
            body_start = i + 1
            continue
        if group and re.match(r"^\s*/\s*$", line):
            yield group, body_start, i - 1
            group = None


CLASS_LIST_RE = re.compile(r"^\s*!\s*(\d+)\s*:\s*(.+?)\s*$")
PARAM_ARRAY_RE = re.compile(
    r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.+?)\s*(?:!\s*(.*))?$")

TBL_TO_IOARRAY_RE = re.compile(
    r"NoahmpIO\s*%\s*(\w+)_TABLE\s*(?:\([^)]*\))?\s*=\s*(\w+)\s*(?:\([^)]*\))?\s*$", re.I)


def build_tbl_alias_map(root):
    """Lookup-alias chain for table parameters (a user may type any of the three
    names): the TBL file's own parameter key (e.g. 'BB') -> the NoahmpIO%<X>_TABLE
    array that key's values are copied into (e.g. 'BEXP_TABLE') -> the short internal
    name a reader would recognize (e.g. 'BEXP', the array name with '_TABLE' stripped
    -- confirmed the same short name is also used as a local variable at several call
    sites, e.g. noahmp/drivers/hrldas/NoahmpGroundwaterInitMod.F90). Extracted by
    scanning every 'NoahmpIO%X_TABLE(...) = Y(...)' assignment in NoahmpReadTableMod.F90
    (220 at this commit); returns {TBL_KEY_UPPER: {"io_array": ..., "internal_name": ...,
    "where": {...}}}."""
    p = root / "noahmp/drivers/hrldas/NoahmpReadTableMod.F90"
    alias = {}
    if not p.is_file():
        return alias
    lines = read_lines(p)
    for i in range(1, len(lines)):
        line = lines[i]
        if line is None or "_TABLE" not in line or "=" not in line:
            continue
        m = TBL_TO_IOARRAY_RE.search(line)
        if not m:
            continue
        io_suffix, tbl_key = m.groups()
        io_array = f"{io_suffix}_TABLE"
        alias.setdefault(tbl_key.upper(), {
            "io_array": io_array, "internal_name": io_suffix,
            "where": where("noahmp/drivers/hrldas/NoahmpReadTableMod.F90", i, "noahmp"),
        })
    return alias


def cmd_parameters(root):
    tbl = "noahmp/parameters/NoahmpTable.TBL"
    lines = read_lines(root / tbl)
    tbl_alias = build_tbl_alias_map(root)
    groups = []
    landuse_class_names = {}
    for group, body_start, body_end in parse_fortran_namelist_style_table(root / tbl):
        params = []
        class_names = []
        for i in range(body_start, body_end + 1):
            line = lines[i]
            if line is None or not line.strip():
                continue
            cm = CLASS_LIST_RE.match(line)
            if cm:
                class_names.append({"index": int(cm.group(1)), "name": cm.group(2), "line": i})
                continue
            if line.strip().startswith("!"):
                continue
            pm = PARAM_ARRAY_RE.match(line)
            if pm:
                pname, values, comment = pm.groups()
                alias_info = tbl_alias.get(pname.upper())
                params.append(fact({
                    "parameter": pname, "values_as_written": values.strip(),
                    "description": (comment or "").strip() or None,
                    "noahmp_io_array": alias_info["io_array"] if alias_info else None,
                    "internal_name": alias_info["internal_name"] if alias_info else None,
                }, tbl, i, commit_repo="noahmp"))
        entry = {"group": group, "parameters": params}
        if class_names:
            entry["class_index_to_name"] = [
                fact({"index": c["index"], "name": c["name"]}, tbl, c["line"], commit_repo="noahmp")
                for c in class_names]
            landuse_class_names[group] = class_names
        groups.append(entry)

    # URBPARM tables: KEY( optional-index ) = value(s)   ! comment, flat key list.
    urban_tables = []
    for urb_name in ("hrldas/run/URBPARM.TBL", "hrldas/run/URBPARM_LCZ.TBL", "hrldas/run/URBPARM_UZE.TBL"):
        p = root / urb_name
        if not p.is_file():
            continue
        ulines = read_lines(p)
        keys = []
        for i in range(1, len(ulines)):
            line = ulines[i]
            if line is None or not line.strip() or line.strip().startswith("#"):
                continue
            km = re.match(r"^\s*([A-Za-z_][A-Za-z0-9_.]*)\s*:\s*(.+?)\s*$", line)
            if km:
                keys.append(fact({"key": km.group(1), "value_or_row": km.group(2)},
                                  urb_name, i, commit_repo="hrldas"))
        urban_tables.append({"table": urb_name, "keys": keys})

    return {
        "pack": "hrldas-noahmp", "catalog": "parameters",
        "generator": "tools/extract_pack.py parameters", "generator_version": GENERATOR_VERSION,
        "scope": SCOPE, "noahmp_table_groups": groups, "urbparm_tables": urban_tables,
        "count": sum(len(g["parameters"]) for g in groups) + sum(len(t["keys"]) for t in urban_tables),
    }


# --------------------------------------------------------------------------------------
# urban path facts
# --------------------------------------------------------------------------------------

def cmd_urban_path(root):
    facts = []

    # 1. Vegetation-type / greenness reassignment for urban cells (ConfigVarInTransferMod.F90).
    ctv = "noahmp/drivers/hrldas/ConfigVarInTransferMod.F90"
    lines = read_lines(root / ctv)
    for i in range(1, len(lines)):
        line = lines[i]
        if line is None:
            continue
        if "SF_URBAN_PHYSICS == 0" in line and "VegType" in "".join(l or "" for l in lines[i:i + 2]):
            facts.append(fact({
                "topic": "bulk_urban_fallback",
                "statement": "When SF_URBAN_PHYSICS==0 and the cell is urban "
                             "(IVGTYP==ISURBAN_TABLE or > URBTYPE_beg), VegType is set to "
                             "ISURBAN_TABLE and FlagUrban=.true.: Noah-MP's own bulk urban "
                             "class handles the cell (no explicit urban scheme).",
            }, ctv, i, commit_repo="noahmp"))
        if "GVFMAX(I,J)" in line and "0.96" in line:
            facts.append(fact({
                "topic": "urban_gvfmax_reassignment",
                "statement": "When SF_URBAN_PHYSICS>0 and the cell is urban, VegType is "
                             "reset to NATURAL_TABLE (rural natural vegetation; the "
                             "explicit urban scheme handles urban energy separately) and "
                             "GVFMAX(I,J) is forced to 0.96*100.0 (96%).",
            }, ctv, i, commit_repo="noahmp"))

    # 2. FRC_URB2D fallback to URBPARM table value (module_sf_urban.F, urban_var_init).
    urb = "urban/wrf/module_sf_urban.F"
    p = root / urb
    if p.is_file():
        ulines = read_lines(p)
        for i in range(1, len(ulines)):
            line = ulines[i]
            if line is None:
                continue
            if "FRC_URB_TBL(UTYPE_URB)" in line:
                facts.append(fact({
                    "topic": "frc_urb2d_table_fallback",
                    "statement": "In urban_var_init, if FRC_URB2D(I,J) read from the "
                                 "input file is not in (0, 1], it is overwritten with "
                                 "FRC_URB_TBL(UTYPE_URB) -- the URBPARM.TBL default urban "
                                 "fraction for that urban type -- with a warning printed; "
                                 "this happens only when the cell's own value was invalid.",
                }, urb, i, commit_repo="hrldas"))

    # 3. FRC_URB2D tile-weighting formulas (NoahmpUrbanDriverMainMod.F).
    nud = "urban/wrf/NoahmpUrbanDriverMainMod.F"
    p = root / nud
    if p.is_file():
        nlines = read_lines(p)
        merged = join_continuations(nlines)
        weight_re = re.compile(
            r"^\s*(\w+)\(I,J\)\s*=\s*FRC_URB2D\(I,J\)\s*\*\s*(\([^()]*(?:\([^()]*\)[^()]*)*\)|\w+)"
            r"\s*\+\s*\(1-?FRC_URB2D\(I,J\)\)", re.I)
        tile_weighted = []
        for i in range(1, len(nlines)):
            line = nlines[i]
            if line is None:
                continue
            text = merged.get(i, line)
            m = weight_re.match(text.strip())
            if m:
                tile_weighted.append({"field": m.group(1), "urban_source": m.group(2), "line": i})
        facts.append(fact({
            "topic": "frc_urb2d_tile_weighted_fields",
            "statement": "Fields combined as FRC_URB2D*<urban_value> + (1-FRC_URB2D)*<prior "
                         "grid value> after the urban call: " +
                         ", ".join(f"{t['field']} (from {t['urban_source']}, line {t['line']})"
                                   for t in tile_weighted) +
                         ". TS_URB2D is assigned directly (not tile-weighted; it is the "
                         "urban-only skin temperature diagnostic). EMISS is NOT in this "
                         "tile-weighted list at this commit.",
            "tile_weighted_fields": [t["field"] for t in tile_weighted],
        }, nud, tile_weighted[0]["line"] if tile_weighted else 1, commit_repo="hrldas"))

    # 4. noahmp_urban driver call argument roles (IN / OUT / IN/OUT), from the trailing
    #    per-line comment tags in module_NoahMP_hrldas_driver.F's call to noahmp_urban.
    driver = "hrldas/IO_code/module_NoahMP_hrldas_driver.F"
    dlines = read_lines(root / driver)
    start = end = None
    for i in range(1, len(dlines)):
        if dlines[i] and re.search(r"call\s+noahmp_urban\s*\(", dlines[i], re.I):
            start = i
            break
    if start:
        for i in range(start, len(dlines)):
            if dlines[i] and ")" in dlines[i] and "&" not in dlines[i].rstrip()[-2:]:
                end = i
                break
        role_re = re.compile(r"!\s*(IN/OUT|IN|OUT|H)\b", re.I)
        arg_roles = {}
        for i in range(start, (end or start) + 1):
            line = dlines[i]
            if not line:
                continue
            rm = role_re.search(line)
            role = rm.group(1).upper() if rm else None
            for am in re.finditer(r"NoahmpIO\s*%\s*([A-Za-z0-9_]+)", line):
                arg_roles.setdefault(am.group(1), {"role": role, "line": i})
        facts.append(fact({
            "topic": "noahmp_urban_call_argument_roles",
            "statement": "Argument role tags (from trailing comments on the "
                         "'call noahmp_urban(...)' block) for NoahmpIO fields passed to "
                         "the urban driver: 'IN' input to the urban scheme, 'OUT' urban "
                         "diagnostic only, 'IN/OUT' updated in place. Roles absent a tag "
                         "are recorded as null, not guessed.",
            "argument_count": len(arg_roles),
            "arguments": [{"field": k, "role": v["role"]} for k, v in sorted(arg_roles.items())],
        }, driver, start, commit_repo="hrldas"))

    return {
        "pack": "hrldas-noahmp", "catalog": "urban_path",
        "generator": "tools/extract_pack.py urban-path", "generator_version": GENERATOR_VERSION,
        "scope": SCOPE, "count": len(facts), "facts": facts,
    }


# --------------------------------------------------------------------------------------
# Catalog registry, consumed by tools/extract_pack.py's generic dispatcher.
# --------------------------------------------------------------------------------------

CATALOGS = {
    "outputs": cmd_outputs, "restart": cmd_restart, "forcing": cmd_forcing,
    "setup": cmd_setup, "namelist": cmd_namelist, "physics-options": cmd_physics_options,
    "constants": cmd_constants, "parameters": cmd_parameters, "urban-path": cmd_urban_path,
}
FILENAME = {
    "outputs": "outputs.yaml", "restart": "restart.yaml", "forcing": "forcing.yaml",
    "setup": "setup.yaml", "namelist": "namelist.yaml",
    "physics-options": "physics_options.yaml", "constants": "constants.yaml",
    "parameters": "parameters.yaml", "urban-path": "urban_path.yaml",
}


def write_yaml(obj, out_path, command_name):
    """Pack-specific header text -- unchanged from the pre-dispatcher extract_pack.py,
    so hrldas-noahmp's catalogs regenerate byte-identically through the new CLI."""
    header = [
        f"Generated by tools/extract_pack.py {command_name} -- do not hand-edit.",
        f"Regenerate: python3 tools/extract_pack.py {command_name} --source-root <pinned-checkout> --out {out_path.name}",
        f"Source commits: hrldas@{HRLDAS_COMMIT}, noahmp@{NOAHMP_COMMIT}.",
    ]
    _common.write_yaml(obj, out_path, header)
