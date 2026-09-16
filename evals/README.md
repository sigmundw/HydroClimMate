# Routing and triggering evals

`trigger-eval.json` contains positive cases across four features and near-miss negatives.
v0.6 adds documented-model questions without a project and ISSM cases; historical counts
below refer to the original v0.5 suite. The negatives are
deliberately close to the domain (hydrology units, a lab model name, the netCDF toolchain,
manuscript writing about a VIC calibration); an obviously irrelevant negative tests nothing.

## Status: not yet measured

The suite has **not produced a valid result**. Recording why, so the next attempt does not
repeat it.

The intended harness is `skill-creator`'s trigger evaluator:

```bash
cd <skill-creator>
python3 -m scripts.run_eval \
  --eval-set <repo>/evals/trigger-eval.json \
  --skill-path ~/.claude/skills/hydroclimmate \
  --runs-per-query 3 --verbose
```

It works by spawning `claude -p` as a subprocess. In the environment where this was first
run, that subprocess returned:

```
"Failed to authenticate"   terminal_reason: "api_error"
```

Every one of the 60 runs died before reaching a tool call, so all 20 queries recorded a
0/3 trigger rate. That produced an apparently clean "10/20 passed" — all ten negatives
counted as passes purely because nothing ran. **Authentication failures invalidate the runs; zero variance alone does not diagnose the cause.** The numbers were discarded rather
than recorded.

To get a real measurement, run it where a nested `claude -p` can authenticate: a plain
terminal session outside the desktop app, or an environment with `ANTHROPIC_API_KEY` set.
Sanity-check first with a single query and confirm the output contains tool calls:

```bash
env -u CLAUDECODE claude -p "compute basin-mean monthly precip from the ERA5 forcing netcdfs, area weighted" \
  --output-format stream-json --verbose | grep -c tool_use
```

A count of zero requires inspection of the transcript and exit status; it may be a missed
trigger or an environment failure, not automatically the latter.

Note also that `timeout` is not present on macOS by default — use `gtimeout` from coreutils
if you want to bound these runs.

## What triggering and routing each mean here

Two separable questions, worth keeping apart:

- **Triggering** — does the `description` cause the skill to fire at all? This is what
  `run_eval.py` measures, and what the negatives above test.
- **Routing** — once it fires, does the routing table send the request to the right one of
  Understand / Plan / Run / Analyze? `expected_feature` in the fixture records the intended
  answer for each positive case.

## Easy vs hard positives

Each positive now carries a `difficulty` flag. Seven of the ten restate a contrasting
prompt that already appears in the routing table — "what is spin-up in this config?",
"Resume this failed job", "why is runoff biased high?", "Compute basin means". An agent
that matches those is demonstrating recall of the table, not routing judgment, so they
measure much less than their pass rate suggests.

The three marked `hard` use wording found nowhere in the table:

- offline vs online mizuRoute coupling for low-flow skill → Plan
- water balance closure on HRLDAS output → Analyze
- Noah-MP top-layer soil moisture looks off after a forcing change → Analyze

Weight these far more heavily, and add more of them before treating a pass rate as evidence.
A suite built only from the table's own examples will report near-perfect routing no matter
how the table performs on real requests.

## In-session subagent probe

Where a nested `claude -p` cannot authenticate, routing can still be measured with in-session
subagents, which inherit the session's credentials. Give a subagent an empty working
directory and the raw researcher request, tell it to consult whatever guidance is available
and to stop once oriented, then have it report the files it read and the feature it selected.
The files-read list is the actual measurement: the expected trace is
`SKILL.md → references/core.md → references/<one feature>.md`, with additional feature reads allowed when justified by a concrete dependency. Judge
the primary feature and relevance of reads, not an exact file-count ceiling.

This is weaker than the `claude -p` harness in one respect: asking the subagent to report
which guidance it used primes it to look for guidance, so it inflates the trigger rate and
cannot measure triggering. Use it for routing only; use `run_eval.py` for triggering.

## v0.6 knowledge evaluation

See [knowledge-eval.md](knowledge-eval.md). Triggering, selective reading and answer quality
are separate outcomes. Historical probe records do not constitute v0.6 measurements.
