# CTSM / CLM: identity and structure

Scope: CLM5-era physical concepts plus explicitly labeled rolling CTSM guidance checked
2026-09-16. The development documentation is not synonymous with the CLM5.0 release.
Identify the actual checkout, configuration and coupled components for a specific run.
[C1](sources.md#c1)

## What the land model represents

CTSM includes the Community Land Model. Its scientific description covers biogeophysical
and biogeochemical processes, including exchange with the atmosphere and water/energy
states in vegetation, soil and snow. A configuration determines which processes and
coupled components are active; the model name alone is not an experiment definition.
[C2](sources.md#c2)

Within a grid cell, land is represented through a hierarchy of landunits, columns and
vegetation patches/PFTs. These represent different physical supports rather than additional
independent geographic grid cells. For example, multiple vegetation patches can share a
soil column. Fractions mediate aggregation between levels. [C3](sources.md#c3)

The consequence for learning and analysis is to separate three questions: where a process
is computed, which state it acts on, and which spatial level is written to output. A
grid-cell average can conceal distinct subgrid responses. See [outputs](outputs.md).

## Configuration is part of the scientific description

A compset describes the combination of components and experiment choices. The user's
guide distinguishes land configurations driven by a data atmosphere from configurations
with active atmosphere and other components. Their feedbacks and forcing assumptions
are different. Do not substitute one because a tutorial command happens to work.
[C4](sources.md#c4)

For an experiment, identify the forcing period and calendar, surface dataset, active
biogeochemistry/vegetation choices, initial state and any transient land-use treatment.
This is a recommended identification checklist, not a requirement to open a project for
a conceptual question. A question about the hierarchy can be answered directly offline.

Do not infer dynamic ice-flow capability merely from a glacier-related land output or
infer routed stream discharge from local runoff. Establish the actual component and field
definition before linking outputs to another model. Cross-model comparisons require
aligned quantities and support, not just similarly named variables.

Use [execution](execution.md) for case preparation and [sources](sources.md) to distinguish
fixed technical-description concepts from rolling examples. Lab compsets are not specified.
