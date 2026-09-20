# VIC: land processes and driver identity

Scope: official UW-Hydro VIC-5 documentation checked 2026-09-16. The lab's release,
driver and physics settings are unknown. A VIC4 example or a third-party fork is not
automatically a valid VIC5 configuration.

## What VIC calculates

VIC represents subgrid variability in infiltration/storage capacity statistically and
calculates runoff and lower-layer drainage alongside other land water and energy
processes. Its standard land calculation and river routing are separate responsibilities.
See [pitfalls](pitfalls.md#local-runoff-treated-as-gauge-discharge) before comparing
generated runoff with gauge discharge. [V1](sources.md#v1), [V2](sources.md#v2)

Vegetation tiles and elevation bands represent subgrid heterogeneity, not necessarily
explicit geographic polygons inside a cell. Many outputs are aggregated using their
fractions. Consequently a band or tile average and a geographic basin average are different
operations. Inspect the output support before applying a second set of weights.
[V2](sources.md#v2)

## Driver is part of the model identity

The Classic driver uses ASCII/binary I/O and processes time before moving through space.
The Image driver uses netCDF I/O, processes space within each timestep and supports MPI.
These differences affect input preparation, execution and output handling; a filename
extension change is not a valid driver conversion. [V3](sources.md#v3), [V4](sources.md#v4)

Before explaining a particular run, establish revision, driver, forcing time resolution,
active physics and parameter/state provenance. A targeted conceptual question does not
require creating a project or choosing calibration parameters.

For diagnosis, separate precipitation/forcing errors, land-process responses and routing
effects. A mismatch in river timing does not justify altering an infiltration parameter
before checking the routing chain. Conversely, changing a routing scheme does not repair
an incorrect land water balance. These are diagnostic recommendations, not fixed rules
for calibration or claims of identifiability from one hydrograph.

Use [execution](execution.md) for driver-specific setup checks and [outputs](outputs.md)
for units, aggregation and coupling. If the project actually uses mizuRoute, follow the
[routing pack](../mizuroute/overview.md); do not infer that coupling simply from VIC output.
Lake extensions and modified lateral-flow implementations require explicit local evidence.
