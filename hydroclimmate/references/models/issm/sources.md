# ISSM sources

Checked: 2026-09-16. Lab revision/interface: unknown. JPL chapters below are unversioned
web documents; their API tables can lag current code. They support the cited concepts,
not an assertion about current defaults. No solve or MATLAB/Python compatibility test was run.

## I1

[Stress balance](https://issm.jpl.nasa.gov/documentation/stressbalance/): retrieved;
physical basis, approximations, boundary conditions and convergence controls. Exact
field names are intentionally not prescribed in this pack.

## I2

[Transient](https://issm.jpl.nasa.gov/documentation/transient/): retrieved; physical basis
and component activation. The page contains dated implementation-status statements;
only the component-selection concept is distilled, not its full execution order or API table.

## I3

[Mass transport](https://issm.jpl.nasa.gov/documentation/masstransport/): retrieved;
conservation, source-term units/signs and free-surface distinction. Some field comments
abbreviate units inconsistently; use the physical-basis definition and local code for a run.

## I4

[ISMIP tutorial](https://issm.jpl.nasa.gov/documentation/tutorials/ismip/): retrieved;
parameterization examples distinguish vertex and element arrays. Does not establish the
interpolation order of every output. Linear-triangle integration in outputs.md is our
explicit mathematical derivation, not a copied ISSM API.

## I5

[Square ice shelf](https://issm.jpl.nasa.gov/documentation/tutorials/squareiceshelf/):
retrieved; idealized MATLAB setup and velocity solve. Example not executed here.

## I6

[Grounding lines](https://issm.jpl.nasa.gov/documentation/groundinglines/): retrieved;
flotation and sub-element treatment. Scheme names/defaults must be checked in the actual revision.

## I7

[Inverse methods](https://issm.jpl.nasa.gov/documentation/inversions/): retrieved;
controls, observation misfit and optimization concepts; no calibration recipe adopted.

## Navigation and gaps

[Team documentation](https://issmteam.github.io/ISSM-Documentation/) and
[source repository](https://github.com/ISSMteam/ISSM) were checked as official entrypoints.
[JPL capability index](https://issm.jpl.nasa.gov/documentation/) links GlaDS, SHAKTI,
sea-level and other modules; those detailed chapters are not covered here. Cluster setup,
restart APIs, full parameter tables and lab configurations require additional evidence.
