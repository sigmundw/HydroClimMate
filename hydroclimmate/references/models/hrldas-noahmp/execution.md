# HRLDAS / Noah-MP: execution

Scope: concepts plus the official master-branch namelist description retrieved 2026-09-16.
That file is a floating source, not the lab's configuration or a pinned API specification.

## Prepare a consistent experiment

Keep the host and submodule revisions together and verify that the physics code is actually
present before diagnosing a build. The official tutorial provides separate download/build,
single-point and regional examples; use one matching the checkout rather than constructing
a command from an unrelated host. [H1](sources.md#h1), [H5](sources.md#h5)

In the checked namelist description, setup data, forcing input and derived output have
separate locations. The start date, duration and requested restart identify the experiment.
Its timing rule requires the model step to divide the forcing and output intervals. It also
describes repeated spin-up periods and an option to omit the first, initial-state output.
These are reasons to inspect generated configuration, not recommendations for numerical
values. [H4](sources.md#h4)

## Minimal preflight and continuation

Recommended checks for an actual project:

1. Identify the forcing time convention, units, completeness and spatial alignment with
   the setup data. A file timestamp alone does not establish its represented interval.
2. Record the adopted physics options and parameter files. Inspect the checkout's parser
   before applying a namelist key learned from another version.
3. State whether the run starts from prescribed fields, repeated forcing spin-up or a
   compatible restart. Choose an equilibration diagnostic and tolerance for the stores
   relevant to the study; a prescribed number of loops is not proof of equilibrium.
4. Run a short authorized interval into a separate directory and inspect timestamps,
   missing values and the requested state/flux diagnostics.
5. Before continuation, check restart time and configuration, forcing continuity, existing
   live jobs and whether the executable would append to or replace outputs.

Capture the executed configuration and logs, not only the template namelist. A successful
restart reads and advances the intended state; merely finding a restart filename is not
that evidence. Retain the [Run feature](../../run.md) resource and submission boundaries.
No compiler, HPC command or universally appropriate spin-up length is supplied here.
