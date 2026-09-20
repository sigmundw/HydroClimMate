# ISSM: mesh statistics and mass change

Scope: basic interpretation and an explicitly limited integration example. Source records
identify JPL documentation checked 2026-09-16, not the version of an unknown output file.

## Establish the field and domain

Confirm the solution type, saved time, units, mesh connectivity, and whether each quantity
is nodal, elemental, depth-averaged or defined at a particular vertical level. The official
ISMIP example illustrates mixed vertex/element associations. [I4](sources.md#i4)

See [pitfalls](pitfalls.md#unweighted-mean-over-a-refined-mesh-mistaken-for-an-area-mean)
before averaging over mesh vertices. For a planar, fully included triangle
with **linear nodal interpolation**, the integral of a scalar is exactly
`A * (v1 + v2 + v3) / 3`. Summing those integrals and dividing by total included area gives
the area mean. This is an elementary integration derivation for linear basis functions,
not a statement that every ISSM field uses that interpolation. For higher-order fields,
partial elements, curved geometry or volume integrals, use the appropriate basis and
quadrature. Establish the projection/physical-area convention before treating map area
as ground area. See [shared spatial checks](../../analyze.md#identify-grid-or-mesh-before-spatial-processing).

## Distinguish thickness, volume and mass

Thickness is a length. On a fixed horizontal domain, integrating thickness gives ice volume;
mass additionally requires a stated density model. A simple constant-density calculation
is `delta_mass = rho_ice * integral(delta_thickness dA)`, in kilograms for SI inputs.
This derived expression is conditional: evolving footprints require evaluating each volume
on its own domain, and firn/density changes need additional treatment. It is not an automatic
sea-level-equivalent calculation.

The documented mass-transport balance includes transport divergence and surface/basal
terms; surface accumulation and positive basal melt have opposite effects on thickness.
Do not infer thickness change from surface balance alone. See
[pitfalls](pitfalls.md#water-equivalent-and-ice-equivalent-rates-mixed-without-conversion)
before mixing water-equivalent and ice-equivalent rates. [I3](sources.md#i3)

Grounding-line schemes can represent partly grounded elements. See
[pitfalls](pitfalls.md#integration-weights-reused-after-a-mesh-or-mask-change) before reusing
prior integration weights after such a change. [I6](sources.md#i6)

Validate using a constant field, a linear-field case and a known area before a real integral.
For a physical budget, state domain, time interval, all included fluxes and residual tolerance.
The mass and quadrature formulas above are tested with synthetic examples in the repository
evaluation, not validated against an ISSM executable or a lab dataset.
