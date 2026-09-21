# HRLDAS / Noah-MP — version anchor

**Pinned to HRLDAS `d9f5b205` with the `noahmp` submodule at `9fbe6724`** (`git describe`: `v3.7.1-355-g9fbe672`). Every `path:line` citation here is relative to that tree and guaranteed only at that commit pair.

## Checking a checkout

```
git -C <hrldas> log --oneline -1     # expect d9f5b205
git -C <hrldas> submodule status     # expect 9fbe6724... noahmp (v3.7.1-355-g9fbe672)
```
If the submodule is unpopulated the physics is absent and nothing in [processes.md](processes.md) can be checked against it.

## Checking a user's output

Without the source, five header facts identify a compatible build:

1. `TITLE` begins `OUTPUT FROM HRLDAS ` / `RESTART FILE FROM HRLDAS `; what follows is the build's own label, not the commit.
2. Global `missing_value = -1e33` and **no** variable-level `_FillValue`/`missing_value`; variable attributes are exactly `MemoryOrder`, `description`, `units`, `stagger`.
3. Dimensions `west_east`, `south_north`, `soil_layers_stag`, `snow_layers`, `rad_num` (history); `sosn_layers`, `rad_layers`, `ubhi_layers` (restart). **`urban_layers` and the other `u*_layers` appear only when `SF_URBAN_PHYSICS > 0`** (measured: 11 restart dimensions urban-off, 22 urban-on), so they are not build identifiers.
4. Spellings `SFCRNOFF`, `UGDRNOFF`, `ZSNSO_SN`, `SOIL_M`, `ACSNOM`; restart `SFCRUNOFF`, `UDRUNOFF`, `ZSNSO`, `SMC`, `ACMELT`.
5. `RAINRATE` carries `units = "mm/timestep"`.

## What is known to differ elsewhere

- **One quantity, two spellings, inside this tree.** Internal arrays and the restart file use `SFCRUNOFF`/`UDRUNOFF`; history writes `SFCRNOFF`/`UGDRNOFF` (`hrldas/IO_code/module_NoahMP_hrldas_driver.F:1177-1178` vs `:1498-1499`), so a name learned from internal code or another host finds nothing in a history file.
- **Two urban drivers exist here**: the offline path this pack cites (`urban/wrf/NoahmpUrbanDriverMainMod.F`) and a WRF-coupled one (`noahmp/drivers/wrf/...`); the weighting facts are from the former.
- **Neither namelist annotation is authoritative**, and the `**` marker is not consistently the right one: `SNOW_COVER_OPTION` `[default = 2]` vs `**` on 1 (code 1); `TEMP_TIME_SCHEME_OPTION` `[default = 1]` vs `**` on 3 (code 1); `SURFACE_RESISTANCE_OPTION` `[default = 1]` vs `**` on 4 (code 1) (`hrldas/run/README.namelist:204-235`). **The executable's defaults are the initialisers at `noahmp/drivers/hrldas/NoahmpReadNamelistMod.F90:73-116`.**
- Anything about other releases is **not established** here.

## What is void if the version differs

Every `path:line` citation; the output and restart name lists; option value meanings; the hard-coded thresholds in [processes.md](processes.md) and [failures.md](failures.md); and all of `catalogs/*.yaml`, generated from this commit pair. The I/O-layer conventions — dimension order, global-only `missing_value`, the first-record behaviour, end-stamped records — must be **re-checked against your own file headers** rather than assumed to carry over.
