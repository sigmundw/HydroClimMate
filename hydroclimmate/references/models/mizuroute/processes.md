# mizuRoute — process map

Source root mizuRoute `28514dea` (tag `v3.1.1`). A bare `file:line` means `route/build/src/file.f90`; **sa** = its `standalone/`. Defaults are the initialisers in `public_var:86-210`. Names and units: `tools/hcm_lookup.py --pack mizuroute <NAME>`; this file gives gates, not tables.

## Network topology and HRU-to-reach mapping

Keys `<fname_ntopOld>`, `<dname_sseg>`, `<dname_nhru>`, the `<varname_*>` family, `<topoNetworkOption>`, `<computeReachList>`, `<hydGeometryOption>`, `<seg_outlet>`, `<ntopAugmentMode>` ([failures.md](failures.md)). Only `segId`, `downSegId`, `HRUid`, `hruSegId`, `area`, `length` and `slope` are marked required (`popMetadat:124-134,213-215`); the rest is computed under `<topoNetworkOption> 1` (default). The map matches `hruSegId` to `segId`; a reach's local area is `sum(hruArea)`, each HRU's weight `hruArea / sum(hruArea)` (`network_topo:175-190`), so lateral inflow is exactly `sum_h(area_h * runoff_h)`.
- **Channel geometry is normally invented, not read.** `<hydGeometryOption>` defaults to **0** = read-from-file (`public_var:192`), and under 0 the reader enables only those of `width`, `man_n`, `depth`, `sideSlope`, `floodplainSlope` that exist in the file (`read_streamSeg:322-333`). What is missing is filled with `wscale*sqrt(totalArea)`, `dscale*sqrt(totalArea)`, the namelist `mann_n`, side slope `0` and `floodplainSlope` (`process_ntopo:176-187`). `dscale` (4.5e-5) and `floodplainSlope` (1000) are **in no namelist group** and unsettable from the control (`globalData:187-188`, `read_param:26-28`).
- **`goodBasin` is a property of the downstream reach.** For every immediate upstream link of reach *i* the flag is set from **reach *i*'s own** `totalArea > verySmall`, the *double*-precision `tiny(1.0_dp)` (`public_var:29`, `network_topo:771-775`), despite the comment there. Every scheme but accumulation counts and skips upstream inflows by it (`irf_route:82,93` and the matching pair in `kwe_route`, `mc_route`, `dfw_route`); accumulation uses `size(UREACHI)` and never skips (`accum_runoff:61`).

## Remapping a grid or foreign HRUs

Keys `<is_remap>`, `<fname_remap>` and the `<vname_*>`/`<dname_*>` names of its id, weight, count and index variables. The runoff rank picks the path: 3 dimensions a grid, using `i_index`/`j_index`; 2 a vector, using `qhruid`; else fatal (`sa/model_setup:743-775`). The mapping file is ragged: per network HRU, `num_qhru` entries are taken in order from the weight and id arrays (`process_remap:85-104,191-213`). Under `<is_remap> F` the ids are matched directly, unmatched HRUs left at `realMissing`, then negatives — that value included — zeroed (`:292-312`).
- **Partial coverage is silently renormalised.** Sources at or below `-1e-6` are dropped from both the weighted sum and the weight sum, and if the surviving weights miss 1 by over `1e-6` the result is divided by their sum (`:128-150`; 1-D at `:231-255`).

## Hillslope (basin) routing

Key `<doesBasinRoute>`: `1` (default) convolves local runoff with a gamma unit hydrograph, `0` passes it through; any other value lands in the same pass-through branch (`main_route:203-237`). Parameters `fshape`, `tscale` from `&HSLOPE`. Bin *j* is `gammp(fshape, j*dt/tscale) - gammp(fshape, (j-1)*dt/tscale)`; the bin count is bisected until the cumulative probability lands in (0.99, 0.999), then normalised to 1 (`process_param:55-90`). Answers: `instRunoff` (`BASIN_QI`), `dlayRunoff` (`BASIN_QR(1)`).
- **One hydrograph serves the whole domain**: `FRAC_FUTURE` is a single global array (`process_param:29,76-79`), so hillslope timing cannot vary in space. Under `<is_lake_sim> T` a lake's copy becomes an impulse, so lakes get local runoff undelayed (`basinUH:112-116`).

## Reach routing: what each solves

All five take upstream inflow from the *same* method's `REACH_Q` at the immediately upstream reaches, add `BASIN_QR(1)` as lateral inflow, and write `REACH_Q`, `REACH_INFLOW` and `REACH_VOL(0:1)`. `<hw_drain_point>` (default 2) puts a headwater reach's lateral flow at the top (1, routed) or the bottom (2, bypassing the channel solution, volume forced to 0: `kwe_route:345-355` and its twin in DW and MC). `<min_length_route>` (default 0) makes shorter reaches pass inflow through with zero storage. **Both apply to IRF, KW, MC and DW only**; `kwt_route` has neither (`read_control:599-607`).

**IRF (digit 1).** Convolution with a per-reach unit hydrograph from the Lohmann diffusive-wave kernel, `&IRF_UH` celerity `velo` and diffusivity `diff`, built at a 1-hour internal step over at most 240 hours and aggregated to `dt` (`process_param:136-146,152,248-258`). No channel geometry, no momentum; `velo`/`diff` are spatially constant, so **reach length alone distinguishes one reach's response**. Outflow is capped at `(max(0,V)/dt + Qin)*0.999`, the volume adjusted to match (`irf_route:235-249`).

**KWT (digit 2).** Lagrangian: flow particles with entry and exit times, not a fixed grid; above `MAXQPAR = 20` particles in a reach they are merged (`public_var:36`, `kwt_route:210-211,999-1107`). It alone exchanges state between tasks at tributary-mainstem junctions (`mpi_process:1254-1274,1317-1329`).

**KW (3) and DW (5).** Both call `solve_ade`: a tridiagonal implicit solve of `dQ/dt + ck dQ/dx = dk d2Q/dx2` on `nMolecule = 20` nodes, Dirichlet upstream, Neumann downstream, weights `wck`/`wdk` hard-coded to 1 (fully implicit) (`advection_diffusion:90-152`, `init_model_data:387-393`). KW passes `dk = 0`; DW computes it from normal-depth hydraulics (`kwe_route:294`, `dfw_route:296`). Volume follows `(Qin - Qout)*dt`; under `<floodplain> T` the excess over bankfull volume becomes `FLOOD_VOL`, and `REACH_ELE` is reported.
- **Neither sub-cycles, despite its comment.** `ntSub` is `1` and never changed, immediately below a comment promising Courant-number control (`kwe_route:252,280-281`; `dfw_route:254,282-283`). Only MC adapts, `ntSub = ceiling(dt*ck/L)` when the Courant number exceeds 1 (`mc_route:305-310`). Stability at a long `<dt_qsim>` rests on the implicit solve, not on step control.

**MC (4).** Two nodes (`nMolecule%MC_ROUTE = 2`). Each sub-step recomputes normal depth, top width and celerity from a 3-point average discharge, forms `X = 0.5*(1 - Qbar/(B*S*ck*L))` and the three Muskingum coefficients, and clamps outflow at zero; the reported outflow is the **mean over the sub-steps** (`mc_route:324-348`), or zero below `Qbar = 1e-50` (`:299,339-341`).

## Accumulation ("sum upstream")

Digit `0`; answer `sumUpstreamRunoff`, which is **off unless asked for** ([failures.md](failures.md)). A reach's value is its own lateral inflow plus the accumulated values of **all** immediate upstream reaches: no storage, no delay, no `goodBasin` filter (`accum_runoff:61-75`).
- **It accumulates the *delayed* lateral inflow.** The starting value is `BASIN_QR(1)`, so under `<doesBasinRoute> 1` it already carries the gamma lag, though the module header calls it "total instantaneous upstream runoff" (`:3-5,63`). Lake handling is skipped for it (`main_route:368`), so over a lake it reports inflow, not release.

## Lakes and reservoirs

Keys `<is_lake_sim>`, `<lakeRegulate>`, `<LakeInputOption>`, `<is_vol_wm>`, `<is_vol_wm_jumpstart>` and the `<varname_islake|lakeModelType|LakeTargVol>` names. Under `<is_lake_sim> T` the topology file **must** carry `islake` and `lakeModelType` (`read_streamSeg:336-340`); the latter picks the outflow model: `0` endorheic (none), `1` Doll 2003 `Q = A(S-S0)((S-S0)/(Smax-S0))^B` converted per-day to per-second, `2` Hanasaki 2006 with inflow and demand memories, `3` HYPE, two spillways (`lake_route:15-18,206-441`); `<lakeRegulate> F` forces them all to Doll (`process_ntopo:482-486`). `LakeTargVol` replaces the parametric model with a release toward a prescribed volume and is **rejected as a conflict** if it also has a type 0-3 — but only under `<is_vol_wm> T`, which gates the whole check (`read_streamSeg:392-400`).
- **`<LakeInputOption>` decides whether local runoff enters a lake at all, and its default excludes it.** `0` (default) gives a lake only precipitation and evaporation, `1` only local runoff, `2` all three (`lake_route:162-173`). Evaporation is capped at the storage available, which the code itself notes breaks the coupled-mode balance (`:167-172`).

## Water balance

Key `<checkMassBalance>` (default `F`). Per reach, `comp_reach_wb` forms `WB = dVol - (Qin + Qlat + precip + take_actual + Qout + evap)` with every term already multiplied by `dt` and `Qout`, `take_actual`, `evap` already negated (`water_balance:70-87`), and warns above `2e-5` m3 — **but only under `<qmodOption> 0`**, so data assimilation skips it entirely (`water_balance:61-110`; `irf_route:200-202` and its twin in each scheme); for lakes it is unconditional, tolerance `2e-2` m3 (`lake_route:469-470`). Domain-wide, `comp_global_wb` sums volume change, lateral inflow, lake precipitation and evaporation, abstraction and the outflow of reaches it takes for outlets (`DREACHI == -1 .and. DREACHK <= 0`), warning above 1 m3, once per active method per step (`water_balance:272-274,303-320`, `mpi_process:1333-1339`).

## Restart, continuation

Keys `<restart_write>` (`never` default, else `last`, `specified`, `yearly`, `monthly`, `daily`), `<restart_date>`, the periodic `<restart_month|day|hour>`, `<fname_state_in>`, `<restart_dir>` (default `<output_dir>`), `<continue_run>`. Under `specified` and the periodic `yearly|monthly|daily` the drop-off datetime is the requested one **minus one `<dt_qsim>`**, so the file is written the step before the one it restarts (`sa/model_setup:672,677`); under `last` it is `<sim_end>` itself, unshifted (`:663-665`), and under `never` it is all-missing (`:680-681`). `<fname_state_in>` absent, `none` or `coldstart` is a cold start (`read_control:395-402`). On read, the time bound is recovered and `dt` added; the history buffers come from the same file, so a restart mid-window keeps its partial average (`init_model_data:601-620`, `histVars_data:356-383`).

## Domain decomposition, MPI

The network splits into "mainstem" reaches — those with more than `nSeg/nNodes` upstream reaches — and the tributaries below them, distributed over tasks (`domain_decomposition:508-521`). Every task routes its tributaries, their outlet fluxes are gathered to the root, and the root alone routes the mainstem (`mpi_process:1200-1312`). Within a task, reaches run in stream-order groups, OpenMP over independent branches (`main_route:350-398`).
- **The split depends on the task count.** With one task the threshold is `nSeg`, no reach exceeds it, there is no mainstem and the root routes everything as tributaries. A restart file records `nNodes` and refuses a different value (`read_restart:87-96`), so a run cannot continue on a different task count; and the history file's reach order follows the decomposition, so `reachID` is the only safe index.

## Data assimilation, tracer

`<qmodOption> 1` is direct insertion: a gauge observation present at the current step is inserted and the error subtracted from routed discharge, decaying by `<QerrTrend>` over `<qBlendPeriod>` steps, floored at zero (`main_route:125-148`, `data_assimilation:63-93`). It needs `<gageMetaFile>` and `<fname_gageObs>`; if that file is absent it is **silently reset to 0** (`init_model_data:845-868`). `<tracer> T` advects a solute and **aborts unless digit 5 (DW) is in `<route_opt>`** (`read_control:715-725`); in-stream reaction and dispersion are absent (`tracer:5-10`).

## Coupled mode

`runMode = 'cesm-coupling'` is set by the host, not by a control key. It renames history and restart to `<case_name>.mizuroute.h.*` / `.mizuroute.r.*`, dates the `rpointer.rof`, and overrides `<histTimeStamp_offset>` with half the window, stamping each record at its midpoint (`write_simoutput_pio:214-217,376-381`, `write_restart_pio:243-246`). It owns the negative-runoff keys and skips the PIO initialisation the host performs (`init_model_data:55-65`). Under `<continue_run> T` the branch that could clear `isColdStart` is itself skipped (`read_control:395-402`), so it keeps its `.true.` initialiser (`globalData:139`) and the cold start runs; what the host's driver then does is outside this pack.
