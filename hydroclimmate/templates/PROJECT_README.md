# <Project name>

<Research group or lab>. Follows the HydroClimMate workflow.

Keep this concise (aim for 60–100 lines; shorter is fine). Link existing documentation,
configuration and logs; omit irrelevant fields. Maintain run commands here only.
Update confirmed durable facts affected by the task; do not turn this into a run history.

## Research objective and scope
- Main question: <question>
- Intended outputs: <outputs>
- Included / excluded: <boundaries>
- Research owner: <name or role>

## Project map
- Relevant code and entry points: <existing paths>
- Data documentation: <section or link>
- Methods, equations, assumptions, and limitations: <section or link>
- Tests and reference cases: <paths and origin of expected results>
- Working rules: AGENTS.md
- Important decisions: <DECISIONS.md, if used>
- Current state: <HANDOVER.md, if active>

## Data and methods essentials
- Input sources, versions, and access: <details; no credentials>
- Variables and units: <source and internal units>
- Temporal semantics: <rate / interval total / cumulative counter; intervals and calendar>
- Spatial semantics: <grid/mesh type; CRS; cell/node values; area source and equal-area evidence; aggregation weights, masks and coverage>
- Missing-data convention: <definition and handling>
- Core method and scientific constraints: <description or authoritative links>

## Environment and execution
- Environment setup / dependency record: <file and instructions>
- Small example input: <location and preparation>
- Small reproducible run: <exact command>
- Relevant validation: <command; expected behavior and tolerance rationale>
- Full run: <command and compute requirements>
- Output locations: <paths; overwrite behavior; authorization boundaries are in AGENTS.md>

## Result provenance
- Run records and diagnostics: <location>
- Records identify input versions, configuration snapshot, code state including uncommitted changes, environment, command, and output paths.
- Additional requirements: <seed / model version / HPC job information, if applicable>

## Known limitations
<Scientific or operational limitations; use Unknown where necessary.>
