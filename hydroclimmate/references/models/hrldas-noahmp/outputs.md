# HRLDAS / Noah-MP: output interpretation — moved

This file is a redirect stub. Output conventions (file kinds and naming, records per file, the
time-stamp convention, dimension order, units, accumulated vs instantaneous, fill and mask
behaviour) are in **[card.md](card.md)**. The exhaustive variable table is
`catalogs/outputs.yaml` — query it with
`tools/hcm_lookup.py --pack hrldas-noahmp <NAME>`. Analysis procedures with their cost
are in **[recipes.md](recipes.md)**; ways an output analysis goes wrong are in
**[failures.md](failures.md)**.

## Follow the output interface

An internal Noah-MP process variable and the written history variable need not share a name or
a shape: the mapping happens in the driver's transfer layer, and the restart file uses a third
set of spellings again. Resolve every name against `catalogs/outputs.yaml` and
`catalogs/restart.yaml` for the pinned commit pair before writing analysis; see
[failures.md: A restart file's variables are not where you expect](failures.md#a-restart-files-variables-are-not-where-you-expect)
and [failures.md: A variable you remember from another Noah-MP does not exist here](failures.md#a-variable-you-remember-from-another-noah-mp-does-not-exist-here).
Grid and area rules for spatial statistics: [recipes.md](recipes.md) recipe 4, plus the
[shared spatial rules](../../analyze.md#identify-grid-or-mesh-before-spatial-processing).
