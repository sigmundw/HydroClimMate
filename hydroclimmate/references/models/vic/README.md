# VIC knowledge pack

## What this model is

VIC (Variable Infiltration Capacity) is a macroscale land surface and hydrology model. It solves the water and, optionally, the energy balance of each grid cell as an independent soil column: nothing flows from one cell to its neighbour. Within a cell the land is divided into vegetation tiles and, optionally, elevation bands, each with its own snowpack and canopy over shared soil layers. Its signature is the variable-infiltration curve: a cell's saturated fraction is a function of how wet its upper soil is. Because cells are independent, it produces runoff and baseflow as depths and leaves routing to a separate model.

## What this pack covers

Pinned to VIC **tag 5.1.0, commit `14a371a8`**, sample data submodule `3f2dcb4`. It covers the two drivers that release ships offline: **classic** (ASCII or binary, one file per grid cell) and **image** (NetCDF, MPI). Not the `cesm` or `python` drivers, any fork, parameter values for a basin, or any statement about model results. No runtime cost is measured.

## How to use it — as a person

Start with [card.md](card.md): one page on what a grid cell is, how the drivers differ, and what a time stamp and an output value mean. Then look up what you need by name — two real runs, abridged only by `...`; a key present in both drivers prints one entry per driver:

```
$ tools/hcm_lookup.py --pack vic OUT_RUNOFF
# OUT_RUNOFF  [vic output variable]
  ...
  units: mm
  description: surface runoff
  ...
  default aggregation type (kind): AGG_TYPE_SUM
  ...
  where: vic/drivers/shared_all/src/history_metadata.c:590 (vic@14a371a8)  [driver: both]
  evidence: source_read

$ tools/hcm_lookup.py --pack vic MODEL_STEPS_PER_DAY
# MODEL_STEPS_PER_DAY  [vic global parameter key]
  ...
  where: vic/drivers/classic/src/get_global_param.c:59 (vic@14a371a8)  [driver: classic]
  evidence: confirmed_in_sample_input
# MODEL_STEPS_PER_DAY  [vic global parameter key]
  ...
  where: vic/drivers/image/src/get_global_param.c:56 (vic@14a371a8)  [driver: image]
  evidence: confirmed_in_sample_input
```

When something looks wrong, go to [failures.md](failures.md) by symptom; before a total, a closure or a basin average, read [recipes.md](recipes.md). Before a run, `tools/hcm_check.py check-global-file` (below) names every removed VIC 4 key, unrecognised spelling and violated constraint it can evaluate in a global parameter file, and is quiet on both shipped samples.

## How to use it — as an agent

Read [card.md](card.md) only. Resolve any variable, option or parameter with `tools/hcm_lookup.py --pack vic <NAME>` rather than reading a catalog. Then open [failures.md](failures.md) by symptom, [processes.md](processes.md) by process, or [recipes.md](recipes.md) by task. This README is not part of that path.

## What is in the folder

| File | What it is (hand-maintained unless stated) |
|---|---|
| `card.md` | the one-page orientation, the must-read file |
| `processes.md` | question → option → source → variable, with gates |
| `failures.md` | symptom-indexed entries with remedy and evidence |
| `recipes.md` | bounded procedures with a cost |
| `version.md` | the pin, and how to tell which VIC made a run |
| `sources.md` | what was read, what is not established |
| `catalogs/*.yaml` | generated from the pinned source; the lookup's data |
| `curated/options_overlay.yaml` | documentation-versus-code disagreements |
| `pack.yaml` | file list, commands, known gaps |

## How far to trust it

Every prose statement carries a `path:line` in the pinned tree with its complete gate — which driver, which option values, which code path. Two grades: **read in source** covers almost everything; **confirmed in the sample inputs** means an input-format claim was also checked against the Stehekin files. There is no third grade, because **nothing was verified against model output**. Where documentation, a comment and the code disagree, the pack states what the code does and names the disagreement. The catalogs are mechanical and not exhaustive; `pack.yaml`'s `known_gaps` lists what they could not resolve.

## Regenerate and validate

```
tools/extract_pack.py --pack vic all --source-root <VIC checkout> --out-dir catalogs
tools/validate_catalogs.py --pack-dir <pack-dir> --pack vic --sample-data-root <VIC checkout>/samples/data
tools/hcm_check.py pack-info --pack vic
tools/hcm_check.py check-global-file --pack vic --driver classic --file <global param file>
```
The first rebuilds the catalogs from the pin, the second confronts them with the sample inputs and records the result in `catalogs/MANIFEST.json`, the third prints declared files, known gaps and fact counts, the fourth checks a global parameter file against the pinned key list and the parser's own constraints. The prose is hand-maintained.

## Cite and credit

Cite VIC as its authors ask, and this pack by its pin. The symptom-indexed design of `failures.md` is an idea taken from the KISS project ([arXiv 2605.17856v1](https://arxiv.org/abs/2605.17856)); see [sources.md](sources.md). Links upstream do not relicense it.
