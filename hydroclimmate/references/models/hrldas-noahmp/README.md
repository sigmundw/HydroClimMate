# HRLDAS / Noah-MP pack

## What this model is

Noah-MP is a land surface model: it solves the water and energy balance of each grid cell, from canopy through snowpack and soil column, and returns the fluxes an atmosphere or hydrology application needs. Its distinguishing feature is that most of its physics is a **choice** — radiative transfer, stomatal resistance, runoff, snow albedo and phenology are each selected by a numbered option, so two runs of "the same model" can differ enormously. HRLDAS is the offline driver that runs it without an atmospheric model, reading gridded meteorology and writing NetCDF history and restart files.

## What this pack covers

Pinned to HRLDAS commit **`d9f5b205`** with the `noahmp` submodule at **`9fbe6724`**. It covers the **offline HRLDAS host**: its namelist, setup file, forcing and output conventions, the physics options as that host exposes them and the offline urban path — not the WRF-coupled driver, any other host or release. Option families read in source but never exercised: `SF_URBAN_PHYSICS` 2 and 3, crops, irrigation, tile drainage, wetland, glacier and every runoff option but the default; `pack.yaml`'s `known_gaps` has the list.

## How to use it — as a person

Start with [card.md](card.md): one page on file naming, dimension order, forcing units, the end-of-step record convention and the time bases that cost a factor of two. Then look up what you need — two real runs, abridged only by `...`:

```
$ tools/hcm_lookup.py --pack hrldas-noahmp SFCRNOFF
# SFCRNOFF  [output variable]
  NOTE: this is the HISTORY name; in restart output the same field (driver array NoahmpIO%SFCRUNOFF) is written as `SFCRUNOFF`
  ...
  units: mm
  kind: accumulated_since_start  [true_kind (curated): accumulated_since_start]
  dims (file order, observed -- reverse of source-declared): ['Time', 'south_north', 'west_east']
  ...
  evidence: both

$ tools/hcm_lookup.py --pack hrldas-noahmp SNOW_ALBEDO_OPTION
# snow_albedo_option  [namelist option]
  ...
  allowed_values: 1=BATS, 2=CLASS, 3=SNICAR
  where: noahmp/drivers/hrldas/NoahmpReadNamelistMod.F90:82 (noahmp@9fbe6724)
  evidence: source_read
# OptSnowAlbedo  [physics option]  (matched via alias 'snow_albedo_option' (by namelist key))
  1 = BATS  ->  SnowAgingBats @ noahmp/src/SurfaceAlbedoGlacierMod.F90:62; also: SnowAlbedoBats @ ...:76, SnowAgingBats @ ...SurfaceAlbedoMod.F90:113, ...
```

When something looks wrong, go to [failures.md](failures.md) by symptom; before a total, a budget or an area statistic, read [recipes.md](recipes.md).

## How to use it — as an agent

Read [card.md](card.md) only. Resolve any variable, option or parameter with `tools/hcm_lookup.py --pack hrldas-noahmp <NAME>` rather than reading a catalog. Then open [failures.md](failures.md) by symptom, [processes.md](processes.md) by process or [recipes.md](recipes.md) by task. This README is not part of that path.

## What is in the folder

| File | What it is |
|---|---|
| `card.md` | hand-maintained: the one-page orientation, the must-read file |
| `processes.md` | hand-maintained: question → switch → module → variable |
| `failures.md` | hand-maintained: symptom-indexed entries with remedy and evidence |
| `recipes.md` | hand-maintained: bounded procedures with measured cost |
| `version.md` | hand-maintained: the pin, and which build made a run |
| `sources.md` | hand-maintained: what was read, what is not established |
| `catalogs/*.yaml` | generated from the pinned source; the lookup's data |
| `curated/*.yaml` | hand-maintained: variable kinds, switch effects, checks, overlays |
| `pack.yaml` | hand-maintained: file list, regeneration commands, known gaps |

## How far to trust it

Every statement carries a `path:line` in the pinned trees, with the option values and code path gating it. Three grades are used, each entry says which: **read in source**; **observed**, measured on real files from a build of this pin; and **both**. Real output does exist here — a paired offline run, urban physics off and on — so the fill patterns, dimension order on file, accumulator monotonicity and the read costs in `recipes.md` are measured, not inferred. What it did not exercise is in `known_gaps`; anything about another commit, host or release is not established. Where the namelist docs and the code disagree, the pack states the code's behaviour: the annotated defaults are not authoritative. The curated overlays cover 70 of 179 history variables.

## Regenerate and validate

```
tools/extract_pack.py all --source-root <ckt> --out-dir catalogs
tools/validate_catalogs.py --pack-dir <d> --ldasout <f> --restart <f> --ldasin <f> --apply
tools/hcm_check.py pack-info --pack hrldas-noahmp
```
The catalogs regenerate byte-identically from the pin; the prose is hand-maintained.

## Cite and credit

Cite Noah-MP and HRLDAS as their authors ask, and this pack by its pin. The symptom-indexed design of `failures.md` is an idea taken from the KISS project ([arXiv 2605.17856v1](https://arxiv.org/abs/2605.17856)); see [sources.md](sources.md). Links upstream do not relicense it.
