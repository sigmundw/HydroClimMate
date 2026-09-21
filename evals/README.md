# Routing and triggering evals

`trigger-eval.json` holds positive and negative fixtures across the five features (Understand, Plan, Run, Analyze, Review) plus documented-model questions asked without a project. Negatives sit deliberately close to the domain (hydrology units, a lab model name, the netCDF toolchain, manuscript writing about a VIC calibration); an obviously irrelevant negative tests nothing.

## Running the trigger/routing harness

Use `skill-creator`'s trigger evaluator:

```bash
cd <skill-creator>
python3 -m scripts.run_eval \
  --eval-set <repo>/evals/trigger-eval.json \
  --skill-path ~/.claude/skills/hydroclimmate \
  --runs-per-query 3 --verbose
```

It spawns `claude -p` as a subprocess, so it needs an environment where that can authenticate: a plain terminal session outside the desktop app, or `ANTHROPIC_API_KEY` set. Sanity-check first with a single query and confirm the output contains tool calls:

```bash
env -u CLAUDECODE claude -p "compute basin-mean monthly precip from the ERA5 forcing netcdfs, area weighted" \
  --output-format stream-json --verbose | grep -c tool_use
```

A count of zero needs inspection of the transcript and exit status before concluding the query did not trigger. `timeout` is not present on macOS by default; use `gtimeout` from coreutils if you need to bound a run.

Classify from the whole streamed transcript, not the first event alone — a thinking-only opening block is not a miss on its own. A single run per query is not enough to draw a conclusion; use `--runs-per-query 3` or more before treating a pass rate as evidence.

## What triggering and routing each mean here

- **Triggering** — does the `description` cause the skill to fire at all? This is what `run_eval.py` measures, and what the negatives test.
- **Routing** — once it fires, does the routing table send the request to the right one of Understand / Plan / Run / Analyze / Review? `expected_feature` in the fixture records the intended answer for each positive case.

## Easy vs hard positives

Each positive carries a `difficulty` flag. Most restate a contrasting prompt that already appears in the routing table; an agent that matches those is demonstrating recall of the table, not routing judgment. Weight `hard`-flagged cases (wording found nowhere in the table) more heavily when judging a pass rate; a suite built only from the table's own examples reports near-perfect routing regardless of how the table performs on real requests.

## In-session subagent probe

Where a nested `claude -p` cannot authenticate, routing can still be measured with in-session subagents, which inherit the session's credentials. Give a subagent an empty working directory and the raw researcher request, tell it to consult whatever guidance is available and to stop once oriented, then have it report the files it read and the feature it selected. The files-read list is the actual measurement: the expected trace is `SKILL.md → references/core.md → references/<one feature>.md`, with additional feature reads allowed when justified by a concrete dependency. Judge the primary feature and relevance of reads, not an exact file-count ceiling.

This is weaker than the `claude -p` harness in one respect: asking the subagent to report which guidance it used primes it to look for guidance, so it inflates the trigger rate and cannot measure triggering. Use it for routing only; use `run_eval.py` for triggering.

## Knowledge evaluation

See [knowledge-eval.md](knowledge-eval.md) for the pack-coverage question set and rubric. Triggering, selective reading and answer quality are separate outcomes.

## Link rot and staleness

`check_knowledge.py` runs offline by default and reports the age of each model pack's `Checked:` date, warning past 180 days. Pass `--network` to confirm every cited external URL still resolves:

```bash
python3 evals/check_knowledge.py --network
```

The network mode probes a control URL first and refuses to draw a conclusion if that fails: a bare macOS Python with no CA bundle, no egress, or a captive portal can make every HTTPS URL look unreachable, so a uniform 100% failure alongside a working control is reported as **UNMEASURED**, not as link rot. A result where every case fails identically means the instrument needs checking before the content is blamed.

## Markdown formatting

`format_markdown.py --check` (wired into `check_knowledge.py`) asserts every Markdown file in the repository is one-line-per-paragraph formatted; run `python3 evals/format_markdown.py` to reflow a file that fails it.
