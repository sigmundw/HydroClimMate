# HydroClimMate

Version 0.6 — for lab trials. Developed by ACT Hydro Lab.

An agent workflow for hydrological, land-surface and ice-sheet modeling work: one workflow, four
features, and lightweight project records. Normally one agent handles the task and loads
only the detail the current step needs.

Works as a native skill in **Claude Code and Codex**, or through explicit `AGENTS.md` integration.

## Features

The entry point selects the current feature; these are not mandatory stages.

| Feature | Purpose | Example |
|---|---|---|
| [Understand](hydroclimmate/references/understand.md) | Explain project code, data and associated methods | Explain how runoff is calculated |
| [Plan](hydroclimmate/references/plan.md) | Discuss a real design choice or an execution boundary | Compare spin-up strategies within the budget |
| [Run](hydroclimmate/references/run.md) | Prepare, execute, resume and diagnose model runs | Run the agreed configuration |
| [Analyze](hydroclimmate/references/analyze.md) | Process, evaluate, plot and investigate results | Diagnose high simulated runoff |

A clear execution request skips Plan. An ordinary explanation is not a planning session.
Generic editing and unrelated coding do not need this workflow at all.

Plan, Run and Analyze share five fields — goal/scope; inputs and selected
method/configuration; steps/output locations; resource budget/authorization; acceptance
checks/pending choices. These can live in the conversation; a task file is optional.

## Install

The package is `hydroclimmate/`. Everything else in this repository is documentation about it.

**Claude Code** — symlink it so a `git pull` updates every project at once:

```bash
mkdir -p ~/.claude/skills
ln -s "$PWD/hydroclimmate" ~/.claude/skills/hydroclimmate
```

For a shared project checkout instead of your personal skills, link it into that project's
`.claude/skills/` directory. Confirm it worked by starting a new session: `hydroclimmate`
should appear in the available skills, and `/hydroclimmate` should be invocable.

**Codex native skill** — from this repository root, with no existing destination:

```bash
mkdir -p ~/.agents/skills
ln -s "$PWD/hydroclimmate" ~/.agents/skills/hydroclimmate
```

For project scope, use that project's `.agents/skills/` instead. Verify discovery in the
skill selector; restart if the change is not visible. See the [official skill guide](https://learn.chatgpt.com/docs/build-skills).

**Explicit AGENTS.md integration** — an alternative for a project-wide workflow. Copy the
package directory into the project and instruct its root AGENTS.md to read
`hydroclimmate/AGENTS.md` for applicable work. A Git submodule contains the **whole repository**:
if checked out at `vendor/HydroClimMate`, the package entry is
`vendor/HydroClimMate/hydroclimmate/AGENTS.md`, not `vendor/HydroClimMate/AGENTS.md`.
Resolve paths relative to the target project. Choose one primary integration path to avoid
reading both entrypoints. Do not overwrite an existing skill destination.

## Adopt in a research project

Keep the package directory together so references and templates stay reachable. Installing
the files does not grant execution permissions.

1. Merge [PROJECT_AGENTS.md](hydroclimmate/templates/PROJECT_AGENTS.md) into the project's
   `AGENTS.md` and fill in the authorized boundaries — paths, budgets, entry points, owner.
2. Merge [PROJECT_README.md](hydroclimmate/templates/PROJECT_README.md) into the project's
   `README.md`, including actual data definitions and small run and check commands.
3. Try one inexpensive, well-defined task. Add optional records only when needed.

Do not copy this README into the research project. Replace template placeholders with
evidence or `Unknown`, and omit irrelevant fields. Use version control for code, and
filesystem or tool permissions to protect raw and reference data — these documents describe
intent and cannot enforce it.

## Offline model knowledge

[The model index](hydroclimmate/references/models/index.md) routes directly to a topic.
Targeted model questions need no project. Content is locally readable; source links support
verification and updates rather than being a prerequisite for every answer.

| Knowledge pack | Coverage |
|---|---|
| HRLDAS/Noah-MP | Offline driver, physics structure, forcing, initialization and output semantics |
| WRF-Urban | Urban schemes, setup dependencies, grid and urban-output interpretation |
| CTSM | Cases/configuration, initialization, subgrid structure and history output |
| RBM | UW-Hydro candidate implementation; lab identity remains unconfirmed |
| ISSM | Ice flow, mesh, stress balance, transient evolution and mass-change analysis |

VIC and mizuRoute retain general workflow support but have no dedicated knowledge pack.
These are concise, source-attributed explanations, not complete parameter catalogs or
validated lab configurations. Unknown versions/interfaces require local evidence or an
explicit gap. Lab settings remain in project records. No models or skills are installed by
adding these documents. See [knowledge evaluation](evals/knowledge-eval.md) for coverage and limits.

## What the researcher does

The workflow constrains the agent. These are the parts it cannot do for you.

- **Read the diff, not the summary.** The summary is the agent's account of its own work.
  A well-organized report is not evidence, and length is not rigor.
- **Check one number by hand.** For any result you intend to use, reproduce a single value
  independently: one cell, one month, one basin. This finds more errors per minute spent
  than any other habit available to you.
- **Ask what was actually run.** "Which command produced this, and where is its output?"
  An agent that cannot answer did not verify what it claimed to verify.
- **Own the scientific choices.** Units, sign conventions, time windows, masks, thresholds
  and evaluation definitions are yours to adopt. An agent's proposal, however well argued,
  remains a proposal until you adopt it.
- **Notice when you have stopped reading.** Approving without inspection is the failure this
  workflow exists to prevent, and it arrives gradually, after a stretch of work that
  happened to be correct.

Trust in an agent's output should track the checks you ran, not the number of times it was
previously right.

## Trial log

Keep a running record while the workflow is in trial: what the agent got wrong, what these
documents failed to say, and where a person had to step in. That record is the input to the
next version. Impressions gathered at the end of a term are not, and neither is the absence
of remembered disasters.

## Scope

This release provides instructions and templates — not a scheduler, a permission enforcement
system, or a verified implementation of any hydrological model. Do not conflate execution
success, a numerically verified property, and support for a scientific claim. Use independent
validation and review for consequential results.

Prefer replacing an ineffective rule to adding another paragraph. Size budgets are not
minimum lengths; link existing methods, configuration and evidence before expanding prose.
