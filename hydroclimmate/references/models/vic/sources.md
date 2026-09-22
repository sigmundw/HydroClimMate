# VIC sources

Primary authority for this pack is a **pinned local source tree**, not a web page. Ids `L*` below are the primary sources; ids `V*` are the older web-retrieved records, kept because earlier structured layers reference them. `Checked: 2026-09-21` appears only on records whose content was actually read on that date; `V1`-`V8` keep their original `Checked: 2026-09-16` and were **not** re-verified. Where the pinned in-repo documentation and the pinned code disagree, this pack states the code's behaviour and records the disagreement.

## L0

The pinned tree (version anchor). VIC repository at commit `14a371a8`, tag `5.1.0` (2021-12-14), with the `samples/data` submodule at `3f2dcb4`, confirmed by `git describe --tags`, `git log` and `git submodule status`. Every `path:line` citation in [card.md](card.md), [processes.md](processes.md), [failures.md](failures.md), [recipes.md](recipes.md) and [version.md](version.md) is relative to the root of that tree and holds only at that commit. The tag commit itself changes no file. Checked: 2026-09-21.

## L1

Shared physics: `vic/vic_run/src/*.c` and `vic/vic_run/include/*.h`. Supports the tile and band loop, the variable-infiltration curve and the runoff sub-step, the ARNO baseflow formulation, the two-layer snowpack and its water-equivalent split, canopy interception and blowing snow, the surface energy balance and its solver fallbacks, the lake and carbon paths, and the array-size and sentinel constants. Checked: 2026-09-21.

## L2

Driver-independent I/O and control: `vic/drivers/shared_all/src/*.c` — in particular `get_global_param.c`'s two driver copies via L3 and L4, `put_data.c` (per-step unit conventions, the tile and band weighting, the water and energy residuals), `agg_data.c` and `vic_history.c` (the six aggregation types and the per-variable defaults), `alarms.c` and `make_dmy.c` (the timestep-beginning clock), `set_output_defaults.c`, `get_parameters.c` (the constants file), `history_metadata.c` (output names, units and descriptions), `input_tools.c`. Checked: 2026-09-21.

## L3

Classic driver: `vic/drivers/classic/src/*.c` — `get_global_param.c` (key list, validation, the VIC 4 rejections), `vic_force.c`, `get_force_type.c`, `read_atmos_data.c`, `read_soilparam.c`, `read_vegparam.c`, `read_veglib.c`, `read_snowband.c`, `make_in_and_outfiles.c`, `write_data.c`, `write_header.c`, `check_state_file.c`, `compute_cell_area.c`. Checked: 2026-09-21.

## L4

Image driver and its shared layer: `vic/drivers/image/src/*.c` and `vic/drivers/shared_image/src/*.c` — `get_global_param.c` (the image key list and its two fatal rejections), `vic_force.c`, `get_global_domain.c` and `check_domain_info.c` (the domain and `run_cell` contract), `vic_init.c` (the NetCDF parameter read and its much smaller validation set), `vic_nc_info.c`, `vic_init_output.c` and `vic_write.c` (dimension order, fill values, global attributes, the record time stamp), `vic_store.c` and `vic_restore.c` (the state file and what is checked), `vic_mpi_support.c` (the decomposition and the gather). Checked: 2026-09-21.

## L5

Build and version metadata: `vic/drivers/classic/Makefile`, `vic/drivers/image/Makefile`, `vic/drivers/shared_all/include/vic_version.h`, `vic/drivers/shared_all/src/cmd_proc.c`. Supports [version.md](version.md), including the finding that a 5.1.0 build reports the fallback version string 5.0.1 because neither Makefile defines the version macros. Checked: 2026-09-21.

## L6

Routing extensions: `vic/extensions/rout_stub/` and `vic/extensions/rout_rvic/` (`rout.c`, `rout_run.c`, `rout_init.c`, `rout_alloc.c`, `rout_convolution.c`, `include/rout.h`, `rout.mk`), with the `ROUT` variable in `vic/drivers/image/Makefile`. Supports every routing statement in this pack: that the shipped default has empty function bodies, that the RVIC extension exists only in the image driver, and what it reads and writes. Checked: 2026-09-21.

## L7

In-repo documentation, pinned with the code: `docs/Documentation/Drivers/{Classic,Image}/*.md`, `docs/Documentation/OutputVarList.md`, `docs/Documentation/Constants.md`, `docs/Development/ReleaseNotes.md`. Citable, but **code wins**: the disagreements found are the soil parameter file's two option-gated trailing columns being listed in the opposite order to the reader's, an undocumented extra soil column block, a promise of `#` comment lines the reader does not support, and a replacement key named in a fatal error message that neither driver accepts. Checked: 2026-09-21.

## L8

Public sample inputs: `samples/data` at `3f2dcb4` — the Stehekin classic and image input sets (global parameter files, soil, veg, veg library and snow-band tables, ASCII per-cell forcings, and the NetCDF domain, parameter and forcing files). Used only to confirm input-format statements, which carry the tag `source_read + sample`. **The sample data contains no model output**, so no statement anywhere in this pack is graded as observed in output. Its shipped global files also name paths that omit the `parameters/` subdirectory. Checked: 2026-09-21.

## Ideas taken from related work

The design of [failures.md](failures.md) — **indexing failure knowledge by symptom, each entry carrying a diagnosis and a remedy** — is an idea taken from the KISS project ([arXiv 2605.17856v1](https://arxiv.org/abs/2605.17856)), together with the principles that a model knowledge layer should carry concrete operational facts (names, units, conventions, option meanings) rather than advice, and that everything should be bound to one model version. No schema, file name, field name or wording from that project is reproduced here; the formats, vocabulary and content of this pack are its own. Recorded: 2026-09-21.

## V1-V8

The earlier web-retrieved records for this pack — the UW-Hydro repository page, the model overview, the two driver pages, the two run guides, the image input page and the two output pages, all on the floating `master` alias of the VIC documentation site. They are superseded for every operational fact by L0-L8 and are not cited by any statement in the rebuilt pack; the pinned copies under `docs/` (L7) are what is cited by line. Checked: 2026-09-16.

## Not established

The `cesm` and `python` drivers are out of scope. The classic driver's own state-file writer and reader were read only for the compatibility checks quoted, not variable by variable. No runtime cost, memory figure or scaling measurement exists, because no run exists. Numerical behaviour of the lake, carbon, blowing-snow and frozen-soil schemes beyond their gates, inputs, outputs and cost implications is not established. The RVIC extension was read but never built or exercised, so nothing is claimed about its numerical results. No literature parameter ranges are given, because the pinned documentation supplies none.
