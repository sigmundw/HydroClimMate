# HRLDAS / Noah-MP — bounded recipes, with cost

Each recipe: inputs → minimal sufficient check → steps → expected cost → what invalidates the
shortcut. Costs are measured orders of magnitude on one parallel filesystem, for ~40 MB files
holding 24 hourly records of ~100 variables; **filesystem speed varies by an order of magnitude —
treat every number as a range**. Conventions and traps: [card.md](card.md),
[failures.md](failures.md).

## 1. Period total from an accumulated field

**Inputs**: the first and last history record of the period; the variable's true `kind` from
`catalogs/kinds_overlay.yaml`. Accumulators: `SFCRNOFF`, `UGDRNOFF`, `ACSNOW`, `ACSNOM`,
`QTDRAIN`; with `IOPT_IRR > 0` also `IRSIVOL`/`IRMIVOL`/`IRFIVOL`/`IRELOSS`/`IRRSPLH`; with
`IOPT_RUNSUB == 5` also `RECH`/`QRFS`/`QSLAT`/`QSPRINGS`. **`EFLXB` is not one** — it is one soil
timestep of energy, so differencing two of its records returns a meaningless number.
**Minimal check**: read one cell's series at a few dates, confirm it is non-decreasing and that
no restart from an unrelated state falls inside the period.
**Steps**: total = value(end record) − value(start record), masking `< -1e30`. Two records,
not the whole period.
**Cost**: two file opens, < 0.1 s; monotonicity at ~50 sampled dates, ~2-5 s.
**Invalidated by**: a decrease anywhere in the interval (reset, restart from a different state,
or the variable is not an accumulator); a period starting at the run's first record.

## 2. Daily or seasonal mean from an instantaneous field

**Inputs**: one variable, all records in the period; the time axis decoded from `Times`.
**Minimal check**: confirm `kind` is `instantaneous` (not accumulated, not per-timestep), and
that the record spacing from `Times` is constant.
**Steps**: drop the run's first record; mask `< -1e30`; group by day using the **end-stamped**
convention (a `00:00` record belongs to the previous day); take the arithmetic mean — with a
constant output interval that is the time mean.
**Cost**: one variable, all records per file, ~0.15 s/file.
**Invalidated by**: a variable only defined part of the time (`ALBEDO` is `-9999` at night,
`ALBSFC*` are 0 then — see [failures.md](failures.md)); an irregular output interval; mixing a
`.loop*` spin-up file into the series.

## 3. Paired-run difference that separates a switch's direct effect from its side effects

**Inputs**: run A (switch off), run B (switch on), identical forcing, setup file, start time and
all other options; and a **control** run C applying only the switch's *side effect*.
**Minimal check**: diff the two namelists and confirm exactly one line differs; confirm both
runs' first output records are identical (same initial state).
**Steps**:
1. Identify from [processes.md](processes.md) which fields the switch actually writes. For
   `SF_URBAN_PHYSICS = 1` the urban routine weights exactly eight: `ALBEDO`, `HFX`, `QFX`, `LH`,
   `GRDFLX`, `TSK`, `QSFC`, `UST`. **Only `ALBEDO`, `HFX`, `LH`, `GRDFLX` exist in history
   output; `QSFC` is restart-only; `QFX`, `TSK`, `UST` are written nowhere** — so the comparison
   set you can actually read is four variables, plus `QSFC` from paired restarts.
2. Identify the side effect. Turning the switch on also reassigns the column's vegetation class
   to `NATURAL`, forces `GVFMAX` to 96%, and — because `FlagUrban` is set only when
   `SF_URBAN_PHYSICS == 0` — **removes** Noah-MP's internal urban treatment (95% impervious top
   layer, urban soil and thermal parameters, ground-thermal/roughness/ground-evaporation
   branches, the `Q2MB` override, no-carbon, `FVEG = 0`). It also runs pedotransfer where the
   urban branch skipped it, but **only if `SOIL_DATA_OPTION == 3`**; under 1/2/4 no column runs
   pedotransfer either way, so that term is absent from the comparison.
3. Build control run C as A plus only that side effect: the `NATURAL` class and `GVFMAX = 96` on
   the same cells, urban physics still off.
4. Report B−C as the switch's direct effect and C−A as the side effect. B−A is their sum and
   must not be presented as the switch's effect.
5. Check scaling against `FRC_URB2D`: the weighting is linear in it, so a direct effect that
   does not vary with the fraction is not from the tile weighting.
**Cost**: two or three file reads per variable per date; the third run is the expensive part and
needs its own authorization.
**Invalidated by**: any second namelist difference; different forcing; comparing variables the
switch never writes (B−C should then be ~0, and a residual is a side effect you have not found).

## 4. Area statistics on this grid

**Inputs**: the setup file (`HRLDAS_SETUP_FILE`) — `MAP_PROJ`, `DX`, `DY`, `XLAT`, `XLONG`,
`MAPFAC_MX`, `MAPFAC_MY`, `XLAND`, `IVGTYP`.
**Minimal check**: read `MAP_PROJ` and `MAPFAC_MX`/`MAPFAC_MY`. If either map factor departs
from 1, the metre-equivalent `DX`/`DY` is not the true local spacing — that is
`DX/MAPFAC_MX` by `DY/MAPFAC_MY`.
**Steps**: cell area = `(DX/MAPFAC_MX) * (DY/MAPFAC_MY)`; domain mean = area-weighted mean over
unmasked land cells; domain total = sum of (value x area), converting units if the value is a
depth (mm x m2 → litres).
**Observed example**: a regular latitude-longitude grid (`MAP_PROJ = 6`) with `MAPFAC_MY = 1.0`
and `MAPFAC_MX = 1/cos(lat)`; the metre-valued `DX`/`DY` were the nominal equivalent of the
degree spacing, not the true east-west spacing. Over a small latitude span the unweighted mean
was within a few tenths of a percent of the weighted one — a property of that domain, not the
model.
**Cost**: one setup-file read, negligible.
**Invalidated by**: a domain spanning enough latitude that cos(lat) varies appreciably; a subset
selected by land class (recheck indices against `MMINLU`); using `IVGTYP` as the mask without
also excluding `-1e33` float fill.

## 5. Mass or energy budget closure

**Inputs**: the stores and boundary fluxes for the chosen scope, at two times.
**Minimal check**: write the scope first. A column water budget is
`ΔSNEQV + ΔCANLIQ + ΔCANICE + Δ(soil water) + ΔWA` versus
`precip − ET − ΔSFCRNOFF − ΔUGDRNOFF − ΔQTDRAIN`; convert `SOIL_M` to a depth with `DZS`.
**Precipitation breaks this recipe**: take it from the `LDASIN` forcing, from `ACC_PRCP`
(`NOAHMP_OUTPUT > 0`), or from `RAINRATE` **with the recipe-8 correction**.
**Steps**: difference the accumulators (recipe 1), difference the states, integrate the true
mm/s rates (`ECAN`, `ETRAN`, `EDIR`) over the output interval, then report the residual as a
fraction of the largest term.
**Cost**: two records for accumulators and states; a full pass only for the rate terms.
**Invalidated by**: a term outside your scope that the model moved — the 5000 mm snow cap
discards mass on ordinary land; the capped aquifer moves water into the bottom soil layer; the
urban soil-wetting block adds water unaccounted; tile drainage and irrigation act only when
their gates are open; and `ΔWA` is meaningful **only under `SUBSURFACE_RUNOFF_OPTION = 1`** —
under 5 `WA` is forced to 0.0 every MMF call, and `WT` is never updated outside 1. If a term is
not written, report **partial** closure and name it.

## 6. Reading thousands of small files

**Inputs**: the file list, one variable name, the records you need.
**Minimal check**: time ten files and extrapolate; confirm from `Times` how many records each
file holds.
**Steps**, cheapest first:
1. **One variable, one record per file** where a daily value suffices: ~0.03 s/file.
2. **One variable, all records**: ~0.15 s/file.
3. **All variables**: ~0.7 s/file — roughly 20x (1) for the same files.
4. Parallel readers over disjoint file ranges scale until the filesystem saturates; 4-8 workers
   is usually enough, and more can be slower on a shared parallel filesystem.
**Cost control**: open each file once and take everything you need; a second pass costs the same
as the first, so concatenating per variable pays off after about two passes.
**Invalidated by**: a variable that must be differenced across a file boundary (you need the
last record of file *n* and the first of *n+1*); `SPLIT_OUTPUT_COUNT = 1`, where per-file
overhead dominates.

## 7. When a full pass is NOT needed

- A **period total of an accumulated variable**: two records (recipe 1), not the period.
- **Does run B differ from run A at all**: compare the last record of each; bit-identical means
  the switch did nothing on those variables.
- **Does the configuration match this pack**: namelist, setup header, one output header
  ([version.md](version.md)). No data read.
- **Which variables exist, with units and dimensions**: one file header, or
  `tools/hcm_lookup.py --pack hrldas-noahmp <NAME>`.
- **Where a variable comes from**: [processes.md](processes.md), not a sensitivity run.
- A full pass **is** needed for: time-mean or extreme statistics of an instantaneous field, event
  detection, and integrating a rate.

## 8. Period total precipitation (and any per-timestep depth)

**Inputs**: `RAINRATE` from history, or the `LDASIN` forcing, or `ACC_PRCP` with
`NOAHMP_OUTPUT > 0`; and `NOAH_TIMESTEP`, `OUTPUT_TIMESTEP` from the namelist.
**Minimal check**: read both timesteps. `RAINRATE` is a **depth per `NOAH_TIMESTEP`** written
once per `OUTPUT_TIMESTEP`, so records are a *sample*, not an integral.
**Steps**: if `OUTPUT_TIMESTEP == NOAH_TIMESTEP`, sum the records. Otherwise multiply the sum by
`OUTPUT_TIMESTEP / NOAH_TIMESTEP`, or sum the forcing (mm/s x `FORCING_TIMESTEP`) instead. The
same rule applies to any per-timestep depth. True mm/s rates (`QMELT`, `ECAN`, `ETRAN`, `EDIR`)
need no such factor, but they are **instantaneous samples**: summing x `OUTPUT_TIMESTEP` is
rectangle-rule quadrature, measured +0.37% against the matching accumulator over a month, with
error growing with `OUTPUT_TIMESTEP/NOAH_TIMESTEP` and the variable's variability — use the
accumulator where one exists.
**Cost**: as recipe 2 (one variable over the period).
**What invalidates it**: measured with a 1800 s model step and hourly output, the record sum was
exactly half the forcing total. A result that is a clean fraction of the forcing is this bug.
