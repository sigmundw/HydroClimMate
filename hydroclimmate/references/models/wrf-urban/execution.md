# WRF-Urban: execution checks

Scope: the standard real-data workflow described by the rolling WRF guide. Use an existing version-matched project recipe for actual commands and scheduler configuration.

## Prepare the chain, not only the final executable

WPS separates static geographic processing, meteorological decoding and interpolation to the model grid. The atmospheric initialization and integration then use those prepared inputs. Keep WRF and WPS versions, tables, source meteorology and geographic data with the experiment provenance. [W2](sources.md#w2), [W3](sources.md#w3)

Before a small trial, inspect geographic categories, urban fractions and the fields required by the selected urban option. Check that urban parameter tables and the chosen land-surface and boundary-layer physics are compatible in the actual release. The guide's current compatibility list is not a guarantee for an older checkout. [W1](sources.md#w1)

## Recommended staged checks

1. Inspect the prepared domain and meteorological intervals, projection and nested-domain coverage. Plot a small diagnostic of the urban mask/fraction if it resolves uncertainty.
2. Check initialization logs and expected initial/boundary files before atmospheric integration; passing preprocessing does not establish successful initialization.
3. Start a short authorized integration with the agreed physics and output requests. Check elapsed model time, log status, readable output, domain and obvious invalid values.
4. For continuation, inspect matching restart records, domain configuration, boundary coverage and existing jobs. Do not append blindly to a directory containing another run.

WRF's run guide describes separate initialization/integration and restart operation. Use its version-matched settings rather than treating a successful scheduler submission as successful integration. [W3](sources.md#w3)

Capture the actual namelists and parameter tables used, not only their editable source templates. When a run fails, locate the failing stage before changing resources or physics. Changing an urban scheme to bypass a failure changes the scientific experiment and requires adoption. Keep all such work within the [Run feature](../../run.md) authorization boundary.

This reference deliberately omits executable flags, machine modules, default timesteps and an urban-parameter calibration recipe. If those cannot be established from the local project offline, identify the missing setting instead of inventing a plausible one.
