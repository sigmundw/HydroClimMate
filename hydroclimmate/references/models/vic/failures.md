# VIC — failures, by symptom

Read before reporting a result. Source root VIC `14a371a8` (5.1.0); `path:line` relative to it. **run** = `vic/vic_run/src`, **sh** = `vic/drivers/shared_all/src`, **cl** = `vic/drivers/classic/src`, **im** = `vic/drivers/image/src`, **shim** = `vic/drivers/shared_image/src`. All entries are `source_read`; `+ sample` means also confirmed against the sample inputs (Stehekin). **No VIC output exists here**, so nothing is graded as observed. Each entry names its driver. Symptom-indexed entries, each carrying a diagnosis and a remedy, is an idea taken from KISS; see [sources.md](sources.md).

## The run aborts on "you cannot have IMPLICIT=TRUE or EXP_TRANS=TRUE", or a thermal switch is ignored

- **Happening**: `QUICK_FLUX`, `IMPLICIT` and `EXP_TRANS` all default to true, which validation forbids, so a global file that never mentions `FROZEN_SOIL` aborts. That handler resets them — `TRUE` clears `QUICK_FLUX`, `FALSE` the other two — **as its line is parsed**, so `IMPLICIT TRUE` above it is silently overwritten, below it survives.
- **Remedy**: always state `FROZEN_SOIL`, put thermal switches after it, and trust the settings dump.
- **Source**: `sh/initialize_options.c:36-44`; `cl/get_global_param.c:107-140,1239-1250`; `im/get_global_param.c:101-136`. Both. `source_read + sample`

## A global-file key is ignored, or its replacement is not recognised either

- **Happening**: the classic parser makes nineteen VIC 4 spellings fatal with a migration message — eighteen unconditionally, `ARC_SOIL` only when its value is `TRUE`, so `ARC_SOIL FALSE` passes silently. The **image parser has no such block**, so `TIME_STEP`, `SNOW_STEP`, `OUT_DT`, `FORCE_DT`, `BINARY_OUTPUT`, `ARC_SOIL`, `SKIPYEAR`, `MAX_SNOW_TEMP`, `NLAYER`, `ROOT_ZONES`, `SOIL`, `VEGLIB`, `VEGPARAM`, `FORCE_STEPS_PER_DAY`, `GRID_DECIMAL`, `RESOLUTION` and `EQUAL_AREA` only produce a `log_warn`. The classic rejection of `OUT_DT` names `OUTPUT_STEPS_PER_DAY`, which **neither driver accepts**; `SNOW_BAND` is a **boolean** in image, where `SNOW_BAND 5` is fatal.
- **Remedy**: `tools/hcm_check.py check-global-file --pack vic --driver <classic|image> --file <global file>` names every removed VIC 4 key, unrecognised spelling and violated step constraint before a run. Coming from VIC 4 you must **add**, not just remove: the three `*_STEPS_PER_DAY` keys for the old step keys, an `OUTFILE`/`AGGFREQ`/`OUTVAR` block for `OUT_DT` and `PRT_*`, and a `CONSTANTS` file for `MAX_SNOW_TEMP`/`MIN_RAIN_TEMP`. In image the layer, root-zone, veg-class and band counts come from the parameter file's dimensions, the forcing step from its time axis.
- **Source**: `cl/get_global_param.c:517-519,568-682`; `im/get_global_param.c:475-480,522-540`; `shim/vic_start.c:97-103`. `source_read + sample`

## Every record is shifted by one interval

- **Happening**: a record's time coordinate is the **beginning** of its aggregation window — not the end, not the midpoint. `dmy` is itself timestep-beginning and `time_bounds[0]` is set at the window's first model step.
- **Remedy**: in image `time[k]` equals `time_bnds[k,0]`; in classic the leading `YEAR MONTH DAY [SEC]` columns are that instant. Bin left-closed: a record labelled `1949-01-01` under daily aggregation covers 1 January.
- **Source**: `sh/agg_data.c:31-37`; `shim/vic_write.c:197-221`; `cl/write_data.c:41-44,133-148`. Both. `source_read`

## A period total is wrong by the number of steps in the window

- **Happening**: only some variables are summed. `SUM` (precipitation, evaporation and its parts, runoff, baseflow, inflow, melt, refreeze, sublimation, the `DEL*` changes, the lake fluxes) holds the **window total**; `AVG` — the default for anything unlisted, including every energy flux — the window mean; `END` states (`OUT_SWE`, `OUT_SOIL_MOIST`, `OUT_SNOW_DEPTH`, `OUT_ZWT`, `OUT_WDEW`) one instant.
- **Remedy**: image writes the type as `cell_methods`; classic writes none, so use `tools/hcm_lookup.py --pack vic <NAME>` or set it as the fifth `OUTVAR` field.
- **Source**: `sh/vic_history.c:214-303,363-369`; `sh/agg_data.c:44-83`; `sh/input_tools.c:352-378`. Both. `source_read`

## Water fluxes look like rates and do not integrate

- **Happening**: every water flux is written as a **depth in mm over one model step**, with the bare `units` string `"mm"`; energy fluxes are instantaneous W/m2. After aggregation a summed water variable is mm over the window, an averaged one mm **per model step**.
- **Remedy**: establish the model step and aggregation type before dividing anything to "make it a rate"; a `units` string is metadata, the filling code is the arithmetic.
- **Source**: `sh/history_metadata.c:292-297,590-594`; `sh/put_data.c:630-634`; `vic/vic_run/include/vic_def.h:795-796`. Both. `source_read`

## Precipitation, pressure or temperature is off by a constant factor

- **Happening**: VIC's forcing units are not the CF ones. Air temperature is **Celsius**, precipitation a **depth in mm over the forcing step**, pressure and vapour pressure **kPa** on file (both drivers multiply by 1000 on read), radiation W/m2, wind m/s. The shipped image sample global file comments three of them wrongly — `K`, `kg/m2/s` for precipitation, `Pa` — the precipitation one costliest.
- **Remedy**: a mean "temperature" near 273 or "pressure" near 100000 means the file is in K or Pa. Convert before the run; the image driver never reads a `units` attribute.
- **Source**: `cl/vic_force.c:107-118`; `im/vic_force.c:87-164,393-399`. Both. `source_read + sample`

## The run refuses a daily forcing, or reads the wrong part after year one

- **Happening**: VIC 5 removed MTCLIM and disaggregates nothing. The forcing step must equal `SNOW_STEPS_PER_DAY`, a sub-daily forcing must also equal the model step, and the snow step must equal the model step unless the latter is daily; with a sub-daily minimum of four per day, `FORCE_STEPS_PER_DAY 1` is never legal. Image takes one file per calendar year, infers the step from the first two `time` values, requires the `calendar` to match, and at each year boundary resets skip and offset to zero — so every file is assumed to begin 1 January 00:00.
- **Remedy**: disaggregate outside VIC; the only daily-model setup is `MODEL_STEPS_PER_DAY 1` with `SNOW_STEPS_PER_DAY = FORCE_STEPS_PER_DAY >= 4`. `tools/hcm_check.py check-global-file` tests these step constraints.
- **Source**: `cl/get_global_param.c:696-743,977-980`; `cl/read_atmos_data.c:58-65`; `im/vic_force.c:51-73,536-577`. Both. `source_read + sample`

## Half the domain is `_FillValue` although the mask says land

- **Happening**: the active-cell list comes from `run_cell` in the **parameter** file, not `mask` in the domain file; `mask` only asserts that no `run_cell == 1` lies outside it, then is discarded, and every cell with `run_cell != 1` is filled at gather time.
- **Remedy**: edit `run_cell`, not `mask`; both must be `NC_INT`. The domain `frac` variable is read and **never used numerically**, `area` only under `LAKES` — VIC applies no fractional-area weighting.
- **Also**: active cells are spread round-robin over MPI ranks with no inter-cell communication, so fields are decomposition-independent, but every NetCDF read and write funnels through rank 0, and a rank gets no cells once the tasks outnumber the active cells.
- **Source**: `shim/get_global_domain.c:45-120`; `shim/vic_mpi_support.c:1655-1684,1691-1778`; `shim/vic_init.c:1531`; `shim/vic_image_run.c:39-56`. Image. `source_read`

## A multi-level NetCDF variable indexed as `[time, y, x, level]` gives nonsense

- **Happening**: the extra axis sits **between** time and the horizontal axes — `(time, nlayer|node|snow_band|front, y, x)`; plain variables are `(time, y, x)`, `time` unlimited. `frost_area`, `veg_class` and `root_zone` are defined in every history file but used by no variable.
- **Remedy**: index by dimension name; the horizontal names are whatever `DOMAIN_TYPE XDIM`/`YDIM` declared. Set `OUT_FORMAT NETCDF4` on any stream with `COMPRESS`: the default `NETCDF4_CLASSIC` maps to `NC_CLASSIC_MODEL`, on which deflate fails.
- **Source**: `shim/vic_nc_info.c:107-190`; `shim/vic_init_output.c:253-312,441-449`. Image. `source_read`

## `OUT_DISCHARGE` is present and identically zero

- **Happening**: it lives in the **shared** output metadata, so any driver accepts it as an `OUTVAR`, but only the `rout_rvic` extension writes it — image only, and only when built with `ROUT=rout_rvic`; the default is four empty function bodies.
- **Remedy**: treat routing as external unless built with `ROUT=rout_rvic`; even then discharge is non-zero only at outlet cells and defaults to `AVG`, a mean of an instantaneous m3/s.
- **Source**: `vic/drivers/image/Makefile:22-31`; `vic/extensions/rout_stub/src/rout.c:12-39`; `vic/extensions/rout_rvic/src/rout_run.c:53-73`. `source_read`

## The bare-soil tile disappeared, or a tile fraction changed

- **Happening**: `read_vegparam` renormalises. A `Cv` sum above 1 is rescaled with a warning; a sum strictly between 0.99 and 1.0 is **also rescaled to 1**, deleting the bare-soil tile, again only warning. At or below 0.99 the remainder silently becomes a bare-soil tile.
- **Remedy**: make the fractions sum to exactly 1, adding the bare fraction yourself if you want it.
- **Source**: `cl/read_vegparam.c:351-369,441-447`. Classic. `source_read`

## Snow band fractions or band elevations differ from the file

- **Happening**: the reader renormalises both fraction sets whenever their sum is not exactly `1.` (a bare float comparison, so a rounded file warns almost every time); it **overwrites the cell elevation** with the area-weighted band mean when they differ by over 1 m and derives the band temperature offsets from it; then divides the precipitation column by the area fraction, so the internal factor is a per-area multiplier, not what was written.
- **Remedy**: a cell missing from the band file only **warns** and runs with one band (`Cannot find current gridcell`).
- **Source**: `cl/read_snowband.c:33-123`. Classic. `source_read + sample`

## The soil parameter file parses but the values land in the wrong variables

- **Happening**: the classic reader is strictly positional, whitespace-delimited, one line per cell, with option-gated blocks: `ORGANIC_FRACT` inserts 3 x `NLAYER` columns after `soil_dens_min`, `BULK_DENSITY_COMB` a further `NLAYER`, and at the end `SPATIAL_SNOW` adds its slope **before** `SPATIAL_FROST` adds `frost_slope`, `JULY_TAVG_SUPPLIED` last; surplus columns are dropped without a message. `docs/Documentation/Drivers/Classic/SoilParam.md` reverses the last two, omits `BULK_DENSITY_COMB` and promises `#` comment lines the reader does not support.
- **Remedy**: take the column list from the catalogs, not docs.
- **Source**: `cl/read_soilparam.c:49-586`. Classic. `source_read + sample`

## Baseflow parameters were converted and do not match the file

- **Happening**: `BASEFLOW NIJSSEN2001` adds **no column**. `d1..d4` are read into `Ds, Dsmax, Ws, c` and converted in place to ARNO parameters once `max_moist` is known, order-dependently (the new `Dsmax` forms the new `Ds`). Image enumerates **both** `NIJSSEN2001` (`im/get_global_param.c:394-396`) and `ARNO` (`:397-399`) and is fatal on a third spelling (`:400-402`); classic enumerates only `NIJSSEN2001` (`cl/get_global_param.c:414-416`), its `else` assigning `ARNO` silently (`:417-419`), so a typo becomes ARNO and the four columns are taken literally.
- **Remedy**: spell it exactly `ARNO` or `NIJSSEN2001`; the legacy `ARNO_PARAMS` and `NIJSSEN2001_BASEFLOW` keys are fatal in both. Calibrating "Ds" calibrates the converted value.
- **Source**: `cl/read_soilparam.c:693-707`; `shim/vic_init.c:815-829`. Both. `source_read`

## A restart "succeeded" but the state did not belong to that date

- **Happening**: **neither driver compares the state file's time stamp with the run's start date, nor any physics option.** Classic reads the date and discards it, checking only soil layer and thermal node counts; image checks grid size, `veg_class`, `snow_band`, `nlayer`, `frost_area`, `soil_node`, `lake_node`, every coordinate and the node geometry — but not time and not the options.
- **Remedy**: the state file is named for the **end** of the step matching the four `STATE*` fields exactly; an inexact `STATESEC` writes no file and no warning. Check continuity in the data ([recipes.md](recipes.md)).
- **Source**: `cl/check_state_file.c:40-67`; `shim/vic_restore.c:910-1100`; `im/check_save_state_flag.c:24-40`. `source_read`

## A switch was turned on and the run needs inputs nobody asked for

- **Happening**: options are gated on other options and files ([processes.md](processes.md)). The trap is a gate missing without an error: `CARBON` needs the `CATM`, `FDIR` and `PAR` forcings, which classic never checks for, so omitting them is an unhandled read, not a clean message; `COMPUTE_TREELINE` is accepted by the image parser and rejected only later at validation; `SPATIAL_FROST TRUE <n>` multiplies the whole soil water balance by `n` sub-areas.
- **Remedy**: check the gate, not the switch.
- **Source**: `cl/get_global_param.c:1139-1153,1270-1335`; `cl/vic_force.c:145-151`; `im/get_global_param.c:968-970`. `source_read`

## Lake or carbon outputs are zero, enormous, or in the wrong units

- **Happening**: every `OUT_LAKE_*_V` output is m3 and its non-`_V` twin that volume over the cell area, which comes from `RESOLUTION` and `EQUAL_AREA` in classic, the domain `area` in image. It is read only under `LAKES`, but there also shapes the basin depth-area table and the m3 inflows, so a wrong `RESOLUTION` changes the lake **simulation**, not only its outputs ([processes.md](processes.md)). Separately, `OUT_RHET` is **multiplied** by the model step over 86400 s, so it is gC/m2 per step under a `g m-2 d-1` label while `OUT_NPP` stays `g m-2 s-1` and `OUT_NEE` mixes them; `CHANNEL_IN` is documented m3 but consumed as a depth, `CATM` as ppm but consumed as a mixing ratio.
- **Remedy**: check `RESOLUTION` against the grid; supply `CHANNEL_IN` as mm over the cell and `CATM` as ppm x 1e-6; rebuild NEE from consistently scaled terms.
- **Source**: `sh/put_data.c:126,137,329-412,506-510`; `cl/compute_cell_area.c:27-48`; `run/vic_run.c:418-419`. `source_read`
