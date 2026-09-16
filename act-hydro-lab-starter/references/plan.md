# Discuss a model or analysis plan

Use for explicit design/comparison requests or a consequential unresolved choice discovered
in Run or Analyze. A factual question or a clear execution request does not need this feature.

## Establish the actual decision

- Read existing project facts, configuration, adopted decisions and available evidence first.
- Ask only for goals, scientific choices or constraints that cannot be established from them.
- Discuss the few choices that materially change the result, cost or feasibility.
- Offer a small number of real alternatives, a recommendation and the evidence or limitation behind it.
- Resolve one blocking choice without replanning an otherwise settled task.

## Tailor the discussion

For model work, consider the requested experiment, control/baseline, forcing and parameters,
time/domain, spin-up or restart basis, resource budget, outputs and acceptance checks.
Read [Run](run.md) only if its execution details matter to the decision.

For analysis, establish the target quantity, input selection, spatial/temporal support,
aggregation or evaluation method, uncertainty and independent validation basis.
Read [Analyze](analyze.md) when data semantics or grid treatment affect the choice.

A missing spin-up value is not automatically a new decision: check the existing setup and
method first. If its choice remains unresolved and affects the experiment, ask the research
owner before dependent execution. Likewise, pause before exceeding budget or taking an
irreversible action; do not infer approval from a recommended plan.

## Produce the shared checklist

Use the five fields defined in [the entrypoint](../SKILL.md#shared-plan-to-execution-checklist):
Goal and scope; Inputs and selected method/configuration; Steps and output locations;
Resource budget and authorization; Acceptance checks and pending choices.

Keep known fields brief or link their existing source. Label proposed choices as proposed;
identify the decision owner and dependent steps. If the user is still exploring, finish with
options and unknowns instead of pretending that an executable plan has been agreed.

## Records and transition

- Keep an ordinary discussion in the conversation. Use [TASK.md](../templates/TASK.md) only for complex or coordinated work, updating the same record.
- On adoption, the current agent records important choices in DECISIONS.md with the authorized decision maker and evidence; never log a proposal as adopted.
- Discussion permits inexpensive read-only investigation, not job submission, environment changes or a full analysis run.
- When execution is requested or already authorized for the selected scope, pass the same checklist to Run or Analyze without asking again about settled items.
- Stop when the requested comparison or actionable plan is complete, or the remaining decision is clearly presented. Do not add an obligatory planning ceremony to later routine work.
