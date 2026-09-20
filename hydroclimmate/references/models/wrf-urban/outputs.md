# WRF-Urban: interpreting outputs

Scope: semantic checks around WRF history output. The official output-variable list is
illustrative for its documented system; the actual file header and build remain decisive.

## Read dimensions and definitions before plotting

WRF output contains variables on different horizontal/vertical locations, including
staggered dimensions. See
[pitfalls](pitfalls.md#perturbation-base-state-or-accumulated-fields-plotted-as-if-directly-usable)
before plotting a field as-is. [W5](sources.md#w5)

History and restart outputs serve different purposes, and output requests can be customized.
See [pitfalls](pitfalls.md#missing-diagnostic-assumed-to-mean-the-process-was-disabled)
before concluding an absent diagnostic means a disabled process. Check the history
configuration and corresponding model implementation. [W4](sources.md#w4)

## Recommended analysis sequence

- Confirm the quantity: urban-only versus full-cell, canopy air versus surface, flux versus
  state. Inspect the active urban scheme and the output assignment if the header is ambiguous.
  When HRLDAS hosts the urban option rather than a WRF-coupled run, see the
  [HRLDAS/Noah-MP pitfalls: paired urban on/off snow difference](../hrldas-noahmp/pitfalls.md#paired-urban-onoff-snow-difference-attributed-to-canopy-physics) —
  that host's urban routine may not tile-weight every state variable the way this pack's
  fields do.
- Establish spatial support before comparing urban and rural samples. A change in sample
  mask or urban fraction can change the reported mean without a local physical response.
- For vector fields, check staggering and coordinate orientation before interpolation or
  combining components. Do not assume identical array shape means identical physical support.
- For accumulated quantities, identify initial values and restart/reset behavior before
  differencing. See [pitfalls](pitfalls.md#accumulated-quantity-divided-by-a-nominal-timestep)
  before dividing by a nominal timestep.
- For area statistics, check projection and map-scale/area information; see
  [pitfalls](pitfalls.md#fixed-nominal-grid-spacing-treated-as-equal-ground-area) before
  treating fixed nominal grid spacing as equal ground area.
  Use the [shared spatial guidance](../../analyze.md#identify-grid-or-mesh-before-spatial-processing).
- Keep local-time and UTC interpretation explicit in a diurnal urban analysis. Match the
  observation's measurement height and temporal statistic to the modeled diagnostic.

Validate one selected location and interval against the raw output before producing a
regional plot. Preserve metadata and the transformations used to produce the figure.
The checks above are analysis recommendations, not claims that every WRF output needs
every transformation. No urban heat-island definition is selected on the researcher's behalf.
If a diagnostic is version-specific and absent from the local pack, trace the available
local Registry/output code or mark its interpretation unresolved.
