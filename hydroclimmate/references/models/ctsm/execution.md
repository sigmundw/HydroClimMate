# CTSM: cases, configuration and initialization

Scope: conceptual case workflow using the rolling CTSM user guide. Exact commands, input
paths and defaults depend on the checkout and machine and are intentionally not prescribed.

## Identify the case before running it

Choose or recover the actual compset and resolution/domain before diagnosing downstream
settings. Data-atmosphere land experiments and active-atmosphere experiments impose
different boundary conditions; changing the component set changes the study.
[C4](sources.md#c4)

The user guide distinguishes configuration, land namelist and atmospheric-driving settings.
The land user namelist customizes generated model settings; input datasets and history
requests are among the relevant controls. Inspect the resulting configuration rather than
assuming the user edit alone describes the executed case. [C5](sources.md#c5)

## Recommended preparation

1. Record code revision, compset, grid/mesh and machine configuration; verify required
   input datasets are available and match the domain and intended period.
2. Inspect the actual atmosphere/forcing stream, calendar and time coverage. Do not copy
   a demonstration data path or assume its forcing cycle is appropriate locally.
3. Establish initial-state provenance and whether the work is a new experiment or a
   continuation. Identify active stores and the diagnostics used to assess equilibration.
4. Verify setup/build evidence and run a short authorized case into a distinct location.
   Check elapsed model time, logs, readable history and planned restart products.
5. Before continuation, verify state/configuration compatibility, completed timestep,
   remaining forcing coverage and output preservation.

A short stable hydrological trajectory is not evidence that slower carbon or nutrient
stores are equilibrated. Define the study's convergence criterion instead of selecting a
universal spin-up duration. This is experimental guidance, not an instruction to enable
biogeochemistry or a particular accelerated spin-up method.

The developer guide can expose options not present in an older release. Offline, use the
local case tools and version-matched examples; report an unavailable parameter as a gap,
not a guessed name. See the [source scope](sources.md) and [Run feature](../../run.md).

Record the generated namelist/configuration, initial data, executed command and logs with
the run. Successful submission or a completed build does not establish completed model
integration. This pack has not executed a CTSM case and contains no lab machine settings.
