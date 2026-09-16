---
name: act-hydro-lab-starter
description: Understand hydrological research projects, discuss experiment or analysis choices, run models, and analyze hydrological data using lightweight project records. Use for project-specific scientific computation or explicit adoption of this lab workflow; not for generic editing, unrelated software work, or broad literature surveys.
---

# ACT Hydro Lab

One skill with four features, normally used by one agent. Read only the feature needed
for the current step. Do not load every reference or run all four stages in sequence.

## Establish context

- Identify the target research project; this skill's templates are not its live records.
- Check applicable project AGENTS.md instructions, including relevant directory-specific rules. Do not assume the host loaded them; do not reread instructions already available and current.
- Read relevant project README sections and an active task or handover only when needed. Inspect code or metadata to resolve stale or conflicting documentation.
- Do not submit jobs beyond authorization, overwrite existing results, or change scientific definitions without adoption. Continue within unchanged existing authorization.
- Missing documents do not authorize guessed budgets or configurations and do not block safe explanation. Ask only for missing facts that affect the next action.

## Choose the current feature

| Feature | Use when | Do not use for | Contrasting prompts |
|---|---|---|---|
| [Understand](references/understand.md) | Explain project code, model structure, inputs or associated methods | A defined execution request or broad literature survey | “Explain this runoff function” → understand; “plot its existing output” → analyze |
| [Plan](references/plan.md) | Explicit design/comparison requests; unresolved scientific choices or a budget/irreversibility boundary | Every open-ended question or routine execution | “Compare spin-up strategies” → plan; “what is spin-up in this config?” → understand; “run the agreed config” → run |
| [Run](references/run.md) | Prepare, execute, resume or diagnose model execution | Scientific interpretation of completed results | “Resume this failed job” → run; “why is runoff biased high?” → analyze |
| [Analyze](references/analyze.md) | Process, evaluate, plot or diagnose hydrological data/results | Submission of a new experiment | “Compute basin means” → analyze; “launch a calibration experiment” → run, or plan if choices remain |

Generic spelling fixes and unrelated coding need no research workflow. Honor explicit
feature requests within scope. For mixed work, choose the current objective and borrow
only missing context: a high-runoff diagnosis starts in Analyze, may need Understand,
and reaches Plan only if evidence calls for a new scientific choice or expanded scope.
Changing feature does not create another agent or grant additional execution authority.

## Shared plan-to-execution checklist

Use these same five fields in discussion and as inputs to Run or Analyze. Reuse known
answers from the request, project or existing task; do not require a separate form.

1. **Goal and scope** — outcome, included/excluded work and definitions to preserve.
2. **Inputs and selected method/configuration** — data, versions, entry point and adopted choices.
3. **Steps and output locations** — necessary actions, expected products and owners if coordinated.
4. **Resource budget and authorization** — sample scope, applicable compute/storage limits, costly retries and approved actions.
5. **Acceptance checks and pending choices** — expected checks, independent basis, tolerances, review needs and unresolved decisions with owners.

An unresolved item blocks only dependent actions. Method adoption is not authorization
for unlimited computation. Escalation to Plan can be a short discussion of one item.

## Project documentation

Templates are starting points, read only when creating or updating the corresponding
record. Merge into existing project files; never copy this package's README as a project
README. Initialize only when requested, or create a particular record for a real need.

| Record and template | Owner and update trigger | Editing budget |
|---|---|---|
| [AGENTS.md](templates/AGENTS.md) | Agent records authorized working agreements when they change; never self-grants permissions | 40–60 lines |
| [Project README](templates/PROJECT_README.md) | Agent updates confirmed durable project facts or commands affected by the task | 60–100 lines or fewer |
| [Task](templates/TASK.md) | Current agent maintains a complex/coordinated task's checklist, progress and evidence | 30–50 lines or fewer |
| [Handover](templates/HANDOVER.md) | Current agent snapshots unfinished work crossing sessions/owners; link any task record | 20–30 lines |
| [Decisions](templates/DECISIONS.md) | Research owner or authorized decision maker adopts; current agent records important adopted choices in any feature | 5–8 lines per entry |

Keep commands in the project README, execution evidence beside outputs, and decisions
in one log. Pending proposals remain in conversation or an active task/handover. Preserve
superseded decisions and link replacements. Use the existing task directory, otherwise
`tasks/YYYY-MM-DD-short-name.md`. Replace stale handover state rather than appending history.
Small completed tasks need no new file; do not update every record on each invocation.

## Finish proportionately

Report the outcome, changed files where applicable, checks actually performed and remaining
limits. Distinguish execution, a property verified against an independent basis, and support
for a scientific claim. Read existing evidence; never rerun costly work just to fill a record.
Stop when the requested outcome and relevant checks are satisfied. Recheck only for new
changes, failures or unresolved concerns. Compaction or rereading alone does not require a
restart. Independent validation/review is needed for consequential scientific results;
ordinary tasks do not automatically spawn reviewers or additional agents.
