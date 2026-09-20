# HRLDAS / Noah-MP sources

Checked: 2026-09-16. Lab version: unknown. GitHub master URLs below are floating references,
not pinned commits. Summaries cover the stated topics only; no compilation or model run was performed.

## H1

[NCAR HRLDAS README](https://github.com/NCAR/hrldas): retrieved; introduction, download,
repository structure and v5.0 modernization sections. Supports offline-host identity,
forcing categories, WRF setup relationship and submodule requirement.

## H2

[NCAR Noah-MP README](https://github.com/NCAR/noahmp): retrieved; v5.X refactoring and host
requirements. Supports the v4.5/v5.0 distinction. Some branch descriptions still name v5.0;
do not use this README alone to assert the newest release or coupling availability.

## H3

[He et al. 2023, Noah-MP v5.0](https://gmd.copernicus.org/articles/16/5131/2023/): retrieved;
abstract and sections on code/data organization and host coupling, especially section 7.
Fixed publication DOI: 10.5194/gmd-16-5131-2023. Supports process modularity and column/host distinction.

## H4

[HRLDAS namelist description](https://raw.githubusercontent.com/NCAR/hrldas/master/hrldas/run/README.namelist):
retrieved; NOAHLSM_OFFLINE timing, paths, restart and initial-output comments. Current master
comments are not guaranteed to describe an older executable. No defaults are adopted here.

## H5

[NCAR tutorial index](https://github.com/NCAR/hrldas/tree/master/tutorial): retrieved;
single-point, regional and output-variable lesson listings. Notebook execution and all
embedded examples were not validated.

## H6

NCAR HRLDAS repository (https://github.com/NCAR/hrldas), commit `d9f5b205`; `noahmp`
submodule (https://github.com/NCAR/noahmp), commit `9fbe672` (`v3.7.1-355-g9fbe672`);
`drivers/hrldas` build path. Inspected: `ConfigVarInTransferMod.F90:156-163` (urban-cell
vegetation-type/`GVFMAX` reassignment when `SF_URBAN_PHYSICS>0`);
`module_NoahMP_hrldas_driver.F:1028,1041-1101` (call sequence and IN/OUT argument list for
the urban routine — no snow variable present); `NoahmpUrbanDriverMainMod.F:522-536`
(`FRC_URB2D` tile-weighting formulas for the listed fluxes). Supports the urban-tile scope
note in [pitfalls.md](pitfalls.md#paired-urban-onoff-snow-difference-attributed-to-canopy-physics).
Checked 2026-09-19. Not a claim about other driver paths or releases.

## Further detail and gaps

[Official docs directory](https://github.com/NCAR/noahmp/tree/master/docs) was inspected as
an index: it lists v5.0/v5.2 technical PDFs and a February 2023 variable glossary.
[v5.0 technical note](https://doi.org/10.5065/ew8g-yr95) is a navigation link, not a claim
that every equation or glossary entry was checked. Complete physics/variable catalogs,
version-specific build flags and laboratory configurations are outside this pack.
