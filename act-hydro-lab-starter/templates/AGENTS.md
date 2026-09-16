# ACT Hydro Lab — Project Working Rules

Harness version: 0.4

## Project entry points and boundaries

- Environment, small run and validation commands: <README section>
- Main run entry point: <README section>
- Raw and reference locations, read-only: <paths>
- Permitted derived-output location: <path>
- Compute and retry budgets: <sample scope; runtime, memory, CPU/GPU, jobs or storage as relevant; costly retry limit>
- Submission and environment-change authorization: <approved scope>
- Research owner for scientific decisions: <name or role>

## Working approach

- Before substantial work, read relevant README sections and any active handover; follow links only as needed.
- Inspect relevant code and data metadata. Treat documentation as potentially outdated and report conflicts with evidence.
- Preserve repository conventions; make the smallest useful change and avoid unrelated refactoring or dependencies.
- Define the outcome, scope and acceptance check before substantial work; a short task request is sufficient for routine work.
- Use one implementation agent. Delegate only when explicitly requested or authorized; establish ownership and separate output paths first.

## Scientific integrity and validation

- Distinguish facts, hypotheses and validated findings. Investigate unexpected results before changing methods.
- Preserve agreed units, signs, time windows, calendars, masks, thresholds, control volumes and metric definitions. Scientific changes require research-owner adoption; routine implementation within agreed scope proceeds autonomously.
- Check affected units, dimensions, coordinates, time semantics, missing values and aggregation weights.
- Before spatial analysis, verify grid/mesh geometry, cell/node values and the area basis. Never assume curvilinear means equal-area or add latitude weighting to confirmed equal-area cells; preserve coverage and missing-data semantics.
- Validate numerical changes against independent cases or physical/numerical properties where applicable; state tolerance rationale and limitations.
- Do not adjust tests or references merely to accept new results. Validate intentional baseline changes; add meaningful checks for changed reusable logic.
- Keep final analysis reproducible from a documented entry point; notebooks must run in order from a clean kernel.
- Obtain independent validation and review for core method changes, important scientific results and key publication outputs.

## Execution and escalation

- Preserve raw data, original model outputs and reference results; use explicit separate locations for new runs. Never commit credentials; respect data access restrictions.
- Establish resource budgets, output locations and authorization before costly runs, batch submissions, shared-data or environment changes. Reuse unchanged existing authorization.
- Start with a small relevant check when practical. Continue inexpensive diagnosis within budget; do not stop solely because a check failed twice.
- Ask when a necessary data definition remains ambiguous, a scientific choice must change, or further work would exceed authorized scope or budget. Investigate contradictions with recorded decisions before proposing changes.
- Capture run evidence during execution: command, inputs, actual configuration, code state including uncommitted changes, environment, outputs, checks and applicable job IDs or seeds.
- Read existing logs first. Mark missing evidence unverified; do not rerun costly work just to fill a report. Repeat only necessary checks within budget.
- Finish when acceptance and relevant checks are satisfied. Repeat validation or review only for new changes, failures or unresolved concerns.

## Reporting and continuity

- Distinguish Ran (executed), Verified (a named property checked against an independent basis), and Supported (evidence bears on a scientific claim with limitations). Sample checks do not validate a full run.
- Report outcome and changed files, actual checks with evidence locations, failures or abandoned checks, and remaining limitations. Keep it short; never invent execution facts.
- Small completed tasks need no new document. Update only facts that changed, in their existing location; link commands and logs instead of copying them.
- Use HANDOVER.md only for unfinished work crossing sessions or owners. Keep a current snapshot, ideally 20–30 lines; if TASK.md owns the details, link it.
- Continue after context compaction or rereading when the task remains clear. Hand over when the objective changes, another person takes over, or context contradictions cannot be resolved.
- In any feature, the research owner or authorized decision maker adopts important choices; the current agent records them in DECISIONS.md, ideally 5–8 lines each. Keep proposals in conversation or a task; preserve superseded entries and link replacements.
- Keep this file around 40–60 lines. Remove repetition before extending it; preserve necessary scientific constraints.
