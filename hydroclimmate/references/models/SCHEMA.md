# Model pack structured layers — schema

A pack may carry optional structured layers beside its Markdown, confronted by
`tools/hcm_check.py` against actual files. A declaration is not proof; see
[core.md](../core.md#local-model-knowledge). No acceptance thresholds here —
those stay in the project's experiment record.

## Two generations

A pack declares its generation in its manifest (`pack.yaml`/`pack.json`, field
`generation`, default `1` if absent):

- **Generation 1** (the original seven packs: `ctsm`, `issm`, `mizuroute`,
  `modflow`, `rbm`, `vic`, `wrf-urban`). Five Markdown files
  (`overview.md`/`execution.md`/`outputs.md`/`pitfalls.md`/`sources.md`); the
  **absolute rule** below governs every structured fact; structured layers stay
  JSON. Not rebuilt in the v0.9 knowledge-layer rebuild — no pinned source tree
  was available for them and downloading one was not authorized. See
  [models/index.md](index.md), which marks them as this older generation
  without editing their content.
- **Generation 2** (`hrldas-noahmp`). A card +
  process map + symptom-indexed failure list + bounded recipes + version
  anchor, backed by **generated catalogs** mechanically extracted from a
  pinned source tree and confronted with real output; structured layers are
  YAML (see "YAML subset" below). Facts come from the pinned source or from
  observed output, each with its own citation and evidence grade — this
  **replaces** the old absolute rule for this generation (below).

Every tool that reads a pack's structured layers (`hcm_check.py`,
`hcm_lookup.py`, `build_index.py`, `selftest.py`, `evals/check_knowledge.py`)
accepts both generations: it reads whichever manifest is present
(`pack.yaml` then `pack.json`), and for each declared layer, loads
`<name>.yaml` if that file exists, else `<name>.json`.

## Generation-1 rule (unchanged)

**Absolute rule**: a field the pack's existing sourced Markdown does not
support is absent, never guessed. No placeholder for "not stated" other than
omitting the key.

**Every structured fact** (not a container) carries:

- `source` — a source id in this pack's `sources.md`, or `null` if uncited.
- `scope` — model/driver/version string, or `"unspecified in the pack"`.
- `basis` — `source_read` | `observed_in_output` | `both` | `unverified`.
- `from` — `{"file", "anchor"}` pointing at the prose sentence it came from.

A generation-2 pack's curated facts also carry `confirmed_against`: a short hash
(`tools/_anchor_hash.py`) of the `from.anchor` paragraph's text at the time a person last
confirmed the fact still agrees with that prose. `evals/check_knowledge.py` recomputes
the paragraph's current hash and fails if it no longer matches — a prose correction
changes the paragraph's text, which is exactly what should force every curated fact
citing it to be re-read and re-confirmed, not silently kept. After confirming (or fixing)
each flagged fact by hand, run `tools/refresh_confirmed_against.py --pack <pack>` once to
update the stored hashes; the tool never adjusts a fact's own claim, only the hash.

`basis: unverified` can never yield a VERIFIED/CONSISTENT check verdict.
`basis: both` (source-read AND separately confirmed against real output) is
available to either generation; it was added in the v0.9 rebuild alongside the
catalogs' `evidence` field of the same three-plus-one shape (see below) —
before that, curated-layer facts could only be `source_read`,
`observed_in_output` or `unverified` singly. A generation-2 pack's curated
layers point `from` at the new prose (`card.md`/`processes.md`/`failures.md`/
`recipes.md`/`version.md`), never at the redirect stubs
(`overview.md`/`outputs.md`/`execution.md`/`pitfalls.md`) that generation
keeps only so old links and structured-layer anchors from before the rebuild
still resolve. Where a generated catalog entry already carries a fact (e.g. a
variable's units/kind/fill — see below), the curated layer references that
catalog entry instead of restating it.

## `pack.yaml` / `pack.json` (manifest)
`{pack, generation, version_scope, layers: {narrative|interface|switches|
pitfalls|workflows|index|selftest|catalogs: {file, coverage: full|partial|
none}}, notes}`. `full` is refused if any fact in that layer has
`basis: unverified`. `index.json` is generated (see below), so its coverage
is `full` by construction — it carries no claim of its own. A generation-2
pack additionally declares a `catalogs` layer pointing at
`catalogs/MANIFEST.json`.

## `interface.yaml`/`.json` (data interface: files, inputs, outputs)
`{pack, files: [...], inputs: [...], outputs: [...]}`, each a flat list of
facts. `files` entries: `{file_kind, statement, ...4 keys}` — role/naming/
record-structure/time-stamp meaning, only as stated. `inputs`/`outputs`
entries: `{variable, aspect, statement, ...4 keys}`. `variable` may be a
descriptive string when the pack never names the exact NetCDF variable (this
is common for generation 1; a generation-2 pack usually can name it exactly
and cites `catalogs/outputs.yaml`/`catalogs/restart.yaml` for the rest).
`aspect` ∈ `units|kind|time_stamp_convention|fill|dimension_order|
valid_support|identity|forcing_categories|...`; `kind` ∈ `instantaneous|
accumulated_since_start|interval_mean|state`. `fill` facts may add
`attribute_declared` (bool) and `known_raw_value_order` (number).
`accumulation-and-fill --pack` reads `outputs` facts for `--var`;
`describe --pack --file` reads both `inputs` and `outputs` for every
variable actually in the file, printing NO DECLARATION where silent —
expected for most variables, and for every catalog-only fact of a
generation-2 pack (use `hcm_lookup.py --pack <p> <NAME>` for those instead).

## `switches.yaml`/`.json` (declared switch effects)
`{pack, switches: [{name, structural_change, exchanged_fields,
untouched_fields, expected_scaling_variable}]}` — each of the four is a fact
object (`{statement, ...4 keys}`, `exchanged_fields`/`untouched_fields` also
carry a `fields` list) or absent if not stated. `paired-response --switch`
reads this to flag which compared variables are exchanged, untouched, or
unmentioned, and to hint `--control-var` (never applied silently).

## `pitfalls.yaml`/`.json` (detectable pitfalls)
`{pack, pitfalls: [{id, detect?}]}`. `id` = the matching `pitfalls.md`
heading's anchor slug, one-to-one (a generation-2 pack keeps `pitfalls.md` as
a redirect stub for exactly this reason: it is the stable id namespace, even
though the actual failure prose lives in `failures.md`). `detect` (present
only if automatable): `{check, ...params, what_counts, source, scope, basis,
from}`; `check` must name an existing `hcm_check.py` subcommand.

## `workflows.yaml`/`.json` (common task sequences, prose-only)
`{pack, workflows: [{name, steps: [{step, what_is_done, must_establish,
check, ...4 keys}]}]}`, only for sequences the pack's prose already
describes (generation 1: `execution.md`/`overview.md`; generation 2: the
version/failures/recipes files a step's evidence actually comes from — see
the re-sourcing rule above). A step names the evidence to produce
(`must_establish`) and, if one exists, an observation or `hcm_check.py`
subcommand that would establish it (`check`, nullable) — never a gate the
executing agent certifies for itself as passed. Absent if the pack describes
no sequence. A step whose claim the new prose no longer states is dropped,
not force-cited to an unrelated anchor.

## `index.json` (generated key index — always JSON, both generations)
`{pack, generated_by, entries: [{name, kind: file|input|output|switch|
variable, declared_in, from, related_switches, related_pitfalls}]}`, built
by `tools/build_index.py <pack> --write` from `interface`, `switches` and
`pitfalls` (whichever extension each is stored in). Never hand-edit: the
validator checks the committed file equals a fresh build. `hcm_check.py
lookup --pack P NAME` prints an entry. This is a *machine-only* file (a
build artifact, not prose a person reads for its own sake) and so stays JSON
even for a generation-2 pack — see "YAML subset" below.

## `selftest.yaml`/`.json` (self-test fixtures)
`{pack, cases: [{pitfall_id, faulty: {...fixture spec}, clean: {...fixture
spec}}]}`, one case per `pitfalls` entry with a `detect` stanza.
`tools/selftest.py --packs` builds the fixtures on the fly (none stored in
the repo) and asserts FIRED on faulty / QUIET on clean.

## Tiny example (one generation-1 `interface.json` output fact)
```json
{"variable": "snow water equivalent (name not given in pack)", "aspect": "fill",
 "statement": "large negative fill (~-1e33) may appear on water-body cells, no declared _FillValue",
 "source": null, "scope": "one output set; not verified elsewhere", "basis": "observed_in_output",
 "from": {"file": "pitfalls.md", "anchor": "snow-water-equivalent-identity-and-unmasked-fill-values"}}
```

---

## Generation 2: catalogs, reading order, and the YAML subset

### Reading order (what an agent should actually do)

For a generation-2 pack, read **`card.md` only** as the must-read file
(hard-capped, see below). From there:

1. Any variable/option/parameter/constant name → `tools/hcm_lookup.py --pack
   <pack> <NAME>` (queries the catalogs; never read a `catalogs/*.yaml` file
   wholesale — they exist to be queried, not read).
2. A symptom ("my totals are off", "the switch did nothing") →
   `failures.md`, indexed by symptom.
3. "How does this process work / what module implements it" → `processes.md`,
   a question → switch → module → variable map.
4. A bounded task with a known cost ("period total", "daily mean", "paired
   difference") → `recipes.md`.
5. Whether a checkout/output matches this pack's pin → `version.md`.
6. Provenance / what backs a claim → `sources.md` (ids `L0`-`L6`, plus
   floating `H*` records kept only where a curated-layer fact still cites
   one).

`models/index.md` and `core.md`'s local-model-knowledge paragraph state this
same order for the agent; the
redirect stubs (`overview.md`/`outputs.md`/`execution.md`/`pitfalls.md`) exist
only so pre-rebuild links and `pitfalls.yaml` ids keep resolving, not as a
second reading path.

### Catalogs (generated, never hand-edited)

`catalogs/*.yaml` (`outputs`, `restart`, `forcing`, `setup`, `namelist`,
`physics_options`, `parameters`, `constants`, `urban_path`) are produced by
`tools/extract_pack.py` directly from the pinned source tree — never
hand-typed — and re-derived by running the extractor again (diff against the
committed file is the drift check, same discipline `index.json` already
used). Every catalog file:
- `{"pack", "catalog", "generator", "generator_version", "scope", "count", <catalog-specific list key>}`.
- `generator` names the exact `extract_pack.py` subcommand that produced it.
- `scope` is the fixed string `"HRLDAS <hrldas-commit> + noahmp <noahmp-commit>"`
  for this pack's pinned pair — see `catalogs/MANIFEST.json` for the exact
  hashes, and [version.md](hrldas-noahmp/version.md) for how the commit is
  pinned. The canonical short form for a commit anywhere in this pack (prose,
  catalogs, `sources.md`) is `git rev-parse --short=8` in the pinned checkout
  — 8 hex characters, e.g. `d9f5b205`/`9fbe6724` — not `git describe`'s own
  7-character abbreviation, which is still quoted verbatim where the text is
  literally reporting what `git describe` printed (`version.md`,
  `sources.md#l0`).

Every extracted **fact** (a dict describing one variable/key/parameter/
constant/observation) carries:
- `where` = `{"file", "line", "commit"}`. `file` is relative to the source
  root passed to `--source-root`; `commit` is `"hrldas@<hash>"` or
  `"noahmp@<hash>"` depending which repo the file belongs to.
- `evidence` ∈ `source_read | observed_in_output | both`. Every fact starts
  `source_read` (produced by parsing source only). `tools/validate_catalogs.py`,
  run against a real LDASOUT/RESTART/LDASIN file, upgrades matched,
  non-conflicting facts to `both` **in place**, deterministically: given the
  same source tree and the same real files, `extract_pack.py all` followed by
  `validate_catalogs.py --apply` reproduces the committed catalogs
  byte-identical (verified; see `catalogs/VALIDATION.md`). It never invents
  `observed_in_output` alone, since these catalogs
  are never built from output-reading alone.
- `scope` — the same pinned commit-pair string as the catalog manifest.

This reuses `where`/`evidence`/`scope` rather than the curated layers'
`source`/`basis`/`from`, because catalog facts point at *upstream model
source*, so they need a file:line:commit, not a `sources.md` id.

**Per-file shape** (see each file's own header comment for the exact
regeneration command): `catalogs/outputs.yaml` — LDASOUT variables from
`add_to_output(...)` calls, each with `name`, `driver_array`, `description`,
`units`, `dimensionality`, `dim_order` (source-declared Fortran order — real
files report the **reverse**, confirmed by the validator as the expected
case, not a discrepancy), `gating`, `kind`, `kind_evidence`, `fill_note`.
`catalogs/restart.yaml` — same shape for `add_to_restart(...)`; description/
units are `null` (absent from source, not guessed) since those call sites
never pass them. `catalogs/forcing.yaml` — LDASIN roles, each with its
`forcing_name_*` namelist rename key and whether the read is required.
`catalogs/setup.yaml` — HRLDAS setup-file fields. `catalogs/namelist.yaml` —
every `NOAHLSM_OFFLINE` key, cross-referenced against `README.namelist`.
`catalogs/physics_options.yaml` — namelist key → `IOPT_*` → internal name →
dispatch table, for the options that route to a differently-named subroutine
(most physics options branch inline instead — a real finding about this
codebase, not a shortfall; see the file's own scope note).
`catalogs/parameters.yaml` — every `NoahmpTable.TBL`/`URBPARM*.TBL` group and
key. `catalogs/constants.yaml` — `ConstantDefineMod.F90`'s constants.
`catalogs/urban_path.yaml` — the mechanical urban-path facts (the earlier
hand-written correction to the tile-weighted field list is now one of these:
re-derived by regex from the actual assignment lines, not hand-typed). `catalogs/MANIFEST.json`
— `{pack, generator, generator_version, scope, source_commits, files:
{filename: {count, sha256}}}` (machine-only, stays JSON — see below).
`catalogs/VALIDATION.md` — prose summary of the last `validate_catalogs.py`
run against real files (no paths, run names or other identifying strings).

Regeneration:
```
python3 tools/extract_pack.py all --source-root <pinned-checkout> \
    --out-dir hydroclimmate/references/models/hrldas-noahmp/catalogs
python3 tools/validate_catalogs.py \
    --pack-dir hydroclimmate/references/models/hrldas-noahmp \
    --ldasout <one .LDASOUT_DOMAIN1> --restart <one RESTART.*> --ldasin <one .LDASIN_DOMAIN1> \
    --check-kind-sample --apply \
    --summary-out hydroclimmate/references/models/hrldas-noahmp/catalogs/VALIDATION.md
```

**Known gaps** (mechanical extraction could not reach these; stated, not
hidden): `kind` for the variables/parameters whose accumulate/reset logic
lives inside `noahmp/src/*.F90` under local variable names classify_kind
cannot trace (or, for the MMF groundwater family, under a local dummy
argument name that does not textually match the `NoahmpIO%` field name — see
`catalogs/kinds_overlay.yaml` below) is `state_or_instantaneous` or
`undetermined`, not guessed further at the generator level. `physics_options.yaml`
covers every namelist option `ConfigVarInTransferMod.F90` maps to an internal
`Opt*`/`SF_URBAN_PHYSICS` field (27 at this commit); a value present in
`readme_values` but absent from `code_branches` can
mean the value is genuinely unhandled, OR that its gate is relational (`>`,
`/=`) rather than a literal `==N` the mechanical scan matches — the two must
not be read alike, and `catalogs/options_overlay.yaml` records which is which
for the cases checked so far. `namelist.yaml`'s `allowed_values` is empty for
keys whose `README.namelist` entry doesn't use the recognized comment shape.
Land-use/soil class names are only populated for table groups using the
`! N: Name` comment convention.

### Curated overlays (hand-authored, never generated)

Two files sit in `catalogs/` beside the generated ones but are never touched
by `extract_pack.py` and never asserted equal to a fresh build
(`evals/check_knowledge.py`'s `check_catalogs_fresh_build` only iterates the
files a fresh `extract_pack.py all` actually produces). Both declare
`curated: true` and use the curated-layer citation shape (`where`,
`reset_where`, `evidence`, `scope`) rather than being re-derived from a
regex pass — the judgement call a mechanical pass cannot make safely is
exactly what they exist to hold, always with a citation, re-verified against
source rather than merely transcribed.

`catalogs/kinds_overlay.yaml` — `{pack, catalog: "kinds_overlay", curated: true,
scope, count, rows: [{variable, true_kind, where, reset_where?, note?,
sampling_note?, units_note?, gate?, updated_when?, evidence, scope}]}`. `variable`
must name a real entry in `catalogs/outputs.yaml` (checked by `evals/check_knowledge.py`).
`gate` answers "when is this WRITTEN" (often unconditional, e.g. every record once
`output_timestep>0`); `updated_when`, where present, separately answers "under which
option value(s) does this field's VALUE actually change" — a field can be written every
record while its value stays frozen at an initial/restart value for every option except
a handful (`ZWT`/`WA`/`WT` are the pack's own example: written unconditionally, but only
live under specific `subsurface_runoff_option` values — see `hcm_lookup.py`'s "UPDATED
WHEN" line). Conflating the two is the trap this field exists to prevent.
`true_kind` is a **closed vocabulary**, one of:
- `state` — a prognostic or diagnostic state, valid at the record's instant; never accumulated.
- `static` — does not change over the run (a land-use/soil category, a fixed level height).
- `instantaneous_rate` — a flux/rate (W/m2, mm/s) at the end of the record's step; integrates correctly against the output interval.
- `per_model_timestep_depth` — a depth computed fresh each `NOAH_TIMESTEP` and written as-is; summing records over the output interval over-counts unless corrected by `OUTPUT_TIMESTEP / NOAH_TIMESTEP` (`RAINRATE`, `PONDING`).
- `per_soil_timestep_energy` — an energy/flux quantity valid for exactly one `SOIL_TIMESTEP`, not since-start (`EFLXB`).
- `accumulated_since_start` — accumulates since run start or the resumed restart; monotone barring a documented cap; difference two records for a period total.
- `accumulated_reset_each_soil_step` — accumulates within one soil timestep and is zeroed the step after (the `ACC_*` family).
- `accumulated_reset_each_mmf_call` — accumulates within one MMF (groundwater) call and is zeroed at the next call (`DEEPRECH`).
- `per_mmf_call_depth` — a depth in metres valid for one MMF call only, not a rate and not since-start (`QRF`/`QSPRING`/`QLAT`).
- `layer_integrated_state` — a state formed by summing over snow/soil layers within one call, not accumulated over time (`SOILENERGY`, `SNOWENERGY`).
- `diagnostic` — a per-record diagnostic that is not itself a physical flux or state in the usual sense (a fraction, a ratio, a value that can be `undefined_real` outside its valid condition).

`catalogs/options_overlay.yaml` — `{pack, catalog: "options_overlay", curated: true,
scope, count, rows: [{internal_option_name, namelist_key, kind, value, note,
where, evidence, scope}], note}`. `internal_option_name` must name a real
entry in `catalogs/physics_options.yaml`. `kind` is free text describing what
the row is for (e.g. `"readme_value_with_no_code_branch"`,
`"value_scheme_note"`) — this file is a running list of specific
cross-checks, not itself a closed-vocabulary catalog; its own `note` states
how much of `physics_options.yaml` it covers (deliberately not exhaustive —
see the file's own `note`).

Both are queried the same way as the generated catalogs:
`tools/hcm_lookup.py --pack hrldas-noahmp <NAME>` merges a `kinds_overlay.yaml`
row into the catalog entry it names (`true_kind` shown next to the generated
`kind`, never silently replacing it) and an `options_overlay.yaml` row into
the matching physics option's entry; `--list kind=<true_kind>` lists every
overlay row with that kind; `--process <keyword>` lists output variables and
physics options whose name or description contains the keyword.
`tools/validate_catalogs.py --check-kind-sample` tests the empirical
monotonicity/reset sample against a variable's overlay `true_kind` when one
exists, not the generated `kind` (which would just re-report the known gap
for the ~150 `state_or_instantaneous`/`undetermined` variables the overlay
exists to resolve).

### YAML subset

Design choice: use YAML instead of JSON for readability. Every pack layer a
person or agent reads (curated layers and
catalogs) is YAML. Only **machine-only** files — a generated lookup index
(`index.json`) and a catalog manifest of hashes and counts
(`catalogs/MANIFEST.json`) — stay JSON, because nobody is meant to read them
for their own sake; they exist to be diffed by a script.

The extractor and every hand-authored curated-layer file emit a **strict
simple subset** of YAML, implemented in `tools/_miniyaml.py`:
- block style (`key: value` lines, 2-space indents); no flow style at the
  top level;
- a block list of mappings (`- key: value` then further indented fields) for
  the main record list in a file, and for any field whose own value is a
  list of mappings (e.g. a parameter-table group's `parameters`, a physics
  option's `values`, a workflow's `steps`) — this nests as deep as the data
  actually requires; there is no arbitrary depth limit on list-of-mapping
  nesting, only on mapping-of-mapping nesting (next point);
- scalars: `null`, `true`/`false`, a plain JSON number (floats always keep a
  decimal point, e.g. `1.0e-08` not `1e-08`, so YAML's implicit float
  resolver — which does not require a decimal point before matching, unlike
  JSON — still recognizes it as a float and not a string), or a
  double-quoted string with JSON-style escaping — strings are **always**
  double-quoted, never bare or single-quoted;
- **one level of nested block mapping**: a dict field whose own values are
  all scalars (e.g. `where: {file, line, commit}`) renders as an indented
  block mapping. A dict with a deeper structure (e.g. `kind_evidence`, whose
  values are themselves dicts) renders inline instead, as a JSON-compatible
  flow mapping (`{"key": value, ...}`) — valid YAML, valid JSON, one line;
- short lists of scalars (e.g. `dim_order`, `gating`) render as
  JSON-compatible flow sequences (`["a", "b"]`), never as a block list, since
  they are not the main record list;
- no anchors/aliases, no multi-line scalars, no tab characters;
- a leading `# `-comment header: generator, source commits (for generated
  catalogs), and "do not hand-edit; regenerate with ...".

Because every value that is not itself the start of a nested block is a
single line of valid JSON, `tools/_miniyaml.py`'s reader only implements the
block/indentation walking itself and delegates every terminal scalar/flow
span to the stdlib `json` module — and every file this subset can produce is
therefore also ordinary, valid YAML that PyYAML's `yaml.safe_load` loads to
the identical Python object. Tools load YAML with PyYAML when importable
(`hydroclimmate/tools/_miniyaml.py`'s own `load_file` helper does this), else
with `_miniyaml`'s own strict-subset reader; `tools/selftest.py` (no flag, or
`--yaml`) asserts the two readers agree on every pack YAML file in the repo,
and that `_miniyaml.dump(_miniyaml.load(x))` round-trips.

**Reproducibility of the generated catalogs**: `extract_pack.py all` alone is
deterministic given the same source tree (pure `source_read` facts).
`validate_catalogs.py --apply` is a second, separately deterministic step
given the same source tree and the same real LDASOUT/RESTART/LDASIN files:
it only ever upgrades a matched, non-conflicting fact's `evidence` from
`source_read` to `both`, and refreshes `catalogs/MANIFEST.json`'s hashes for
the files it touched. Running both steps against the pinned source and the
same real files reproduces the committed catalogs byte-for-byte (checked
directly). `evals/check_knowledge.py --source-root <root>`
re-runs `extract_pack.py all` alone and asserts the result is structurally
identical to the committed catalogs **modulo `evidence` fields that could
only differ `source_read` vs `both`** (it cannot also re-run
`validate_catalogs.py`, since that needs real output/restart/forcing files,
not just a source root).
