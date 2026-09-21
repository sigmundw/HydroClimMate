# HRLDAS / Noah-MP — failures, by symptom

Read before reporting a result. Source root = HRLDAS `d9f5b205` + `noahmp` `9fbe6724`;
`path:line` relative to it. **drv** = `hrldas/IO_code/module_NoahMP_hrldas_driver.F`,
**io** = `hrldas/IO_code/module_hrldas_netcdf_io.F`, **nml** = `hrldas/run/README.namelist`,
**hdrv** = `noahmp/drivers/hrldas`, **src** = `noahmp/src`. Evidence tag per entry:
`source_read`, `observed` (measured on real files from this commit), `both`. Indexing failures
by symptom with diagnosis and remedy is an idea taken from KISS; see [sources.md](sources.md).

## Everything over water is a huge negative number, or the mean is nonsense

- **Happening**: `missing_value = -1.E33` is a **global** attribute only; no variable carries
  `_FillValue`/`missing_value`, so netCDF4/xarray auto-masking does nothing. Float fields are
  `-1.E33` where `IVGTYP == ISWATER`.
- **Confirm**: `d.ncattrs()` has `missing_value`; a variable's attributes are only
  `MemoryOrder`, `description`, `units`, `stagger`.
- **Remedy**: mask on `< -1e30`, or build one land mask from `IVGTYP`. **Integer fields
  (`IVGTYP`, `ISLTYP`, `ISNOW`) go through a writer with no mask at all** and hold plausible
  values over the ocean; in **restart** files the 2-D writer also skips the mask while the 3-D
  writer always masks — observed: restart `SNEQV` = 0.0 on water, restart `SMC` = `-1e33`.
- **Source**: io:3147,3402-3448,3471-3477,3493-3518,3526-3555. `both`

## A 3-D field indexed as `[time, layer, y, x]` gives garbage

- **Happening**: the layer axis is written **between** the horizontal axes: in NetCDF/python
  order the shape is `(Time, south_north, <layer>, west_east)` (`MemoryOrder = "XZY"`).
- **Confirm / Remedy**: print `.dimensions` and index by dimension name, never by position.
- **Source**: io:3433,3436. `both`

## The first record of a run has fluxes of -9999

- **Happening**: the loop is `do ITIME = 0, NTIME` with physics skipped at `ITIME==0`; output
  is written anyway, so the first record is the initial state with fluxes never computed,
  holding `undefined_real = -9999.0`.
- **Confirm**: observed — about half the data variables (`HFX`, `LH`, `FSA`, `FIRA`, `GRDFLX`,
  `ALBEDO`, `EMISS`, `TRAD`, `FSNO`, …) were exactly `-9999.0` on every land cell of that
  record; states and `RAINRATE` were real.
- **Remedy**: drop the first record, or set `SKIP_FIRST_OUTPUT = .true.` (nml:33). A
  `-1e30` mask does **not** remove `-9999`.
- **Source**: drv:1008,1129,1131-1133; `noahmp/utility/Machine.F90:22`;
  `hdrv/NoahmpIOVarInitMod.F90:646`. `both`

## The file named 01:00 holds records into the next day, and my daily mean is shifted

- **Happening**: a file name's stamp is its **first** record and the file holds
  `SPLIT_OUTPUT_COUNT` records (the `ITIME==0` file is special-cased to one). Each record is
  stamped with the **end** of the step it represents: a run started at `00:00` with a 1-hour
  output step has its first non-initial record stamped `01:00`, covering `00:00`-`01:00`.
- **Confirm / Remedy**: build the time axis from `Times`, never from file names or a
  records-per-file assumption; when binning to days, a `00:00` stamp belongs to the previous day.
- **Source**: io:3111-3115,3247-3256; drv:1131,1406-1407. `both`

## Runoff "per day" is enormous and grows monotonically

- **Happening**: `SFCRNOFF` and `UGDRNOFF` are **accumulated since the start of the run, or
  since the restart it resumed from**, in mm; zeroed only at initialisation, carried in
  restart files, never reset in the time loop. `ACSNOW`, `ACSNOM`, `QTDRAIN` behave the same
  way; so do `IRSIVOL`/`IRMIVOL`/`IRFIVOL`/`IRELOSS`/`IRRSPLH` when `IOPT_IRR > 0`, and
  `RECH`/`QRFS`/`QSLAT`/`QSPRINGS` when `IOPT_RUNSUB == 5`. **`EFLXB` is not one of them**: it is
  energy through the soil bottom during one soil timestep, so differencing it is meaningless.
- **Confirm**: one cell's series must be non-decreasing (verified over five years).
- **Remedy**: difference successive records. Across a restart boundary, check whether the
  accumulator was continued or restarted before differencing.
- **Source**: drv:1177-1178,389-390,1498-1499; `hdrv/NoahmpIOVarInitMod.F90:717-718`;
  `hdrv/WaterVarOutTransferMod.F90:69-70,122,162,165`; `EnergyVarOutTransferMod.F90:104`. `both`

## `ACC_*` variables do not integrate to anything sensible

- **Happening**: `ACC_*` is not a since-start accumulator. Each accumulates **within one soil
  timestep** and is zeroed on the step after the soil update; all appear only when
  `NOAHMP_OUTPUT > 0` (nml:287-289). With `SOIL_TIMESTEP = 0` (the default) they are single-step
  quantities. `EFLXB` is the same shape: one soil timestep, J/m2.
- **Confirm / Remedy**: use them inside a step, not for period totals.
- **Source**: `hdrv/NoahmpDriverMainMod.F90:60-90`; drv:1289,1306-1314. `source_read`

## A restart file's variables are not where you expect

- **Happening**: restart files use **different spellings** and carry `description = "-"`,
  `units = "-"` for every variable: `SFCRUNOFF`/`UDRUNOFF` vs `SFCRNOFF`/`UGDRNOFF`; `ACMELT` vs
  `ACSNOM`; `SMC` vs `SOIL_M`; `ZSNSO` (on `sosn_layers`) vs `ZSNSO_SN` (on `snow_layers`); the
  radiation dimension is `rad_layers`, not `rad_num`. 2-D restart floats can also hold `-9999`
  where a field was never computed (measured on `QSFC`).
- **Confirm / Remedy**: list the restart variables and dimensions and map them with
  `catalogs/restart.yaml`; never reuse history names.
- **Source**: drv:385,389-390,1455-1474; io:3728-3738. `both`

## A restart file exists, so the run "restarted successfully"

- **Happening**: a file name proves a write, not that the intended state was read and
  advanced. `RESTART_FILENAME_REQUESTED` must be set to restart. **In this code any
  `RESTART_FREQUENCY_HOURS <= 0` — including 0 — writes a restart at the start of each month**
  (drv:1395-1399), so plausible files appear even from a run that never restarted. nml:34-36
  claims 0 writes none; **the code contradicts it** — trust drv:1390-1399.
- **Confirm / Remedy**: read `Times`/`START_DATE` in the restart, then check the first history
  record of the continued run and an accumulator's continuity across the boundary — state
  time, configuration and forcing continuity, not the file name.
- **Source**: nml:17,34-36; drv:338-340,1390-1399. `both`

## Snow water equivalent does not equal the sum of the snow layers

- **Happening**: in the zero-layer state (`ISNOW == 0`) a thin pack is a scalar mass while
  `SNICE`/`SNLIQ` are exactly zero; a layer is created only at `SnowDepth >= 0.025` m and the
  pack collapses back below the same threshold.
- **Confirm**: observed in autumn records — many cells with `ISNOW == 0`, `SNEQV` of a few mm and
  layer sums exactly 0.0; where `ISNOW < 0` the identity held.
- **Remedy**: check `ISNOW` before using any layer identity; use `SNEQV` for mass.
- **Source**: `src/SnowfallBelowCanopyMod.F90:57`; `src/SnowLayerCombineMod.F90:190-193`.
  `both`

## Snow mass stops growing at a round number

- **Happening**: two caps. 2000 mm applies **once, at cold start only**. A 5000 mm cap
  (`SWEMAXGLA_TABLE`) fires **every step on ordinary land, not only glaciers**, taking the excess
  from the bottom snow layer.
- **Confirm / Remedy**: look for cells pinned at 5000 mm and non-zero `ACC_GLAFLW` off glaciers;
  exclude them from a mass budget or report the removed flux.
- **Source**: `hdrv/NoahmpInitMainMod.F90:68-70`; `src/SnowWaterMainMod.F90:116-121`;
  `noahmp/parameters/NoahmpTable.TBL:438`. `source_read`

## Albedo is 0 at night or -9999, and a daily mean albedo is meaningless

- **Happening**: the albedo block runs only when the cosine of the solar zenith angle is
  positive, over fields initialised to 0.0, so `ALBSFC*`/`ALBSOIL*`/`ALBSNOW*` are zeros at
  night; grid `ALBEDO` is a flux ratio set to `undefined_real` (-9999) with no downward shortwave.
- **Confirm / Remedy**: plot one cell's `ALBEDO` with `COSZ`; compute albedo as
  (sum reflected)/(sum incoming) over daylight records, never as a mean of the ratio.
- **Source**: `src/SurfaceAlbedoMod.F90:92-109,124`; `src/EnergyMainMod.F90:343-346`. `both`

## A paired urban on/off run differs in snow, soil or radiation

- **Happening**: with `SF_URBAN_PHYSICS > 0` the column's **vegetation type is reassigned to the
  table `NATURAL` class** and `GVFMAX` is forced to 96% before Noah-MP runs; `FlagUrban` is set
  `.true.` **only in the `SF_URBAN_PHYSICS == 0` branch**, so with urban physics ON the column
  also **loses** Noah-MP's internal urban treatment (95% impervious top layer, urban soil and
  thermal parameters, ground-thermal/roughness/ground-evaporation branches, the `Q2MB` override,
  no-carbon, `FVEG = 0`); and **only under `SOIL_DATA_OPTION == 3`** it now runs pedotransfer
  where the urban branch skipped it — under 1/2/4 no column runs it at all. The routine weights
  by `FRC_URB2D` **exactly eight fields** (option 1, SLUCM): `ALBEDO`, `HFX`, `QFX`, `LH`,
  `GRDFLX`, `TSK`, `QSFC`, `UST` — of which only the first four exist in history output. `EMISS`
  is **not** weighted there, and no snow or soil variable is in the argument list at all.
- **Confirm**: measured on the urban cells of a paired run — `FVEG` 0.000 off vs 0.960 on, while
  `IVGTYP` in the **output is identical in both runs** (the swap is to the internal `VegType`).
  That run used `SOIL_DATA_OPTION = 1`, so it is no evidence about pedotransfer.
- **Remedy**: attribute differences in `SNEQV`, `SOIL_M`, `TRAD`, `FSA` to the reassignment, not
  urban canopy physics; options 2/3 weight a larger set (including `emiss`), so re-derive there.
- **Source**: `src/ConfigVarInitMod.F90:66`; `hdrv/NoahmpDriverMainMod.F90:153-154`;
  `hdrv/ConfigVarInTransferMod.F90:155-165`; `src/SoilWaterMainMod.F90:143`;
  `hdrv/WaterVarInTransferMod.F90:299`; `urban/wrf/NoahmpUrbanDriverMainMod.F:522-536`. `both`

## Urban physics is on but nothing changes

- **Happening**: the driver presets `FRC_URB2D = 0.0` and reads it from the setup file; if the
  variable is absent the reader only prints `"... Using default table values."` and leaves zeros.
  The URBPARM table value is substituted later, in `urban_var_init`, and only on urban classes.
- **Confirm / Remedy**: check `FRC_URB2D` exists and is non-zero where `IVGTYP` is urban; the
  weighting is linear in it.
- **Source**: drv:316-317; io:934-941; `urban/wrf/module_sf_urban.F:2794-2804`. `source_read`

## Cells selected with the wrong land-use class number

- **Happening**: class indices come from the parameter table and differ by dataset: MODIS
  `ISWATER=17`, `ISURBAN=13`, `NATURAL=14`, `ISCROP=12`, `ISICE=15`; USGS 16, 1, 5, 2, 24;
  `URBTYPE_beg=50` and LCZ 51-61 are urban in both.
- **Confirm / Remedy**: read `MMINLU` and resolve indices from it plus the parameter table.
- **Source**: `noahmp/parameters/NoahmpTable.TBL:43-51,239-247,257`; io:3164. `both`

## A switch was turned on and the output is identical

- **Happening**: several options are silently inert. Tile drainage does nothing unless the
  surface runoff option is 3 **and** the tile fraction exceeds 0.3 (opt 1) or 0.1 (opt 2).
  Inconsistent surface/subsurface runoff options are neither corrected nor fatal — only a
  per-cell, per-step warning. `SNICAR_*` needs `SNOW_ALBEDO_OPTION = 3`;
  `DVIC_INFILTRATION_OPTION` needs surface option 8; `PCP_PARTITION_OPTION = 4` needs
  `FORCING_NAME_SN`.
- **Confirm / Remedy**: check the gate, not just the namelist line.
- **Source**: `src/SoilWaterMainMod.F90:191-195`; `hdrv/ConfigVarInTransferMod.F90:188-191`;
  nml:173-176,291. `source_read`

## A variable you remember from another Noah-MP does not exist here

- **Happening**: names differ between hosts and generations. Here the driver writes
  `SFCRNOFF`/`UGDRNOFF` while the internal arrays — and the restart file — use
  `SFCRUNOFF`/`UDRUNOFF`. Friction velocity is internal only (**no `UST` output variable**), and
  there are **no urban-specific history variables at all**.
- **Confirm / Remedy**: list the variables present and resolve names with `tools/hcm_lookup.py`.
- **Source**: drv:1177-1178,1366; `src/EnergyVarType.F90:129-130`. `both`

## Precipitation totals, or my water budget, are off by a factor

- **Happening**: the only precipitation field in default history output is `RAINRATE`, and it is
  **not a rate**: the driver multiplies the mm/s forcing by the model step before writing, so it
  is a **depth per `NOAH_TIMESTEP`** (`units = "mm/timestep"`) sampled once per
  `OUTPUT_TIMESTEP`. Summing records undercounts by
  exactly `NOAH_TIMESTEP / OUTPUT_TIMESTEP` — measured ratio 0.500000 with a 1800 s model step
  and hourly output.
- **Confirm**: compare a period sum of `RAINRATE` against the same period summed from `LDASIN`.
- **Remedy**: multiply the sum by `OUTPUT_TIMESTEP / NOAH_TIMESTEP`, or take precipitation from
  the forcing or from `ACC_PRCP` (`NOAHMP_OUTPUT > 0`). True mm/s rates (`QMELT`, `ECAN`,
  `ETRAN`, `EDIR`) are **instantaneous samples**: summing x `OUTPUT_TIMESTEP` is rectangle-rule
  quadrature — close (+0.37% vs the matching accumulator over a month) but not exact, the error
  growing with `OUTPUT_TIMESTEP/NOAH_TIMESTEP` and the variable's variability.
- **Source**: drv:913,1164. `both`

## `ZWT`, `WA` or `WT` never change

- **Happening**: all three are written every record under every option, but updated by almost
  none. `ZWT`: under `SUBSURFACE_RUNOFF_OPTION` 1, 2 and 5. `WA`: **1 only** — under 5 it is
  **forced to 0.0 at every MMF call**, i.e. identically zero. `WT`: **1 only**, never updated
  under 2 or 5. Under 3 (the executable default), 4, 6, 7, 8 the scheme is
  `RunoffSubSurfaceDrainage`, which touches none of them, so all three keep their initial values
  for the whole run. `SMCWTD`, `RECH`, `DEEPRECH`, `QRF*`, `QSPRING*`, `QLAT`/`QSLAT` are not
  written at all outside option 5.
- **Confirm**: measured constant across a whole free-drainage run.
- **Remedy**: no water-table analysis on a free-drainage run; `ΔWA` is meaningful only under 1.
- **Source**: `src/SoilWaterMainMod.F90:140,245,248-250,259`;
  `src/GroundWaterTopModelMod.F90:146-154,197-198`; `src/WaterTableDepthSearchMod.F90:71`;
  `src/RunoffSubSurfaceShallowMmfMod.F90:46`; drv:1348-1358. `both`
