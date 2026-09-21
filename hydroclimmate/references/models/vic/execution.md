# VIC: preparing and continuing a run

Scope: VIC5 Classic/Image concepts from the rolling official documentation. No compiler, scheduler settings, executable flags or universal spin-up length are prescribed here.

## Match the driver and data

The official run guides have separate build/run instructions for Classic and Image; Image's parallel workflow must not be inferred from a legacy single-cell script. Use the matching checkout and example for the actual command. [V5](sources.md#v5)

Image inputs include global configuration, domain, meteorological forcing and model parameters, with initial state when used. Presence of netCDF files alone does not establish that their masks, coordinates, time axes or variables match the requested domain. [V6](sources.md#v6)

## Recommended preflight

1. Record code revision and driver; inspect the actual global configuration and data readers. Treat flags from VIC4 or a different driver as unverified until checked locally.
2. Verify forcing completeness, units, time convention and timestep against the selected model/snow stepping configuration. Do not assume an old daily-input disaggregation workflow is available in the current driver.
3. Confirm active cells, vegetation fractions, elevation bands and soil parameters are consistent. Inspect a representative cell with the intended physics before scaling.
4. Establish prescribed initialization versus saved state, start time and the stores whose equilibration matters. Set study-specific diagnostics instead of equating a number of spin-up repetitions with convergence.
5. Run a small authorized interval into a separate location; inspect logs, time coverage, budgets and the state/output products actually requested.

For continuation, match the saved state to the driver, physics, grid and time of the new run; verify forcing continuity and existing jobs before launching anything. This is a compatibility check, not a claim that states are interchangeable across versions.

If runoff will feed a routing model, define the exchange contract before production: included components, units, interval meaning, source-cell IDs and area basis. Preserve land outputs and create converted routing input separately. Record conversions in the run evidence and use the [Run feature](../../run.md) for resource limits and retry policy. Driver documentation explains mechanisms; it does not authorize installation or submission.
