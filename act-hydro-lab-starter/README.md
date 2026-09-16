# ACT Hydro Lab: Computational Research Skill

Version 0.4 — for lab trials.

One skill, four features, and lightweight project documentation for hydrological model
runs and data analysis. Normally one agent handles the task and loads only relevant detail.

## Features

The [skill entrypoint](SKILL.md) selects the current feature; these are not mandatory stages.

| Feature | Purpose | Example |
|---|---|---|
| [Understand](references/understand.md) | Explain project code, data and associated methods | Explain how runoff is calculated |
| [Plan](references/plan.md) | Discuss a real design choice or an execution boundary | Compare spin-up strategies within the budget |
| [Run](references/run.md) | Prepare, execute, resume and diagnose model runs | Run the agreed configuration |
| [Analyze](references/analyze.md) | Process, evaluate, plot and investigate results | Diagnose high simulated runoff |

A clear execution request skips Plan. An ordinary explanation is not a planning session.
For overlapping requests, follow the current objective and borrow only missing context.
Generic editing and unrelated coding do not need this research workflow.

Plan, Run and Analyze share five fields: goal/scope; inputs and selected method/configuration;
steps/output locations; resource budget/authorization; acceptance checks/pending choices.
These can live in the conversation; a separate task file is optional.

## Adopt in an existing project

Keep this entire skill directory together so references and templates remain available.
This repository supplies the skill; creating these files does not install it into an agent's
skill registry or grant execution permissions. Its name is `act-hydro-lab-starter`.

When adopting the documentation, preserve the project's layout and existing agreements:

1. Merge [AGENTS.md](templates/AGENTS.md) into project rules and fill in authorized boundaries.
2. Merge [PROJECT_README.md](templates/PROJECT_README.md) into the project's README, including actual data definitions and small run/check commands.
3. Try one inexpensive, well-defined task. Add optional records only when needed.

Do not copy this package README into the research project or overwrite existing files.
Replace template placeholders with evidence or Unknown; omit irrelevant fields. Missing
documents alone do not trigger initialization, and template values are never authorization.
Use version control for code and filesystem/tool permissions to protect raw/reference data.

## Project documentation

| Record | Single purpose and update trigger | Size budget |
|---|---|---|
| [AGENTS.md](templates/AGENTS.md) | Working agreements, authorization and resource boundaries when changed | 40–60 lines |
| [README.md](templates/PROJECT_README.md) | Confirmed project facts, data semantics and actual commands when affected | 60–100 lines or fewer |
| [TASK.md](templates/TASK.md) | Shared checklist, progress and evidence for complex/coordinated work | 30–50 lines or fewer |
| [HANDOVER.md](templates/HANDOVER.md) | Current snapshot of unfinished work crossing sessions/owners | 20–30 lines |
| [DECISIONS.md](templates/DECISIONS.md) | Important adopted choices, rationale and decision maker | 5–8 lines per entry |

The current agent maintains affected records; the researcher or authorized decision maker
adopts scientific choices. This applies in every feature. Pending proposals are not adopted
decisions. Keep superseded decisions with replacement links. A handover links task evidence
instead of copying it; a small completed task needs no new document.

Store execution evidence beside results using existing logs, or a small run-info.md for
important outputs. Identify inputs, actual configuration, code state including uncommitted
changes, environment, command, outputs and checks; include job IDs/seeds where applicable.
Read existing evidence first. Missing evidence remains unverified, not a reason for costly reruns.

## Scientific and cost boundaries

Check only what the task affects. [Analyze](references/analyze.md) contains the spatial
weighting and time-processing guidance: regular degree grids need appropriate area weights;
confirmed equal-area cells must not receive extra latitude weighting; curvilinear/mesh
geometry alone does not establish equal area. Run checks output grid consistency as well.

Do not conflate execution success, a numerically verified property and support for a scientific
claim. Use independent validation/review for consequential results. Keep compute and retry
budgets explicit, proceed within existing authorization, and stop after acceptance is met.

Prefer replacing an ineffective rule to adding another paragraph. Size budgets are not
minimum lengths; link existing methods, configuration and evidence before expanding prose.
This release provides instructions and templates, not a scheduler, permission enforcement
system or verified implementation of a particular hydrological model.
