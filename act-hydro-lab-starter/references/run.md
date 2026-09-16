# Run and diagnose a model

Use for model preparation, small trials, execution, restart and operational failure diagnosis.
Scientific interpretation of completed outputs belongs to [Analyze](analyze.md).

## Consume the shared checklist

Use the five fields in [the entrypoint](../SKILL.md#shared-plan-to-execution-checklist) as the
input contract, whether supplied by a plan, a task record or the user's existing request.
Resolve only gaps affecting the next step; do not require Plan for an already defined run.

## Preflight

- Find actual project commands, environment/dependency record, inputs and configuration; do not invent model-specific flags or scheduler settings.
- Confirm input availability, versions, required variables, time/domain and expected outputs.
- Check relevant grid identifiers, dimensions, coordinates, masks and configuration compatibility; detailed spatial aggregation belongs to Analyze.
- Establish new run versus restart. Check restart time, model/configuration compatibility and output continuation behavior before resuming.
- Use explicit separate output locations and preserve raw, original and reference outputs.
- Confirm applicable runtime, memory, CPU/GPU, job-count and storage limits, plus costly retry allowance and authorization.
- Reuse valid preflight evidence; otherwise start with the smallest meaningful check. A sample pass does not validate the full run.

## Execute and diagnose within scope

- Capture the generation command, code commit and uncommitted patch/snapshot, actual configuration, input identifiers, environment, time and output paths.
- Use existing run records; otherwise a small run-info.md beside important outputs is sufficient. Include seeds, model version and HPC job IDs/resources where applicable.
- Check live jobs and existing outputs before retrying; submission timeouts are not evidence that submission failed.
- Read logs and exit status, diagnose the cause and retry only within the agreed budget. Failure count alone is not an escalation rule.
- Do not alter parameters, forcing, spin-up or other scientific definitions simply to make execution succeed.
- If a necessary scientific choice remains unresolved after inspecting existing decisions, or the next action exceeds budget/authorization or has unapproved irreversible effects, use [Plan](plan.md) for that issue.
- Follow an active run as needed for the requested outcome with bounded status checks. Do not create scheduled monitoring or duplicate jobs by default.

## Check outputs and report state

Distinguish configured/ready, submitted, running, failed, execution completed, and output
checks passed. Use scheduler/process evidence and logs; submission success proves only
submission. If completion cannot be observed, leave it pending and provide the job/log reference.

Check expected files and readable structure, time coverage, grid consistency and obvious
nonfinite or incomplete output, as relevant. Apply established model diagnostics without
claiming full scientific validation. Send interpretation or requested evaluation to Analyze.

## Finish and preserve continuity

Stop at the requested stage: submission-only requests end with confirmed submission;
completion requests require observed completion and relevant checks, or an explicit blocker.
Link run evidence from an existing task. Update README only for changed durable commands or
facts, and HANDOVER only for unfinished work crossing sessions/owners. Record important
adopted choices under the shared decision policy in any feature. Missing evidence remains
unverified; do not repeat costly work to manufacture a complete report.
