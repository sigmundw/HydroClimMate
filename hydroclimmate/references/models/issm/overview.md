# ISSM: ice flow and mass change

Scope: basic ice-flow reasoning, mesh-aware interpretation and mass change. The local
installation, revision and MATLAB/Python interface are unknown. JPL web chapters checked
2026-09-16 are conceptual references, not a pinned specification for current APIs.

## Distinguish the questions being solved

A stress-balance calculation determines a velocity field for supplied geometry, material
properties and boundary conditions. ISSM's documentation describes viscous, incompressible
ice and a hierarchy of stress approximations. SSA neglects vertical shear; higher-order
and full-Stokes formulations retain different terms. They are scientific approximations,
not interchangeable performance switches. A completed velocity solve alone says nothing
about how thickness evolved through time. [I1](sources.md#i1)

A transient calculation advances a configured selection of components through time.
Stress balance can be one component alongside thickness transport, thermal evolution or
other enabled processes. The word transient does not imply every process is active; inspect
the selected components before explaining a trajectory. [I2](sources.md#i2)

Mass transport connects thickness change to ice transport and surface/basal source terms.
The documented depth-integrated convention uses surface accumulation positive for gain
and basal melt positive for loss, expressed as ice-equivalent rates. A simulation's actual
fields and conversion code must still be checked. [I3](sources.md#i3)

## What the mesh represents

ISSM examples distinguish values assigned to vertices from values assigned to elements.
The ISMIP tutorial, for example, uses vertex-sized and element-sized parameter arrays in
the same model. Array length alone is not a physical area weight. [I4](sources.md#i4)

The diagnostic consequence is to ask which discrete field and domain are being integrated
before computing a regional statistic. See [outputs](outputs.md) for a limited linear-triangle
example, and [execution](execution.md) for checks before a solve.

## Inversion and coverage boundary

Inversion estimates controls by minimizing a chosen mismatch with observations, potentially
with regularization. A good fit does not independently establish future predictive skill;
the control choice, objective and observational uncertainty remain research decisions.
Use the inversion chapter for method-specific details. [I7](sources.md#i7)

Sea-level, GlaDS, SHAKTI and other subglacial hydrology capabilities are navigation-only in
this release. They are not implied by the ice-flow coverage. The [source record](sources.md)
links the official capability index and identifies material not distilled here.
