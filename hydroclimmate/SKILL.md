---
name: hydroclimmate
description: Understand, plan, run and analyze hydrological and land-surface modeling work using lightweight project records. Covers explaining model code, configuration and data semantics; discussing experiment design such as spin-up, restart, forcing and calibration choices; preparing, submitting, resuming and diagnosing model runs including HPC batch jobs; and processing or evaluating results — runoff, streamflow, basin and catchment means, water balance, netCDF and forcing data, grid and area weighting, time semantics and missing-data handling. Applies to models including VIC, mizuRoute, WRF-urban, HRLDAS/Noah-MP and CTSM. Use for project-specific scientific computation or explicit adoption of this lab workflow; not for generic editing, unrelated software work, or broad literature surveys.
---

# HydroClimMate

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
