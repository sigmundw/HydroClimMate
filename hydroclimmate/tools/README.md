# tools/

Executable, optional. Nothing in this package requires these tools; they
exist because some checks are cheaper and more reliable to run than to
reason about. See [review.md](../references/review.md) for when a check or
a review packet is proportionate to the task at hand.

## What each tool does

- **`hcm_check.py`** — deterministic checks on NetCDF output:
  - `paired-response` — for two runs, reports where they differ, whether the
    difference scales with a declared controlling variable (binned means,
    Spearman rank correlation), and whether declared invariant variables are
    bit-identical.
  - `accumulation-and-fill` — for one variable across a time-ordered set of
    files, reports whether it is monotone non-decreasing, where it decreases
    (a possible reset), its declared units/cell_methods/long_name, undeclared
    large-magnitude negative values, and whether `_FillValue`/`missing_value`
    is declared.
  - `pack-info` — prints a model pack's declared layers, coverage, version
    scope and fact counts by basis (see [SCHEMA.md](../references/models/SCHEMA.md)).
  - `pitfall-scan` — runs every pack pitfall detection whose required inputs
    are available and reports FIRED / QUIET / NOT RUN per pitfall,
    observations first.
  - `describe --pack <name> --file <f>` — lists every variable actually in a
    file with what was observed (dims, units, fill declared, monotonicity)
    next to whatever the pack declares about it; most variables read NO
    DECLARATION, which is the honest result for a pack that does not name
    exact NetCDF variables.
  - `lookup --pack <name> NAME` — prints a pack's generated `index.json`
    entry for a variable, configuration key or file kind: where it is
    declared, related switches, related pitfalls.

  The first two print observations first, then a verdict (VERIFIED /
  VIOLATED / UNVERIFIED) against expectations you supply with `--thresholds`
  (a JSON file, or `key: value` lines in a plain-text/Markdown file such as
  the project's experiment record). With no expectations, the verdict is
  UNVERIFIED and every observation is still printed — a missing or wrong
  threshold never hides the evidence. Run `hcm_check.py <subcommand> --help`
  for the full option list; each subcommand's help also states what it does
  **not** establish (causality, physical correctness, acceptability).

  `paired-response` and `accumulation-and-fill` also accept `--pack <name>`
  (resolved under `references/models/` next to this tool, never the current
  directory) to confront a pack's optional machine-readable declarations
  with the actual files — **a declaration is not proof**:
  - `accumulation-and-fill --pack <name>` prints a declared-vs-observed
    block for `--var` (keyword-matched against the pack's `interface.json`
    outputs, since a pack often does not name the exact NetCDF variable)
    with a verdict DISAGREES / CONSISTENT / NO DECLARATION; a matched
    declaration with `basis: unverified` can never read CONSISTENT — it
    reads UNVERIFIED and says why.
  - `paired-response --pack <name> --switch <name>` reads the pack's
    `switches.json` and annotates which compared variables are in the
    routine's exchanged list, which are declared untouched, and what a
    genuine effect should scale with (a `--control-var` **hint**, never
    applied automatically); a difference in an untouched variable is flagged
    as not attributable to the switched routine, with the pack's scope.

- **`build_index.py <pack> [--write]`** — (re)generates a pack's `index.json`
  from `interface`, `switches` and `pitfalls`, so it is never hand-written
  and can never drift or carry a claim of its own; the validator checks the
  committed file equals a fresh build. (Throughout this file, `interface.json`
  etc. name the layer, not literally the extension: a generation-2 pack per
  [SCHEMA.md](../references/models/SCHEMA.md) stores these as
  `interface.yaml` etc.; `index.json`/`catalogs/MANIFEST.json` are always
  JSON. `hcm_lookup.py --pack <pack> <NAME>` answers from a generation-2
  pack's generated `catalogs/*.yaml` instead — see SCHEMA.md.)

- **`hcm_review_packet.py`** — assembles exactly what an independent
  reviewer may see: a goal file, an experiment record, decision records,
  artefact paths and check-report files, copied into a packet directory with
  a `MANIFEST.json` (checksums, and for large files a checksum without a
  copy). It refuses any option that looks like executor narrative (a
  `--summary` or similar free-text account) and prints the reviewer's
  instructions: a three-state answer per claim, no authority to modify,
  re-run or recover anything.

## What these tools do NOT cover

- They do not decide whether a result is scientifically acceptable.
  Acceptance conditions and their owner belong in the project's own
  experiment record (`templates/EXPERIMENT.md`), not in these tools.
- They do not establish causality — `paired-response` reports association
  (binned means, rank correlation), not why the difference occurs.
- They do not judge whether a large negative value is a real physical value
  or a fill artifact — that judgement stays with the person reading the
  observations.
- They are not a review process by themselves. `hcm_review_packet.py`
  assembles inputs and states the reviewer's constraints; it does not review
  anything, and it has no authority to change the project.
- They cover exactly the two failure modes named above (plus, per pack, only
  the pitfalls that pack's own `pitfalls.json` declares a detection for). A
  check with no matching tool still needs a person or a project-specific
  script; see [review.md](../references/review.md) for assembling a review
  packet by hand when no tool applies.
- A pack's `--pack` declarations (`interface.json`, `switches.json`,
  `pitfalls.json`, `workflows.json`) are the pack's own claims, not
  independently verified facts about your files. `pack-info`/`pitfall-scan`/
  `describe`/`lookup` report what is declared and what fired; they do not
  establish that a declaration is correct, complete, or applicable to your
  exact model version. A pack's `workflows.json` step names evidence to
  produce; it does not certify that the step was actually done.

## Running without any agent

Both tools are ordinary command-line scripts; run them directly from a
terminal, with no agent or skill loaded:

```bash
python3 hydroclimmate/tools/hcm_check.py paired-response --a run_a.nc --b run_b.nc \
  --var runoff --control-file params.nc --control-var albedo_urban \
  --thresholds experiment-record.md

python3 hydroclimmate/tools/hcm_review_packet.py --goal goal.md \
  --experiment-record experiment-record.md --decisions DECISIONS.md \
  --artefact run_b.nc --check-report check_report.txt --out review_packet/
```

Self-tests build small synthetic NetCDF/text files in a temporary directory
and assert the expected verdicts; they touch no project data:

```bash
python3 hydroclimmate/tools/selftest.py                 # hcm_check.py
python3 hydroclimmate/tools/selftest.py --packs          # pack self-tests: FIRED on faulty, QUIET on clean
python3 hydroclimmate/tools/selftest_review_packet.py    # hcm_review_packet.py (stdlib only)
```

## Environment note

`hcm_check.py` needs numpy and netCDF4; `--help` works without them (the
import is lazy), but running a subcommand does not. On clusters that use
environment modules, load a Python environment that provides numpy and
netCDF4 first, for example:

```bash
module load conda
conda activate <env-with-numpy-and-netcdf4>
```

If numpy or netCDF4 is missing, the tool prints this same instruction and
exits with an error message instead of a traceback. `hcm_review_packet.py`
uses only the Python standard library and needs no environment setup.
