# mizuRoute: discharge, support and budgets

Scope: official stable output concepts. Use actual variable metadata and control settings
for the current revision; the pack does not prescribe output names or defaults.

## Identify which stage a field represents

The output guide distinguishes remapped HRU runoff, hillslope/instantaneous-runoff
diagnostics, method-specific routed discharge and storage-related quantities. Basin and
reach identifiers accompany the output; not every field has the same spatial meaning.
Output selection is configurable. [M6](sources.md#m6)

The channel guide explicitly allows upstream runoff accumulation without routing. It is
useful for separating volume production from transport, but is not evidence that timing
or attenuation has been simulated. [M4](sources.md#m4)

## Recommended checks

- Match a gauge to a reach ID, outlet and contributing drainage area. Nearest coordinates
  alone can select the wrong branch at a confluence.
- Do not sum every reach's discharge to obtain basin outflow: upstream water appears again
  in downstream reaches. Define one outlet or non-overlapping control boundaries.
- For volume comparison, integrate discharge over the represented interval. Account for
  routing storage change and applicable boundary/management fluxes before calling a
  difference a conservation error.
- Compare the same timestamp convention and temporal statistic. A depth accumulated over
  one interval cannot be compared directly with an instantaneous discharge sample.
- Separate a remapping volume error from a routing response error. Check source and target
  coverage and missing-data treatment before changing routing parameters.

For fully covered non-overlapping target HRUs with area A and mean depth rate r, generated
volume rate is the sum of A*r after unit conversion. This dimensional check is not a claim
that routed outflow equals inflow at every timestep. A pulse can be delayed and stored.
Do not compensate a lost-area remap by arbitrarily scaling the final hydrograph.

Use the [VIC output contract](../vic/outputs.md) only when VIC actually supplies the input;
other land models have their own variable/time conventions. Network averages, site means
and land-area means are distinct statistics. No area-weighting rule can be chosen solely
from the presence of latitude and longitude columns in a routing output file.
