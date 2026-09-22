# Core rules

Cross-feature rules loaded from the shared [SKILL.md](../SKILL.md) entrypoint. Read once per task; start with the primary feature.

## Establish context

- Identify the target project when one exists; targeted questions about documented models need no project, budget, research owner or task record. Templates are not live records.
- Check applicable project AGENTS.md instructions, including relevant directory-specific rules. Do not assume the host loaded them; do not reread instructions already available and current.
- Read relevant project README sections and an active task or handover only when needed. Inspect code or metadata to resolve stale or conflicting documentation.
- Do not submit jobs beyond authorization, overwrite existing results, or change scientific definitions without adoption. Continue within unchanged existing authorization.
- Missing documents do not authorize guessed budgets or configurations and do not block safe explanation. Ask only for missing facts that affect the next action.

## Local model knowledge

- For a model-specific question, use the [model index](models/index.md) to select the needed topic; skip overview when the topic is already known. Do not read every model or every topic. Read the applicable topic before tracing source code for a mechanism question; treat source tracing as the fallback when the pack does not cover it, not the default first step. A pack's symptom/pitfall topic (`failures.md` or `pitfalls.md`, depending on the pack) covers ways a result can look right and be wrong; read it before reporting a result the pack's method could quietly get wrong.
- A pack marked `depth: reference` in the model index (currently HRLDAS/Noah-MP, VIC and mizuRoute) is read differently from a `depth: outline` pack: start at its `card.md` (the only must-read file), look up any variable/option/parameter/constant name with `tools/hcm_lookup.py --pack <pack> <NAME>` instead of opening a catalog file, then open `failures.md` by symptom, `processes.md` by process/mechanism, or `recipes.md` by bounded task; never read a `catalogs/*.yaml` file wholesale. See [SCHEMA.md](models/SCHEMA.md).
- Confirm the implementation/version and configuration when the answer depends on them. General explanation may proceed with explicitly stated scope if the version is unknown.
- Prefer applicable local knowledge and inspect actual project metadata/code before assuming the description matches the run. Report source/implementation conflicts rather than silently changing definitions.
- Citations point to local source records. Follow external sources only for missing, conflicting or explicitly current information, when permitted. Offline, continue supported work and identify the exact unresolved dependency; never invent defaults or API names.
- Knowledge describes models, not execution authority. Lab settings stay in project records. Updates are deliberate, source-checked changes, not automatic rewriting during an ordinary task.
- A `depth: reference` pack also carries optional machine-readable declarations (data interface, switch effects, detectable checks, common workflows, a generated key index; see [SCHEMA.md](models/SCHEMA.md)) that `tools/hcm_check.py --pack`/`tools/hcm_lookup.py` confront with actual files. A declaration is not proof: it is the pack's own sourced claim, degraded to UNVERIFIED wherever it is not confirmed, never a substitute for reading the actual output. A `depth: outline` pack carries none of these.

### Source freshness

- A `Checked:` date older than 180 days is a review reminder, not an expiration or proof of error. Also review relevant claims when upstream changes affect them, local evidence conflicts, or they underpin a consequential result.
- With permitted access, compare the specific claim against the matching official release/source, not merely the newest webpage. Report changes or conflicts; preserve a valid older-version explanation with its scope.
- Offline or unable to fetch, disclose the date/coverage once and use supported local material and project code. Pause only a version-sensitive action lacking evidence; do not block basic explanation solely because of age.
- A working URL proves reachability only. Advance `Checked:` only after actually reviewing the pack's source-backed claims, recording scope and changes/gaps in its source record. A partial check is noted separately and does not refresh the entire pack.
- Do not auto-edit knowledge or upgrade a scientific configuration during an unrelated task. Propose substantive method changes for adoption; freshness review does not grant execution authority.

## Shared plan-to-execution checklist

Use these same five fields in discussion and as inputs to Run or Analyze. Reuse known answers from the request, project or existing task; do not require a separate form.

1. **Goal and scope** — outcome, included/excluded work and definitions to preserve.
2. **Inputs and selected method/configuration** — data, versions, entry point and adopted choices.
3. **Steps and output locations** — necessary actions, expected products and owners if coordinated.
4. **Resource budget and authorization** — sample scope, applicable compute/storage limits, costly retries and approved actions.
5. **Acceptance checks and pending choices** — expected checks, independent basis, tolerances, review needs and unresolved decisions with owners.

An unresolved item blocks only dependent actions. Method adoption is not authorization for unlimited computation. Escalation to Plan can be a short discussion of one item.

## Project documentation

Templates are starting points, read only when creating or updating the corresponding record. Merge into existing project files; never copy this package's README as a project README. Initialize only when requested, or create a particular record for a real need.

| Record and template | Owner and update trigger | Editing budget |
|---|---|---|
| [Project AGENTS.md](../templates/PROJECT_AGENTS.md) | Agent records authorized working agreements when they change; never self-grants permissions | 20 lines |
| [Project README](../templates/PROJECT_README.md) | Agent updates confirmed durable project facts or commands affected by the task | 60–100 lines or fewer |
| [Task](../templates/TASK.md) | Current agent maintains a complex/coordinated task's checklist, progress and evidence | 30–50 lines or fewer |
| [Handover](../templates/HANDOVER.md) | Current agent snapshots unfinished work crossing sessions/owners; link any task record | 20–30 lines |
| [Decisions](../templates/DECISIONS.md) | Research owner or authorized decision maker adopts; current agent records important adopted choices in any feature | 5–8 lines per entry |
| [Experiment](../templates/EXPERIMENT.md) | Research owner sets acceptance; current agent records the design and checks for a claim a paired/controlled comparison is meant to support | 20–30 lines or fewer |

Keep commands in the project README, execution evidence beside outputs, and decisions in one log. Pending proposals remain in conversation or an active task/handover. Preserve superseded decisions and link replacements. Use the existing task directory, otherwise `tasks/YYYY-MM-DD-short-name.md`. Replace stale handover state rather than appending history. Small completed tasks need no new file; do not update every record on each invocation.

The project's own AGENTS.md carries project-specific boundaries only — entry points, paths, budgets, authorization scope and the research owner. The general working rules are these files, not that one; do not copy them back into it.

## The four questions

Before stating a result in any feature, answer these:

1. What was established — fact, code-verified behavior, or assumption?
2. What was checked, and how — independent basis, tool output, or none?
3. What is the research owner's to decide — value judgement, acceptance, budget?
4. Does this need [Review](review.md) — consequential, irreversible, or entering a record others rely on?

An unresolved answer does not block stating the result; state the gap instead of guessing.

## Finish proportionately

Report the outcome, changed files where applicable, checks actually performed and remaining limits. Distinguish execution, a property verified against an independent basis, and support for a scientific claim. Read existing evidence; never rerun costly work just to fill a record. Stop when the requested outcome and relevant checks are satisfied. Recheck only for new changes, failures or unresolved concerns. Compaction or rereading alone does not require a restart. Independent validation/review is needed for consequential scientific results; ordinary tasks do not automatically spawn reviewers or additional agents.
