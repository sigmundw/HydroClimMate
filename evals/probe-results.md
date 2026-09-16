# Routing probe results — 2026-09-16, HydroClimMate v0.5

Method: in-session subagents, each given an empty working directory and the raw researcher
request, told to consult whatever guidance was available and to stop once oriented, then to
report the files they read and the feature they selected. See README.md for why the
`claude -p` harness could not be used and what this method can and cannot measure.

Expected trace: `SKILL.md → references/core.md → references/<one feature>.md`.
Reading more than one feature file would itself be a routing failure.

| # | Request | Difficulty | Expected | Selected | Trace | Result |
|---|---|---|---|---|---|---|
| A | runoff 40% high vs USGS gauge | easy (restates table) | Analyze | Analyze | core → analyze | pass |
| B | mizuRoute offline vs online coupling for low-flow skill | **hard** | Plan | Plan | core → plan | pass |
| C | water balance closure on HRLDAS output | **hard** | Analyze | Analyze | core → analyze | pass |

## Observations

**Progressive disclosure works as designed.** All three read `SKILL.md`, then `core.md`,
then exactly one feature file. None loaded a second feature file, which was the specific
failure the four-file split was meant to prevent.

**The routing table's exclusions are load-bearing, not decorative.** Probe A rejected Run by
citing the "do not use for" column ("scientific interpretation of completed results"). Probe B
rejected all three alternatives explicitly. The agents used the table's negative space, not
just its positive matches.

**The references are being used, not merely opened.** Probe C's approach named control volume,
time window, included terms and tolerance; distinguished interval-mean fluxes from cumulative
counters; and applied effective-area weighting — all specific instructions from `analyze.md`
rather than general hydrological knowledge. This is the strongest evidence in the set that the
content earns its place.

**Probe B behaved correctly under missing information.** With no project records available it
produced the five-field checklist with configuration-dependent items labeled proposed, and
flagged the low-flow metric definition as a blocking choice for the research owner, instead of
asserting an answer. That is the intended behavior for Plan.

## Limits of this result

Three probes, one run each, is a smoke test — not a pass rate. It shows the routing table can
work, not how often it does.

Only two of the three were hard cases, and the third hard case (Noah-MP top-layer soil moisture
after a forcing change) was not run. Triggering was not measured at all: asking a subagent to
report which guidance it used primes it to go looking, so these probes cannot tell you whether
the skill fires on its own in a normal session.
