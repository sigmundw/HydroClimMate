# HydroClimMate

Version 0.9 — for lab trials. Developed by ACT Hydro Lab.

An agent workflow for hydrological, groundwater, land-surface and ice-sheet modeling work: one workflow, five features, and lightweight project records. Normally one agent handles the task and loads only the detail the current step needs.

Works as a native skill in **Claude Code and Codex**.

## Features

The entry point selects the current feature; these are not mandatory stages.

| Feature | Purpose | Example |
|---|---|---|
| [Understand](hydroclimmate/references/understand.md) | Explain project code, data and associated methods | Explain how runoff is calculated |
| [Plan](hydroclimmate/references/plan.md) | Discuss a real design choice or an execution boundary | Compare spin-up strategies within the budget |
| [Run](hydroclimmate/references/run.md) | Prepare, execute, resume and diagnose model runs | Run the agreed configuration |
| [Analyze](hydroclimmate/references/analyze.md) | Process, evaluate, plot and investigate results | Diagnose high simulated runoff |
| [Review](hydroclimmate/references/review.md) | Independently check a consequential or irreversible result before it is recorded or acted on | Have a fresh session check this before it goes in the report |

A clear execution request skips Plan. An ordinary explanation is not a planning session. Generic editing and unrelated coding do not need this workflow at all.

Plan, Run and Analyze share five fields — goal/scope; inputs and selected method/configuration; steps/output locations; resource budget/authorization; acceptance checks/pending choices. These can live in the conversation; a task file is optional.

## Install

The package is `hydroclimmate/`. Everything else in this repository is documentation about it.

**Claude Code** — symlink it so a `git pull` updates every project at once:

```bash
mkdir -p ~/.claude/skills
ln -s "$PWD/hydroclimmate" ~/.claude/skills/hydroclimmate
```

For a shared project checkout instead of your personal skills, link it into that project's `.claude/skills/` directory. Confirm it worked by starting a new session: `hydroclimmate` should appear in the available skills, and `/hydroclimmate` should be invocable.

**Codex native skill** — from this repository root, with no existing destination:

```bash
mkdir -p ~/.agents/skills
ln -s "$PWD/hydroclimmate" ~/.agents/skills/hydroclimmate
```

For project scope, use that project's `.agents/skills/` instead. Verify discovery in the skill selector; restart if the change is not visible. See the [official skill guide](https://learn.chatgpt.com/docs/build-skills).

**One shared entrypoint:** both tools read the same `hydroclimmate/SKILL.md`; there is no Claude-specific versus Codex-specific workflow. See the [Claude Code skill guide](https://code.claude.com/docs/en/skills) and the [Codex skill guide](https://learn.chatgpt.com/docs/build-skills).

For explicit project integration, the project's instructions can point directly to `hydroclimmate/SKILL.md`. A submodule contains the whole repository: if checked out at `vendor/HydroClimMate`, use `vendor/HydroClimMate/hydroclimmate/SKILL.md`. Choose one primary integration method; do not overwrite an existing skill destination. The research project's own `AGENTS.md` (a project's working-agreement file, not part of this package) still holds its local paths, budgets and constraints.

## Adopt in a research project

Keep the package directory together so references and templates stay reachable. Installing the files does not grant execution permissions.

1. Merge [PROJECT_AGENTS.md](hydroclimmate/templates/PROJECT_AGENTS.md) into the project's `AGENTS.md` and fill in the authorized boundaries — paths, budgets, entry points, owner.
2. Merge [PROJECT_README.md](hydroclimmate/templates/PROJECT_README.md) into the project's `README.md`, including actual data definitions and small run and check commands.
3. Try one inexpensive, well-defined task. Add optional records only when needed.

Do not copy this README into the research project. Replace template placeholders with evidence or `Unknown`, and omit irrelevant fields. Use version control for code, and filesystem or tool permissions to protect raw and reference data — these documents describe intent and cannot enforce it.

## Offline model knowledge

[The model index](hydroclimmate/references/models/index.md) routes directly to a topic. Targeted model questions need no project. Content is locally readable; source links support verification and updates rather than being a prerequisite for every answer.

Each pack declares a `depth`: **reference** means source-extracted catalogs, line-cited against a pinned checkout, cross-checked against real output; **outline** means orientation from public documentation, not source-verified — confirm a version-sensitive detail against your own checkout before relying on it. See [SCHEMA.md](hydroclimmate/references/models/SCHEMA.md) for the full format.

| Knowledge pack | Depth | Coverage |
|---|---|---|
| HRLDAS/Noah-MP | reference | Offline driver, physics structure, forcing, initialization and output semantics |
| WRF-Urban | outline | Urban schemes, setup dependencies, grid and urban-output interpretation |
| CTSM | outline | Cases/configuration, initialization, subgrid structure and history output |
| RBM | outline | UW-Hydro candidate implementation; lab identity remains unconfirmed |
| ISSM | outline | Ice flow, mesh, stress balance, transient evolution and mass-change analysis |
| VIC | outline | Classic/Image drivers, land runoff, subgrid output and routing handoff |
| mizuRoute | reference | Control file, network and runoff contract, five routing schemes, lakes, restart and output semantics |
| MODFLOW | outline | MODFLOW 6 groundwater flow, discretization, boundaries, heads and budgets; legacy versions distinguished |

These are concise, source-attributed explanations, not complete parameter catalogs or validated lab configurations. Unknown versions/interfaces require local evidence or an explicit gap. Lab settings remain in project records. No models or skills are installed by adding these documents. See [knowledge evaluation](evals/knowledge-eval.md) for coverage and limits.

Source reviews older than 180 days trigger a reminder, not automatic invalidation. Offline work continues where evidence is sufficient; only unsupported version-sensitive steps pause. See the [freshness policy](hydroclimmate/references/core.md#source-freshness). A successful link check does not establish accuracy or justify changing the source-review date.

## Tools

`hydroclimmate/tools/` holds optional, executable checks: `hcm_lookup.py` and `hcm_check.py` confront a model pack's declarations with actual NetCDF output instead of trusting prose; `hcm_review_packet.py` assembles exactly what an independent reviewer may see. See [tools/README.md](hydroclimmate/tools/README.md) for what each one does and how to run it without any agent.

A `depth: reference` pack's generated catalogs are reproducible, not hand-typed:

```bash
python3 hydroclimmate/tools/extract_pack.py all --source-root <pinned-checkout> \
  --out-dir hydroclimmate/references/models/hrldas-noahmp/catalogs
python3 hydroclimmate/tools/validate_catalogs.py \
  --pack-dir hydroclimmate/references/models/hrldas-noahmp \
  --ldasout <one .LDASOUT_DOMAIN1> --restart <one RESTART.*> --ldasin <one .LDASIN_DOMAIN1> \
  --check-kind-sample --apply
```

Validate any pack (links/anchors, structured-layer facts, private-string and Markdown-formatting scans, and — with `--source-root`, for a `depth: reference` pack — citation and fresh-build checks against the pinned source):

```bash
python3 evals/check_knowledge.py [--source-root <pinned-checkout>] [--network]
```

## License and citation

MIT License; see [LICENSE](LICENSE). To cite this repository:

> ACT Hydro Lab. *HydroClimMate* (v0.9). https://github.com/sigmundw/HydroClimMate

Indexing failure knowledge by symptom, and stating a checkable data-interface contract for a knowledge pack, are ideas learned from KISS (arXiv 2605.17856v1); this repository's own schemas, file names, field names and content are not copied from that project.

## What the researcher does

The workflow constrains the agent. These are the parts it cannot do for you.

- **Read the diff, not the summary.** The summary is the agent's account of its own work. A well-organized report is not evidence, and length is not rigor.
- **Check one number by hand.** For any result you intend to use, reproduce a single value independently: one cell, one month, one basin. This finds more errors per minute spent than any other habit available to you.
- **Ask what was actually run.** "Which command produced this, and where is its output?" An agent that cannot answer did not verify what it claimed to verify.
- **Own the scientific choices.** Units, sign conventions, time windows, masks, thresholds and evaluation definitions are yours to adopt. An agent's proposal, however well argued, remains a proposal until you adopt it.
- **Notice when you have stopped reading.** Approving without inspection is the failure this workflow exists to prevent, and it arrives gradually, after a stretch of work that happened to be correct.

Trust in an agent's output should track the checks you ran, not the number of times it was previously right.

## Trial log

Keep a running record while the workflow is in trial: what the agent got wrong, what these documents failed to say, and where a person had to step in. That record is the input to the next version. Impressions gathered at the end of a term are not, and neither is the absence of remembered disasters.

## Scope

This release provides instructions and templates — not a scheduler, a permission enforcement system, or a verified implementation of any hydrological model. Do not conflate execution success, a numerically verified property, and support for a scientific claim. Use independent validation and review for consequential results.

Prefer replacing an ineffective rule to adding another paragraph. Size budgets are not minimum lengths; link existing methods, configuration and evidence before expanding prose.
