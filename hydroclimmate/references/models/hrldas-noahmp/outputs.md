# HRLDAS / Noah-MP: output interpretation

Scope: semantic checks for offline output. Exact output names, units, time statistics and
available budget terms must come from the actual files and corresponding driver revision.

## Follow the output interface

The v5.0 design separates column physics from a host-facing I/O representation. An internal
process variable and a written history variable need not have the same name or shape.
Trace the output through the host interface when metadata is insufficient. [H3](sources.md#h3)

The official tutorial index includes a dedicated lesson on adding output variables. This
establishes an appropriate route for extending diagnostics; this pack does not reproduce
the notebook's code or assert that its edits fit another revision. [H5](sources.md#h5)

The checked namelist separates forcing, model and output intervals, and can suppress the
initial-state record. Do not treat an initial record with no completed flux interval as an
ordinary averaged timestep. [H4](sources.md#h4)

See
[pitfalls](pitfalls.md#paired-urban-onoff-snow-difference-attributed-to-canopy-physics)
before attributing a paired urban on/off snow difference on urban cells to canopy physics
rather than the version-scoped vegetation-table swap.

## Recommended analysis checks

- Distinguish water stored in a layer from a concentration or volumetric water fraction.
  A column inventory requires the relevant thickness, phase and unit conversions; adding
  layer values without their meaning can produce a plausible but incorrect total.
- See [pitfalls](pitfalls.md#snow-water-equivalent-identity-and-unmasked-fill-values) before
  trusting a snow-water-equivalent layer identity or automatic fill masking.
- For fluxes, establish instantaneous rate, interval mean, interval total or cumulative
  counter. Integrate rates over represented durations; difference counters only after
  identifying their restart/reset behavior.
- Separate locally generated runoff from routed river discharge. Comparing a local depth
  flux directly with a gauge discharge needs a defensible drainage-area and routing basis.
- Inspect grid mapping, cell areas and masks. A WRF-derived geographic setup is not evidence
  of equal physical cell area. Apply the [shared spatial rules](../../analyze.md#identify-grid-or-mesh-before-spatial-processing).
- Define budget scope before computing a residual: include relevant snow, canopy, soil and
  other active stores and boundary fluxes. If a needed term is absent, report partial closure.

These checks are dimensional and diagnostic guidance, not an exhaustive model water-budget
formula. For a bias after a forcing change, compare the applied forcing first, then state
and flux responses over matching intervals. Preserve the original run while diagnosing.
An output glossary is linked in [sources](sources.md), but its entries were not fully audited.
