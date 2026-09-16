# HydroClimMate — agent working rules

Entry point for Codex and other tools that read AGENTS.md. Claude Code uses SKILL.md,
which carries the same routing table.

HydroClimMate v0.5 — developed by ACT Hydro Lab.

One workflow with four features, normally used by one agent. Read only the feature needed
for the current step. Do not load every reference or run all four stages in sequence.

Read [references/core.md](references/core.md) first for context checks, the shared
plan-to-execution checklist, project-record policy and stopping rules. Then read the one
feature file selected below.

<!-- ROUTING TABLE: duplicated by design in SKILL.md and AGENTS.md. Keep both in sync. -->
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
<!-- END ROUTING TABLE -->
