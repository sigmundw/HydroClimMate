# Understand the project

Use for project-specific explanation and learning. The routing and document policy in
[the skill entrypoint](../SKILL.md) apply; no execution stage is implied.

## Start from the question

- Identify what must be explained: a method, variable, function, configuration or data path.
- Read the relevant project overview, entry point and definitions, not the entire repository.
- Follow only the calls and transformations needed to answer the question.
- Inspect data headers or a small sample when documentation alone cannot establish semantics.
- Separate documented intent, observed implementation and unresolved assumptions.

## Trace the scientific meaning

- Connect inputs, units, dimensions, state/flux definitions and outputs to the relevant code.
- Identify configuration switches and assumptions that change the answer.
- Read a linked method paper or authoritative documentation only when the explanation needs it.
- Cite the code location or source behind a material claim; do not turn project learning into a literature survey.
- Use inexpensive read-only inspection; importing code can execute side effects, so inspect before using it as a probe.

## Boundaries and transitions

- “Explain this runoff function” stays here until its behavior and assumptions are clear.
- “Why are these completed results too high?” belongs primarily to [Analyze](analyze.md); contribute only the missing code understanding.
- “Which experimental design should we choose?” belongs to [Plan](plan.md).
- Do not install dependencies, edit methods or launch simulations merely to understand them.
- If evidence is missing, identify exactly what would resolve it. Continue independent safe investigation rather than guessing.

## Answer and stop

Give a concise explanation with the relevant files or sources, confirmed facts, and any
unknowns that affect the answer. No fixed report or comprehensive project map is required.
Stop once the current question is answered or a concrete evidence gap is established.

Update the project README only when the task calls for preserving a confirmed durable fact.
Do not create learning notes by default. If the researcher adopts an important choice during
this discussion, the current agent records it under the shared decision policy; explanation
or an agent recommendation alone is not adoption.
