# Routing probe results — 2026-09-16, HydroClimMate v0.5

Method: in-session subagents, each given an empty working directory and the raw researcher
request, told to consult whatever guidance was available and to stop once oriented, then to
report the files they read and the feature they selected. See README.md for why the
`claude -p` harness could not be used and what this method can and cannot measure.

Expected trace: `SKILL.md → references/core.md → references/<one feature>.md`.
Historical v0.5 criterion: a second feature read was counted as failure.
**v0.6 correction:** judge the primary feature and the purpose of additional reads;
Plan and Analyze explicitly allow needed cross-feature context. The observations below
are retained, not rerun or re-scored.

| # | Request | Difficulty | Expected | Selected | Trace | Result |
|---|---|---|---|---|---|---|
| A | runoff 40% high vs USGS gauge | easy (restates table) | Analyze | Analyze | core → analyze | pass |
| B | mizuRoute offline vs online coupling for low-flow skill | **hard** | Plan | Plan | core → plan | pass |
| C | water balance closure on HRLDAS output | **hard** | Analyze | Analyze | core → analyze | pass |
| D | write the methods section on our VIC calibration | negative near-miss | *no fire* | *did not fire* | went to `yifan-help-me-revise` | pass |

## Observations

**The hardest negative discriminated correctly, against a real competitor.** Probe D names
VIC and calibration — both in the skill's own description — yet the agent did not invoke
HydroClimMate. It routed to the manuscript skill `yifan-help-me-revise` instead, and stated
why it had ruled HydroClimMate out: the skill "is scoped to project-specific records and
there is no project in the permitted directory." This is one observed exclusion under
competition, not proof of which clause caused it.
In v0.6, absence of a project is no longer itself an exclusion for documented-model questions.

**Observed selective loading.** All three read `SKILL.md`, then `core.md`,
then exactly one feature file. None loaded a second feature file in these probes. This does
not establish that additional feature reads would be wrong on other requests.

**The probes cited routing exclusions.** Probe A rejected Run by
citing the "do not use for" column ("scientific interpretation of completed results"). Probe B
rejected all three alternatives explicitly. The agents used the table's negative space, not
just its positive matches.

**The answer was consistent with the reference.** Probe C's approach named control volume,
time window, included terms and tolerance; distinguished interval-mean fluxes from cumulative
counters; and applied effective-area weighting — consistent with `analyze.md`. Without a
no-reference control, this does not establish that the skill caused the behavior rather than the agent using prior hydrological knowledge.

**Probe B behaved correctly under missing information.** With no project records available it
produced the five-field checklist with configuration-dependent items labeled proposed, and
flagged the low-flow metric definition as a blocking choice for the research owner, instead of
asserting an answer. That is the intended behavior for Plan.

## Incidental finding, unrelated to this skill

Probe D reported two defects in `yifan-help-me-revise` while reading it. Both were checked
and both hold:

- `SKILL.md:126-127` cites `evidence/rules.yaml` and `evidence/move-statistics.json` for its
  rule counts and machine-checked examples. There is no `evidence/` directory in the
  installed skill.
- `M-03` is defined inconsistently: `references/methods.md:52` gives it as "Report the
  robustness check, not just the choice", while `references/paper-types.md:20` cites it as
  "keep calibration, optimization, validation, and application separate".

Worth fixing there; nothing to do here.

## Limits of this result

Four probes, one run each, is a smoke test — not a pass rate. It shows the routing table can
work, not how often it does. Three of the four are worth weight: A restates the table almost
verbatim and mainly confirms the plumbing.

Triggering was not measured. Asking a subagent to report which guidance it used primes it to
go looking, so these probes cannot tell you whether the skill fires unprompted in a normal
session. Probe D is partial evidence on the negative side — it declined to fire even while
primed — but the positive side is still unmeasured.
