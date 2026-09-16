# <Project name> — Working Rules

This project follows the HydroClimMate workflow.
Integration: <native hydroclimmate skill OR explicit path to hydroclimmate/SKILL.md; choose one>

That file and the references beside it carry the general rules — evidence and reporting
standards, escalation, data semantics, grid and area weighting, validation. Do not copy
them here. This file records only what is specific to this project.

## Entry points

- Environment activation: <command or README section>
- Small run and validation commands: <commands or README section>
- Main run entry point: <command or README section>

## Boundaries

- Raw and reference locations, read-only: <paths>
- Permitted derived-output location: <path>
- Compute and retry budgets: <sample scope; runtime, memory, CPU/GPU, jobs or storage as relevant; costly retry limit>
- Submission and environment-change authorization: <approved scope>
- Research owner for scientific decisions: <name or role>

## Project-specific scientific constraints

<Only where this project narrows or overrides the general rules: a model's sign convention,
a basin mask definition, a fixed evaluation period, a required calendar. Omit if none.>

Keep this file around 20 lines. If a rule here would apply to any project in the lab, it
belongs in the workflow files instead.
