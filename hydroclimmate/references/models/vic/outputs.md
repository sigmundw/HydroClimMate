# VIC: runoff, storage and spatial aggregation

Scope: VIC5 documentation, not a cross-version output schema. Confirm the active driver,
actual variable attributes and output aggregation configuration before using a field.

## Separate quantity, statistic and support

The documented variable catalog distinguishes surface runoff, bottom-layer baseflow,
evaporation, soil-water storage and snow diagnostics. Its water flux entries often use
depth units rather than discharge units. See
[pitfalls](pitfalls.md#catalog-unit-assumed-to-fix-the-output-interval-and-aggregation)
before assuming the unit fixes the interval or aggregation. [V7](sources.md#v7)

Image outputs use netCDF and configurable streams. Retain the selected variables and
their temporal aggregation metadata with the data; file naming alone is not a definition
of an average or accumulation. [V8](sources.md#v8)

See
[pitfalls](pitfalls.md#grid-cell-aggregate-weighted-by-vegetation-or-band-fractions-a-second-time)
before weighting a grid-cell aggregate by its vegetation/band fractions again. For explicit
subgrid fields, establish the correct parent fractions before combining them. Geographic
area weighting is a separate step, using verified areas and basin overlap rather than
assuming every degree-spaced cell is equal area. [V2](sources.md#v2)

## Recommended analysis and routing handoff

- For a water budget, reconcile precipitation, net evaporation, included runoff components
  and storage change on the same spatial support and interval. Avoid double-counting a
  storage component already contained in a total.
- Distinguish layer water depth from volumetric water fraction when vertically aggregating.
  Check the layer thickness and phase definition against the actual field.
- Before routing, identify whether the input contract expects a depth rate, interval depth
  or volume rate. Include surface/subsurface contributions according to that contract;
  do not silently substitute one component for total runoff.
- A simple dimensional example: 1 mm over 1 km2 is 1,000 m3. Distributed uniformly over
  one day, it is about 0.011574 m3/s. This is local generated water, not the delayed outlet
  hydrograph. See
  [pitfalls](pitfalls.md#land-output-area-converted-a-second-time-by-the-receiving-routing-model)
  before area-converting it again at the receiving interface.
- Check a converted interval and a basin-integrated volume independently before processing
  the full record. Diagnose masks, gaps and resets before retuning the model.

For an actual mizuRoute coupling, use its [input contract](../mizuroute/execution.md).
No ready-made adapter or universal variable mapping is supplied by this pack.
