# mizuRoute — failures, by symptom

Read before reporting a result. Source mizuRoute `28514dea` (tag `v3.1.1`); a bare `file:line` means `route/build/src/file.f90`, **sa** = its `standalone/`, **ctl** = `route/settings/SAMPLE.control`. All entries are `source_read`, `+ sample` also confirmed in the sample control files; **no mizuRoute input or output data exists here**, so nothing is graded as observed, and each entry names its mode. The symptom index, each entry carrying a diagnosis and a remedy, is an idea taken from KISS ([sources.md](sources.md)).

## The run stops at once with "unexpected text in control file provided"

- **Happening**: the parser has no fall-through: an unrecognised `<key>` is fatal, as is a tab in a value, as is a data line with no `!`, which aborts with "problem disentangling cLines".
- **Confirm**: the message names the offending key; the log above lists every key accepted so far.
- **Remedy**: the shipped `ctl` is **not runnable as it stands**: its lines 150-154 use five `<*inflow>` keys that do not exist; the one real key is `<outputInflow>`, which turns all five on. The docs offer five more rejected keys ([sources.md](sources.md)).
- **Source**: `read_control:100-118,262,374-378`; `ctl:150-154`. Both. `source_read + sample`

## Discharge is out by 1000, by 86400, or by both

- **Happening**: the runoff units come **from the control file, never from the file's `units` attribute**. `<units_qsim>` must contain a `/`, the length part `m|mm`, the time part `d|day`, `h|hr|hour` or `s|sec|second`; anything else is fatal. Both factors are applied per HRU into the reach.
- **Confirm**: recompute one reach; `sum_h(area_h * runoff_h) * length_conv * time_conv` must equal its `instRunoff` in m3/s.
- **Remedy**: state the units the producer wrote. `<scale_factor_runoff>` and `<offset_value_runoff>` rescale the input first; a zero scale with no offset **skips the read and sets runoff to zero** rather than erroring.
- **Source**: `read_control:443-474`; `process_remap:402-410`; `sa/get_basin_runoff:71-74`. Both. `source_read + sample`

## `<dt_ro>` in the control file has no effect, or the run aborts on time spacing

- **Happening**: the setup reads every input file's time axis, converts it to seconds, requires uniform spacing across the whole concatenated series to within `maxTimeDiff` = `1/secprday` ~ 1.16e-5 s (the differences are in seconds, `public_var:28`), and **overwrites `<dt_ro>` with that spacing**. The control value is never used.
- **Confirm**: the abort text is "time spacing in netCDF input(s) is not consistent within tolerance"; it fires on overlaps and gaps between files as readily as inside one.
- **Remedy**: fix the time axis, not the key. Files are concatenated in the order the list (or `ls` of the wildcard) gives; no check reorders them.
- **Source**: `sa/model_setup:327-367,488-502`. Standalone. `source_read`

## Half the network produces no water, and nothing said so

- **Happening**: that every river-network HRU was found in the mapping file (or, without remapping, the runoff file) is checked **only under `<debug> T`**; otherwise an absent HRU contributes nothing, ever.
- **Confirm**: set `<debug> T` for one step and read the three printed counts (network, mapping, matched); the run aborts if the first and third differ.
- **Remedy**: compare the id sets before the run; matching lengths prove nothing: the match is by id, not position.
- **Source**: `sa/model_setup:806-857`. Standalone. `source_read`

## Remapped runoff volume does not match the land model's

- **Happening**: the remapper renormalises. Source cells at or below `-1e-6` are dropped from the weighted sum and the weight sum, and if the surviving weights miss 1 by more than `1e-6` the result is **divided by their sum**: an HRU covered 10% by valid source cells gets the mean of that 10%, not 10% of it.
- **Confirm**: feed a constant field and compare `sum(area * basRunoff)` with that constant times the network area; lost coverage shows as no loss at all.
- **Remedy**: audit the mapping weights first: the exclusion is a bare value test, so `-9999` over ocean is handled, `0` is not.
- **Source**: `process_remap:128-150,231-255`. Both. `source_read`

## "mismatch in HRU ids for polygons in the runoff layer"

- **Happening**: for every overlap entry the 1-D remapper checks its stored id against the id at that position of the runoff file's id array, aborting on a mismatch. It fires when the runoff file's HRU order differs from the one the mapping was built against.
- **Confirm / Remedy**: rebuild the mapping against the runoff file you will use, or reorder it. The grid path has no such check: a 2-D input is addressed by the stored `i_index`/`j_index` alone, so a transposed or re-gridded input is read at the wrong cells, silently.
- **Source**: `process_remap:217-229,107-126`. Both. `source_read`

## A network variable is "not found", or its values are ignored

- **Happening**: names are configurable, and only the seven listed in [recipes.md](recipes.md) are required. Channel geometry differs: under `<hydGeometryOption> 0`, the default, each of `width`, `man_n`, `depth`, `sideSlope`, `floodplainSlope` is used **only if a variable of that name exists**, else computed — a misspelled `<varname_width>` is not an error, the file's widths are simply replaced by `wscale*sqrt(totalArea)`. A file `depth` is discarded outright under `<floodplain> F`, the default, every reach's depth being overwritten after the read (`public_var:101`, `process_ntopo:189-194`; [recipes.md](recipes.md)).
- **Confirm**: change a value that should matter by a factor of 10 and rerun one step; if nothing moves, it was never read.
- **Remedy**: the docs give the default as `1`, the code `0` (`public_var:192`) — the code decides ([sources.md](sources.md)). With `<is_lake_sim> T`, `islake` and `lakeModelType` are also required and their absence *is* fatal.
- **Source**: `read_streamSeg:322-333,336-340`; `process_ntopo:176-187,189-194`. Both. `source_read`

## An output variable you asked for is not in the file

- **Happening**: a history variable is silenced when its routing method is absent from `<route_opt>`, when `<floodplain>` is off (`*floodVolume`, `*height`), under `<doesBasinRoute> 0` (`instRunoff`), or when `<tracer>` is off; `<outputInflow>` is all-or-nothing across methods. Most flags also start **off**: only the five `*routedRunoff`, `IRFvolume` and `basRunoff` default to true (`popMetadat:238-271`); `instRunoff`, `sumUpstreamRunoff`, the other `*volume`, `*height`, `*floodVolume` and `*inflow` appear only if asked for.
- **Confirm**: the control echo at the top of the log shows what was asked for; the file, what survived.
- **Remedy**: also beware `<outputNameOption> generic`: with one routing method the names collapse to `RoutedRunoff`, `volume`, `inflow`, and under IRF the discharge lands in `volume` (`IRFroutedRunoff` assigned twice, `IRFvolume` never renamed).
- **Source**: `read_control:610-705`; `popMetadat:238-271`. Both. `source_read + sample`

## A reach's discharge is zero, or its upstream inflow vanished

- **Happening**: three independent gates. `goodBasin`, by which every scheme but accumulation counts upstream inflows, is set from the **downstream** reach's own `totalArea > verySmall` = `tiny(1.0_dp)`, double precision (`public_var:29`) — a reach with no contributing area above it drops *all* its upstream inflow. `<min_length_route>` makes a short reach a pass-through with zero storage. `<hw_drain_point> 2`, the default, sends a headwater reach's lateral flow straight to its outlet, leaving its volume identically zero.
- **Confirm**: set `<desireId>` to the reach id and read the per-reach dump it prints.
- **Remedy**: expect `sumUpstreamRunoff` and the routed discharge to differ there — accumulation uses `size(UREACHI)` and never applies the flag.
- **Source**: `network_topo:771-775`; `irf_route:82,93,235-262`; `kwe_route:263-265,345-355`; `accum_runoff:61`. Both. `source_read`

## Discharge is never quite zero, or a negative runoff aborts the run

- **Happening**: per reach the depth-rate is floored at `<runoffMin>` (default `0`) before multiplying by area; a reach with no contributing HRUs is set to `runoffMin` outright. HRU runoff below `-1e-3` is **fatal**, the HRU id printed.
- **Confirm**: the message is "Exceeded negative RO tolerance: HRU = ...".
- **Remedy**: both sit behind `basin2reach`'s optional `limitRunoff`, `.true.` unless a caller passes otherwise (`process_remap:364-369`), so the evaporation and precipitation mappings are floored and checked alike (`main_route:96-99,180-197`); only the coupled driver's irrigation mapping disables it (`route/build/cpl/RtmMod.F90:537,542,546`), outside this pack's scope. A small negative is clipped only on the no-remap path and in the remapper's threshold, *not* before this check. Reach volumes have their own tolerance and only print " ---- NEGATIVE VOLUME", without stopping.
- **Source**: `process_remap:392-414,310-312`; `public_var:31,33`; `irf_route:183-186`. Both. `source_read`

## The water balance warns, or never warns at all

- **Happening**: the per-reach check `WB = dVol - (Qin + Qlat + precip + take_actual + Qout + evap)`, every term in m3 and the outgoing three negated ([processes.md](processes.md)), runs **only when `<qmodOption> 0`**: with direct insertion on, no reach is checked. The domain check runs only under `<checkMassBalance> T`, once per active method per step, warning above 1 m3.
- **Confirm**: a per-reach warning prints `id`, `lake` and eleven numbered terms — 1 and 3-12, no 2; the domain one, eight (`water_balance:93-106,261-269`).
- **Remedy**: with lakes on, the lake call passes `BASIN_QR(1)` as lateral inflow whatever `<LakeInputOption>` says, so under the default `0` both it and the domain sum report an error of exactly that inflow times `dt`. Expect it; do not tune it away.
- **Source**: `water_balance:61-110,303-320`; `lake_route:162-173,469-470`; `mpi_process:1333-1339`. Both. `source_read`

## Every record looks shifted by one output window

- **Happening**: a record's `time` is its window's **start** plus `<histTimeStamp_offset>` (default 0), not the end or the midpoint; `time_bounds` carries both ends. `<ro_time_stamp>` (`start`, `middle`, `end`) shifts only the *input* series' datetimes and never the output stamp, although the log says "The same time stamp is used for history output".
- **Confirm / Remedy**: bin left-closed, or set `<histTimeStamp_offset>` to half the window. Coupled mode already does that, so the same run stamps its records differently under the two hosts.
- **Source**: `historyFile:364-373`; `read_control:511-519`; `sa/model_setup:506-516`; `write_simoutput_pio:214-217`. Both. `source_read`

## A volume series behaves unlike the discharge series beside it

- **Happening**: every history variable is a **time mean over the output window** — except the five per-method `*volume` variables and `soluteMass`, which are assigned, not accumulated, so the written value is the window's **last step**. `*floodVolume` and `*height`, despite the names, are accumulated and divided like the rest — means (`histVars_data:233-234,284-291`).
- **Confirm**: with `<outputFrequency> 1` the two coincide; any 1-step vs n-step difference is this.
- **Remedy**: difference volumes across records for a storage change; never average them with discharge. `sumUpstreamRunoff` is a mean built from the **delayed** lateral inflow, so under `<doesBasinRoute> 1` it carries the hillslope lag despite the module's "instantaneous" wording.
- **Source**: `histVars_data:230-243,259-304`; `accum_runoff:3-5,63`. Both. `source_read`

## The simulation silently covers a different period than requested

- **Happening**: `<sim_start>` earlier than the runoff series, or `<sim_end>` later, is **not** an error: the code warns and resets the bound to the data. Only `<sim_start>` after the last input time, or `<sim_end>` before `<sim_start>`, is fatal.
- **Confirm**: grep the log for "Reset <sim_start>" or "Reset <sim_end>".
- **Remedy**: the calendar is always taken from the runoff file, overriding `<ro_calendar>`; `<time_units>` defaults to the first runoff file's units.
- **Source**: `sa/model_setup:462-465,533-562`; `read_control:413-435,545-563`. Standalone. `source_read`

## A restart refuses to load, or the restarted run is offset

- **Happening**: the state file stores `nNodes`, and reading it under a **different MPI task count is fatal** ("Number of MPI tasks on restart file is different"). Its stamp is the *next* step. Under `<restart_write> specified` or a periodic value the drop-off datetime is the requested one **minus one `<dt_qsim>`**, so `<restart_date>` and the file name differ by one step by design — `last` does not subtract.
- **Confirm / Remedy**: `<fname_state_in>` unset, `none` or `coldstart` is a cold start — a typo'd path is a read error, not a silent cold start. Neither network nor routing options are compared with the run's, so a changed `<route_opt>` is not caught.
- **Source**: `read_restart:87-96`; `write_restart_pio:185,229-249`; `sa/model_setup:663-665,672,677`; `read_control:395-402`. Both. `source_read`

## Two runs on different task counts do not line up

- **Happening**: the mainstem/tributary split uses the threshold `nSeg/nNodes`, so the decomposition — and with it the reach order along the history file's `seg` dimension — changes with the task count. On one task there is no mainstem.
- **Confirm / Remedy**: never index history output positionally across runs; join on `reachID`, written beside the fluxes, and `basinID` for HRU fluxes.
- **Source**: `domain_decomposition:508-521`; `mpi_process:1200-1312`; `historyFile:186-188,292-300`. Both. `source_read`

## The run ends immediately after writing a network file

- **Happening**: `<ntopAugmentMode> T` or `<seg_outlet> > 0` is a *tool* mode: the augmented or subset network is written to `<fname_ntopNew>` and the program finalises. `<seg_outlet> > 0` also turns augmentation off.
- **Confirm / Remedy**: the log says "Run again using the new network topology file". Point `<fname_ntopOld>` at it and clear both keys.
- **Source**: `init_model_data:247-249,718-746`; `read_control:404-410`. Both. `source_read + sample`
