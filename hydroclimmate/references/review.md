# Review — independent check of a claim

Use when a result is consequential (feeds a decision, a paper or another researcher's work), an action was irreversible, or a claim is about to enter a record others will rely on. Do not use it for a routine calculation, a quick exploratory question, or as a substitute for checking your own work before reporting it — Review is added scrutiny, not a replacement for the executor's own checks under [core.md](core.md#finish-proportionately).

## When Review is proportionate

- A scientific claim will be recorded (DECISIONS.md, a paper, a handover another owner will act on) and being wrong is costly to detect later.
- An experiment's acceptance conditions in [EXPERIMENT.md](../templates/EXPERIMENT.md) were met, or a controlling variable's expected response (paired-response) was checked, and the result will be used to choose between real options.
- A physics option, configuration change or dataset switch produced a surprising or convenient result and no independent check has run yet.

Not proportionate: an ordinary explanation, a plot made to look at the data, a small calculation with an independent basis already applied, or repeated review of the same unchanged result. Reviewing every routine step raises the cost of the checked path until people route around it — see [core.md](core.md#finish-proportionately).

## How to call it

Review is a fresh agent or a new session, not the same conversation continuing under a different hat — a new subagent or a new session invoked for review only, whichever the current tool calls it. The tool matters less than the property: the reviewer must not have produced the work, must not share the executor's running context, and must not be told what the executor concluded before forming its own answer.

## What the reviewer receives — and must not receive

Give the reviewer: the goal or claim being checked, the experiment record (or the relevant fields from the [shared checklist](core.md#shared-plan-to-execution-checklist)), adopted decisions, the raw artefacts (data, logs, figures) and any check reports from `tools/hcm_check.py`.

Do not give the reviewer: the executor's narrative, summary or rationale for why the result is correct. A written account of what happened is the executor's claim, not evidence for it, and handing it over invites the reviewer to grade the story instead of the artefacts. Use [`tools/hcm_review_packet.py`](../tools/README.md) to assemble the packet — it refuses free-text summary-style inputs for exactly this reason.

## Authority

The reviewer has no authority to modify project files, re-run a job, or recover a failed run. Its output is an assessment, not an action. If the reviewer believes something needs to change, that goes back to the research owner or the executor's next task — never as a direct edit made under the reviewer's own authority.

## Output: three states per claim

For each claim under review, the reviewer answers exactly one of:

- **Supported** — the packet's evidence supports the claim; cite where.
- **Contradicted** — the packet's evidence contradicts the claim; cite where.
- **Insufficient evidence** — the packet does not contain enough to decide.

A vague or general endorsement is not one of these three states. Every answer names a specific file, variable, table row or line — the same evidence-location discipline `hcm_check.py` uses when it prints observations before a verdict.

## Deterministic violations are not overridden by prose

If a `hcm_check.py` report in the packet shows a VIOLATED verdict, no amount of surrounding narrative — the executor's, the reviewer's, or anyone's — changes that verdict. The reviewer may still judge the violation immaterial to the specific claim being reviewed, but must say so explicitly and separately from the verdict itself; it does not get to disappear.

## Disagreement and final acceptance

The reviewer and the executor will sometimes disagree, and the reviewer and the research owner will sometimes disagree with each other. Record both positions rather than resolving them by whoever wrote last. Final acceptance of a scientific claim belongs to the research owner, per [core.md](core.md#finish-proportionately) — Review informs that decision, it does not make it.

## Same-model reviewers share blind spots

A reviewer built from the same model and similar prompting as the executor is better than no review, but it tends to miss the same classes of error the executor missed, for the same reasons. Treat agreement from a same-model reviewer as weaker evidence than agreement from a materially different setup (a different model, a person, or an independent deterministic check), and say which kind of review actually happened when reporting the result.

## Using `tools/hcm_review_packet.py`

Run it with the goal file, the experiment record, any decision records, artefact paths and check-report files; it writes a packet directory and a `MANIFEST.json` listing exactly what is included, plus the reviewer instructions above. It refuses `--summary` or similarly named free-text options outright — put anything factual that would have gone there into the experiment record or a decision entry instead. See [tools/README.md](../tools/README.md) for usage and what it does not cover.

## Assembling a packet by hand

When no tool is available, keep the same separation rule: collect the goal, experiment record, decisions and raw artefacts and check outputs into one place, list exactly what you included, and add no account of what happened or why it is correct. Give the reviewer that list, the files it points to, and the same instructions above — three-state answers with evidence locations, no authority to modify or re-run anything, disagreement escalated to the research owner. What matters is separating evidence from the executor's narrative, not which tool enforces it.
