# ISSM: preparing and checking a solve

Scope: conceptual preflight, not an installation recipe or a release-specific command list.
First identify checkout/release, interface, analysis type and an existing project example.

## Build a meaningful model state

The official square-ice-shelf tutorial illustrates a sequence of model creation, mesh
generation, masking, parameterization, flow-equation selection and a stress-balance solve.
It is a MATLAB tutorial for an idealized shelf, not a validated recipe for a grounded glacier
or a Python installation. [I5](sources.md#i5)

Recommended preflight for the actual project:

- Verify geometry consistency, units and coordinate system; establish which mesh is used
  for the horizontal domain and whether a three-dimensional extrusion is present.
- Check input array association with vertices/elements and the intended boundary nodes.
  Check connectivity and degenerate elements before interpreting a numerical failure.
- Identify the flow approximation, rheology, friction law and boundary conditions. Do not
  silently substitute an approximation to reduce runtime or make convergence easier.
- Preserve the observation dataset and objective when reproducing an inversion; changing
  either defines a different experiment, not merely a solver adjustment.

The ISMIP example assigns distinct parameter fields at vertices and elements. Use the
installed classes and a matching example to establish array shape and constraints rather
than transplanting fields from another language binding. [I4](sources.md#i4)

## Select the requested outcome

For a diagnostic velocity solve, inspect the mechanical convergence evidence. The stress
chapter distinguishes residual and velocity convergence controls; no universal tolerance
is selected here. [I1](sources.md#i1)

For a time-dependent run, inspect enabled components, start/end times, time step and output
schedule. Check whether geometry and masks are updated as intended. A transient run may
disable some processes, so the solution name alone does not establish the experiment.
[I2](sources.md#i2)

Start with an authorized small case using separate output paths. Keep scripts, parameters,
model state, solver logs and revision together. Check an existing job before resubmitting;
solver termination and production of a result object do not prove physical validity.

A restart procedure, cluster configuration or parameter absent from this pack requires
evidence from the local installation. Report the missing interface detail rather than
inventing a MATLAB/Python equivalent. Apply the [Run feature](../../run.md) for resource
and authorization boundaries; no new job is authorized by this reference.
