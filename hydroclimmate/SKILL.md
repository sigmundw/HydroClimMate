---
name: hydroclimmate
description: Understand, plan, run and analyze hydrological, groundwater, land-surface and ice-sheet modeling work. Supports targeted offline questions about HRLDAS/Noah-MP, WRF-Urban, CTSM, RBM, ISSM, VIC, mizuRoute and MODFLOW without requiring a project. Covers experiment design, spin-up and restart, calibration choices, forcing data, HPC job submission and failure diagnosis, model-output analysis — runoff and streamflow, basin and catchment means, water balance closure and ice mass budgets, netCDF variable and unit semantics, grid, mesh and area weighting, time, interval and calendar semantics, and missing-data handling — and independent review of a consequential result before it is recorded or acted on. Not for generic editing, textbook questions unrelated to a documented model, manuscript writing, or broad literature surveys.
---

# HydroClimMate

HydroClimMate v0.9 — developed by ACT Hydro Lab.

One workflow with five features, normally used by one agent. Read only the feature needed for the current step. Do not load every reference or run all five in sequence.

Read [references/core.md](references/core.md) first for context checks, the shared plan-to-execution checklist, project-record policy and stopping rules. Then read the primary feature below; supplement it only for a concrete dependency.

## Choose the current feature

| Feature | Use when | Do not use for | Contrasting prompts |
|---|---|---|---|
| [Understand](references/understand.md) | Explain project code or targeted questions about documented models, inputs and methods | A defined execution request or broad literature survey | “Explain this runoff function” → understand; “plot its existing output” → analyze |
| [Plan](references/plan.md) | Explicit design/comparison requests; unresolved scientific choices or a budget/irreversibility boundary | Every open-ended question or routine execution | “Compare spin-up strategies” → plan; “what is spin-up in this config?” → understand; “run the agreed config” → run |
| [Run](references/run.md) | Prepare, execute, resume, verify an existing input archive before running, or diagnose model execution | Scientific interpretation of completed results | “Resume this failed job” → run; “why is runoff biased high?” → analyze; “are the boundary files all in place for the next submission?” → run (preflight) |
| [Analyze](references/analyze.md) | Process, evaluate, plot or diagnose hydrological data/results | Submission of a new experiment | “Compute basin means” → analyze; “launch a calibration experiment” → run, or plan if choices remain |
| [Review](references/review.md) | A consequential or irreversible result needs an independent check before it is recorded or acted on | A routine calculation already checked, or reviewing the same unchanged result again | “Have a fresh session check this before it goes in the report” → review; “try this again with a different setting” → run |

Generic spelling fixes and unrelated coding need no research workflow. Honor explicit feature requests within scope. For mixed work, choose the current objective and borrow only missing context: a high-runoff diagnosis starts in Analyze, may need Understand, and reaches Plan only if evidence calls for a new scientific choice or expanded scope. Changing feature does not create another agent or grant additional execution authority.

## When a claim needs checking

Before stating a consequential result, prefer a deterministic tool over prose: see [tools/](tools/README.md) for checks that print evidence before any verdict. When the result is consequential enough that a wrong check also matters, use [Review](references/review.md) — a fresh agent or session, not the same one continuing.
