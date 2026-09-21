# HRLDAS / Noah-MP sources

Primary authority for this pack is a **pinned local source tree**, not a web page. Ids `L*`
below are the primary sources; ids `H*` are the older web-retrieved records, kept because
earlier structured layers reference them and because two of them are still cited.

`Checked: 2026-09-21` appears only on records whose content was actually re-read on that date.
`H1`-`H5` keep their original `Checked: 2026-09-16` and were **not** re-verified.

## L0

The pinned tree (version anchor). HRLDAS repository at commit `d9f5b205`, with the `noahmp`
submodule at commit `9fbe6724` (`git describe`: `v3.7.1-355-g9fbe672`), confirmed by `git log`
and `git submodule status`. All `path:line` citations in [card.md](card.md),
[processes.md](processes.md), [failures.md](failures.md), [recipes.md](recipes.md) and
[version.md](version.md) are relative to the root of that tree and hold only at that commit
pair. Checked: 2026-09-21.

## L1

HRLDAS offline driver and NetCDF I/O: `hrldas/IO_code/main_hrldas_driver.F`,
`hrldas/IO_code/module_NoahMP_hrldas_driver.F`, `hrldas/IO_code/module_hrldas_netcdf_io.F`.
Supports: file kinds and naming, records per file, the time loop and first-record behaviour,
the history and restart variable lists, dimension definitions and order, the global-only
`missing_value`, the water masking rules, the forcing unit conversions, the accumulators and
their restart handling, the urban call site and the urban-fraction read. Checked: 2026-09-21.

## L2

Noah-MP physics modules: `noahmp/src/*.F90` (the capital-`F90` originals, not the preprocessed
`.f90` copies). Supports the process → module map and every hard-coded threshold, cap,
substitution and order-of-operations statement in [processes.md](processes.md) and
[failures.md](failures.md). Checked: 2026-09-21.

## L3

Noah-MP HRLDAS driver layer: `noahmp/drivers/hrldas/*.F90` — in particular
`NoahmpReadNamelistMod.F90` (namelist → `IOPT_*`), `ConfigVarInTransferMod.F90` (`IOPT_*` →
`Opt*`, the urban and crop reassignments, the soil-type substitution), `NoahmpIOVarType.F90`
and `NoahmpIOVarInitMod.F90` (fixed `NSNOW`, the `undefined_real` initialisation, accumulator
zeroing), `NoahmpDriverMainMod.F90`, `WaterVarOutTransferMod.F90`, `NoahmpInitMainMod.F90`,
`GroundWaterMmfMod.F90`, `NoahmpReadTableMod.F90`. Checked: 2026-09-21.

## L4

Namelist description and parameter tables: `hrldas/run/README.namelist` (every namelist item,
its allowed values and the annotated defaults — note the self-contradiction recorded in
[version.md](version.md)); `noahmp/parameters/NoahmpTable.TBL` (land-use class indices per
dataset, physical and process parameters); `hrldas/run/URBPARM.TBL`, `URBPARM_LCZ.TBL`,
`URBPARM_UZE.TBL`. Checked: 2026-09-21.

## L5

Offline urban path: `urban/wrf/NoahmpUrbanDriverMainMod.F` and `urban/wrf/module_sf_urban.F`.
Supports the urban section of [processes.md](processes.md): the argument list, the
tile-weighted field set per `SF_URBAN_PHYSICS` value, the internal floors and splits, and the
`FRC_URB_TBL` fallback in `urban_var_init`. **Supersedes and corrects [H6](#h6)**: `EMISS` is
*not* tile-weighted in the single-layer path, `UST` *is*, and the table-fraction fallback was
previously omitted. Checked: 2026-09-21.

## L6

Real output from this commit: a two-member paired regional offline run (urban physics off/on,
otherwise one-line-identical namelists) built from this commit pair — history,
restart, setup and forcing files, read with a local Python/netCDF4 environment. Used only for
statements tagged `observed`/`both`: the first-record `-9999` pattern, the dimension order as
it appears on file, the mask behaviour of float / integer / restart fields, accumulator
monotonicity, the zero-layer snow state, the grid and map-factor properties, and the read-cost
ranges in [recipes.md](recipes.md). No paths, run names or place names from that run appear in
this package. Checked: 2026-09-21.

## L7

Independent cross-check and correction pass (2026-09-21): 269 claims re-checked against L0-L6 by
someone who wrote none of the pack, 16 wrong and 21 imprecise, every one re-opened at its cited
line before this text was changed. It supplied the `FlagUrban` gating correction (the internal
urban treatment applies **only** when `SF_URBAN_PHYSICS == 0`), the `EFLXB` and
`SOILENERGY`/`SNOWENERGY` kinds, the `ZWT`/`WA`/`WT` option gating, the measured precipitation
factor of two, and the paired-run urban measurements. Its variable-by-variable kind and
misleading-unit table is carried as the curated `catalogs/kinds_overlay.yaml`, which overrides
the generated `catalogs/outputs.yaml` where they disagree. One item was **not** adopted as
written: it reported, from `hrldas/run/README.namelist:34-36`, that `RESTART_FREQUENCY_HOURS = 0` writes no
restart files; the driver's own test is `<= 0` and writes monthly restarts for 0 as well
(`hrldas/IO_code/module_NoahMP_hrldas_driver.F:1390-1399`), so the pack states the code
behaviour and records the disagreement. Checked: 2026-09-21.

## Ideas taken from related work

The design of [failures.md](failures.md) — **indexing failure knowledge by symptom, each entry
carrying a diagnosis and a remedy** — is an idea taken from the KISS project
([arXiv 2605.17856v1](https://arxiv.org/abs/2605.17856)), together with the principles that a
model knowledge layer should carry concrete operational facts (names, units, conventions,
option meanings) rather than advice, and that everything should be bound to one model version.
No schema, file name, field name or wording from that project is reproduced here; the formats,
vocabulary and content of this pack are its own. Recorded: 2026-09-21.

## H1

[NCAR HRLDAS README](https://github.com/NCAR/hrldas): retrieved; introduction, download,
repository structure and v5.0 modernization sections. Floating reference; superseded for every
operational fact by [L0](#l0) and [L1](#l1). Checked: 2026-09-16.

## H2

[NCAR Noah-MP README](https://github.com/NCAR/noahmp): retrieved; v5.X refactoring and host
requirements. Floating reference; not used for any claim in the rebuilt pack.
Checked: 2026-09-16.

## H3

[He et al. 2023, Noah-MP v5.0](https://gmd.copernicus.org/articles/16/5131/2023/),
DOI 10.5194/gmd-16-5131-2023: fixed publication, retrieved; code/data organization and host
coupling. The citable description of the modular architecture; not used for any variable name,
unit or threshold here. Checked: 2026-09-16.

## H4

[HRLDAS namelist description on master](https://raw.githubusercontent.com/NCAR/hrldas/master/hrldas/run/README.namelist):
retrieved. Floating reference, superseded by the pinned copy in [L4](#l4); the pinned file is
the one cited by line number. Checked: 2026-09-16.

## H5

[NCAR tutorial index](https://github.com/NCAR/hrldas/tree/master/tutorial): retrieved; lesson
listings only. Notebooks not executed; not used for any claim here. Checked: 2026-09-16.

## H6

Earlier hand-written urban note (HRLDAS `d9f5b205`, `noahmp` `9fbe6724`) covering
`ConfigVarInTransferMod.F90:156-163`, `module_NoahMP_hrldas_driver.F:1028,1041-1101` and
`NoahmpUrbanDriverMainMod.F:522-536`. **Retained for the structured layers that reference it,
but superseded and corrected by [L5](#l5).** Checked: 2026-09-19.

## Not established

The technical note PDF and the February 2023 variable glossary spreadsheet under `noahmp/docs`
were **not** read for this rebuild; nothing here depends on them. Numerical behaviour of
`SF_URBAN_PHYSICS` 2 and 3 beyond the argument list and the weighting block is not established.
Bit-reproducibility across compilers or MPI decompositions was not tested.
