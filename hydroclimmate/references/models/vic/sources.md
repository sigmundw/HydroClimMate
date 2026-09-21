# VIC sources

Checked: 2026-09-16. Scope: official UW-Hydro VIC5 documentation under `master`, a floating alias, not a pinned release. Lab revision and driver: unknown. No model run was performed.

## V1

[UW-Hydro/VIC](https://github.com/UW-Hydro/VIC): retrieved; model identity, infiltration, baseflow and development context. Does not document a third-party fork's added physics.

## V2

[Model overview](https://vic.readthedocs.io/en/master/Overview/ModelOverview/): retrieved; Main Features, Land Cover and Elevation Bands. Supports standard land/routing separation and subgrid weighting. Extensions such as lake-channel interactions need their own scope.

## V3

[Classic driver](https://vic.readthedocs.io/en/master/Documentation/Drivers/Classic/ClassicDriver/): retrieved; I/O and execution order. Not a VIC4-to-VIC5 migration recipe.

## V4

[Image driver](https://vic.readthedocs.io/en/master/Documentation/Drivers/Image/ImageDriver/): retrieved; netCDF, execution order and MPI support.

## V5

[Classic run guide](https://vic.readthedocs.io/en/master/Documentation/Drivers/Classic/RunVIC/) and [Image run guide](https://vic.readthedocs.io/en/master/Documentation/Drivers/Image/RunVIC/): retrieved; separate build/run workflows. Commands were not executed or adopted for the lab.

## V6

[Image inputs](https://vic.readthedocs.io/en/master/Documentation/Drivers/Image/Inputs/): retrieved; required input categories and initial-state navigation, not all individual formats.

## V7

[Output variables](https://vic.readthedocs.io/en/master/Documentation/OutputVarList/): retrieved; water-state and flux distinctions. Full field catalog and option-dependent aggregation behavior have not been audited.

## V8

[Image outputs](https://vic.readthedocs.io/en/master/Documentation/Drivers/Image/Outputs/): retrieved; output streams and configurable products. Match generated metadata to the checkout.

## Limits

Legacy forcing tools, complete parameter catalogs, coupled drivers, custom routing adapters and lab calibration settings are not covered. Summaries are original paraphrases; the simple depth/volume conversion is a dimensional example, not a model validation result.
