# mizuRoute sources

Primary authority for this pack is a **pinned local source tree**, not a web page. Ids `L*` below are the primary sources. `Checked: 2026-09-21` appears only on records whose content was actually read on that date. Where the pinned in-repo documentation and the pinned code disagree, this pack states the code's behaviour and records the disagreement.

## L0

The pinned tree (version anchor). mizuRoute repository at commit `28514dea3fd28a2f820c7ecaa9014f820c1bb220`, tag `v3.1.1` (2026-04-14), confirmed by `git describe --tags` and `git log`. Every `path:line` citation in [card.md](card.md), [processes.md](processes.md), [failures.md](failures.md), [recipes.md](recipes.md) and [version.md](version.md) is relative to the root of that tree and holds only at that commit. Checked: 2026-09-21.

## L1

Control and configuration: `route/build/src/public_var.f90` (every control variable and its default, the routing-method ids, the tolerances and sentinels) and `route/build/src/read_control.f90` (the key list, the fatal default branch, the runoff and solute unit conversions, the time-step and output-frequency validation, the routing-digit parsing, and the gating and renaming of every history variable). Checked: 2026-09-21.

## L2

Standalone driver and its I/O: `route/build/src/standalone/route_runoff.f90`, `model_setup.f90` (input-file discovery, the time axis and the overwriting of `dt_ro`, the calendar and time-units precedence, the simulation-window resets, the runoff metadata and the id matching, the restart drop-off datetimes), `read_runoff.f90` (fill values and the fraction-weighted temporal aggregation), `get_basin_runoff.f90` (the simulation-to-input time mapping, scaling and offsetting), `read_remap.f90`. Checked: 2026-09-21.

## L3

Network and parameters: `route/build/src/read_streamSeg.f90` (the topology reader and the channel-geometry and lake variable enabling), `network_topo.f90` (HRU-to-reach mapping, weights, areas, `goodBasin`, the reach list), `process_ntopo.f90` (geometry filling, storage, the structure population, the lake type override), `process_param.f90` (the gamma hillslope hydrograph and the Lohmann reach unit hydrograph), `read_param.f90` (the three namelist groups), `popMetadat.f90` and `var_lookup.f90` (variable names, units, descriptions and which are required). Checked: 2026-09-21.

## L4

Routing: `route/build/src/main_route.f90` (the per-step driver, the water-management initialisation, the data-assimilation insertion, the OpenMP reach loop, the lake branch), `basinUH.f90`, `accum_runoff.f90`, `irf_route.f90`, `kwt_route.f90`, `kwe_route.f90`, `mc_route.f90`, `dfw_route.f90`, `advection_diffusion.f90`, `hydraulic.f90`, `lake_route.f90`, `tracer.f90`, `data_assimilation.f90`, `base_route.f90`. Supports every statement about what each scheme solves, its parameters, its sub-stepping, its headwater and short-reach branches, and the lake outflow models. Checked: 2026-09-21.

## L5

Output, state and parallelism: `route/build/src/write_simoutput_pio.f90` (file frequency, file naming, the output alarms), `historyFile.f90` (dimensions, variable definition, the time and time-bounds write, the global attributes), `histVars_data.f90` (the aggregation, the mean-versus-last-value distinction, the restart of the buffers), `write_restart_pio.f90` and `read_restart.f90` (restart naming, the drop-off alarm, the task-count check), `io_rpointfile.f90`, `water_balance.f90`, `mpi_process.f90` and `domain_decomposition.f90`, `init_model_data.f90`, `globalData.f90`. Checked: 2026-09-21.

## L6

Build: `route/build/Makefile`. Supports [version.md](version.md): the `VERSION`, `BRANCH` and `HASH` macros are filled from `git` at compile time, so a history file's version attributes describe the build's checkout; built outside a git working tree by this Makefile they are written **empty**, because every compiler arm passes the macros regardless, and the initialiser `undefined` appears only in a binary built without those `-D` flags. Checked: 2026-09-21.

## L7

Sample control files, pinned with the code: `route/settings/SAMPLE.control` and `route/settings/SAMPLE-coupled.control`. Used to confirm control-file statements, which carry the tag `source_read + sample`. **They are examples, not tested configurations**: `SAMPLE.control:150-154` uses five `<*inflow>` keys the parser does not accept, so the file as shipped is fatal; and its comments on lines 142-143 describe `<MCroutedRunoff>` as kinematic-wave output and `<KWroutedRunoff>` as Muskingum-Cunge output, the two the wrong way round. Checked: 2026-09-21.

## L8

In-repo documentation, pinned with the code: `docs/source/users_guide/*.rst` and `docs/source/tech_note/*.rst`. Citable, but **code wins**. Five disagreements were found. `Riv.rst:17` names the routing key `<routOpt>` where the parser accepts only `<route_opt>`; `Control_file.rst:206,266,331` use `<dt_rof>` where the parser accepts only `<dt_ro>`; `Input_files.rst:126` lists `<topoNetworOption>` where the parser accepts `<topoNetworkOption>`; `Input_files.rst:250` lists `<vname_vname_hruid>` where the parser accepts `<vname_hruid>`; and `Riv.rst:31,58-60` give the default of `<hydGeometryOption>` as `1` (compute internally) where `public_var.f90:192` initialises it to `0` (read from file). The first four are keys a control file copied from the documentation would be rejected for. `docs/source/history.rst` is a narrative of the model's origins and carries no operational fact used here. Checked: 2026-09-21.

## Ideas taken from related work

The design of [failures.md](failures.md) — **indexing failure knowledge by symptom, each entry carrying a diagnosis and a remedy** — is an idea taken from the KISS project ([arXiv 2605.17856v1](https://arxiv.org/abs/2605.17856)), together with the principles that a model knowledge layer should carry concrete operational facts (names, units, conventions, option meanings) rather than advice, and that everything should be bound to one model version. No schema, file name, field name or wording from that project is reproduced here; the formats, vocabulary and content of this pack are its own. Recorded: 2026-09-21.

## M1-M6 (retired)

The earlier records for this pack were six pages of the mizuRoute documentation site read on its floating `stable` alias (repository identity, input files, hillslope routing, river routing, control file, output files), checked 2026-09-16. They are superseded for every operational fact by L0-L8, are cited by no statement in this pack, and were retired with the four outline files they supported. The pinned copies under `docs/` (L8) are what is now cited, by line.

## Not established

The coupled build is covered only where it differs from the standalone one; nothing is claimed about a host's own configuration, its pointer-file handling or its runoff units. The KWT particle algorithm is described by its interface, its wave limit and its gating, not derived line by line. The Hanasaki and HYPE reservoir formulations are stated as the parameters and branches the code carries, with no claim about their calibration or their behaviour in a simulation. The PIO layer, the Pfafstetter code path, the gauge-metadata reader and the water-management input files were read only far enough to state the gates quoted here. **No mizuRoute run, input file or output file was available**, so no numerical result, no cost and no scaling figure is claimed anywhere in this pack.
