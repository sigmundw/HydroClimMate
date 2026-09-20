# Model pack structured layers — schema

A pack may carry optional JSON layers beside its Markdown, confronted by
`tools/hcm_check.py` against actual files. A declaration is not proof; see
[core.md](../core.md#local-model-knowledge). No acceptance thresholds here —
those stay in the project's experiment record.

**Absolute rule**: a field the pack's existing sourced Markdown does not
support is absent, never guessed. No placeholder for "not stated" other than
omitting the key.

**Every structured fact** (not a container) carries:

- `source` — a source id in this pack's `sources.md`, or `null` if uncited.
- `scope` — model/driver/version string, or `"unspecified in the pack"`.
- `basis` — `source_read` | `observed_in_output` | `unverified`.
- `from` — `{"file", "anchor"}` pointing at the prose sentence it came from.

`basis: unverified` can never yield a VERIFIED/CONSISTENT check verdict.

## `pack.json` (manifest)
`{pack, version_scope, layers: {narrative|interface|switches|pitfalls|
workflows|index|selftest: {file, coverage: full|partial|none}}, notes}`.
`full` is refused if any fact in that layer has `basis: unverified`.
`index.json` is generated (see below), so its coverage is `full` by
construction — it carries no claim of its own.

## `interface.json` (data interface: files, inputs, outputs)
`{pack, files: [...], inputs: [...], outputs: [...]}`, each a flat list of
facts. `files` entries: `{file_kind, statement, ...4 keys}` — role/naming/
record-structure/time-stamp meaning, only as stated. `inputs`/`outputs`
entries: `{variable, aspect, statement, ...4 keys}`. `variable` may be a
descriptive string when the pack never names the exact NetCDF variable.
`aspect` ∈ `units|kind|time_stamp_convention|fill|dimension_order|
valid_support|identity|forcing_categories|...`; `kind` ∈ `instantaneous|
accumulated_since_start|interval_mean|state`. `fill` facts may add
`attribute_declared` (bool) and `known_raw_value_order` (number).
`accumulation-and-fill --pack` reads `outputs` facts for `--var`;
`describe --pack --file` reads both `inputs` and `outputs` for every
variable actually in the file, printing NO DECLARATION where silent —
expected for most variables.

## `switches.json` (declared switch effects)
`{pack, switches: [{name, structural_change, exchanged_fields,
untouched_fields, expected_scaling_variable}]}` — each of the four is a fact
object (`{statement, ...4 keys}`, `exchanged_fields`/`untouched_fields` also
carry a `fields` list) or absent if not stated. `paired-response --switch`
reads this to flag which compared variables are exchanged, untouched, or
unmentioned, and to hint `--control-var` (never applied silently).

## `pitfalls.json` (detectable pitfalls)
`{pack, pitfalls: [{id, detect?}]}`. `id` = the matching `pitfalls.md`
heading's anchor slug, one-to-one. `detect` (present only if automatable):
`{check, ...params, what_counts, source, scope, basis, from}`; `check` must
name an existing `hcm_check.py` subcommand.

## `workflows.json` (common task sequences, prose-only)
`{pack, workflows: [{name, steps: [{step, what_is_done, must_establish,
check, ...4 keys}]}]}`, only for sequences the pack's `execution.md`/
`overview.md` already describe. A step names the evidence to produce
(`must_establish`) and, if one exists, an observation or `hcm_check.py`
subcommand that would establish it (`check`, nullable) — never a gate the
executing agent certifies for itself as passed. Absent if the pack describes
no sequence.

## `index.json` (generated key index)
`{pack, generated_by, entries: [{name, kind: file|input|output|switch|
variable, declared_in, from, related_switches, related_pitfalls}]}`, built
by `tools/build_index.py <pack> --write` from `interface.json`,
`switches.json` and `pitfalls.json`. Never hand-edit: the validator checks
the committed file equals a fresh build. `hcm_check.py lookup --pack P NAME`
prints an entry.

## `selftest.json` (self-test fixtures)
`{pack, cases: [{pitfall_id, faulty: {...fixture spec}, clean: {...fixture
spec}}]}`, one case per `pitfalls.json` entry with a `detect` stanza.
`tools/selftest.py --packs` builds the fixtures on the fly (none stored in
the repo) and asserts FIRED on faulty / QUIET on clean.

## Tiny example (one `interface.json` output fact)
```json
{"variable": "snow water equivalent (name not given in pack)", "aspect": "fill",
 "statement": "large negative fill (~-1e33) may appear on water-body cells, no declared _FillValue",
 "source": null, "scope": "one output set; not verified elsewhere", "basis": "observed_in_output",
 "from": {"file": "pitfalls.md", "anchor": "snow-water-equivalent-identity-and-unmasked-fill-values"}}
```
