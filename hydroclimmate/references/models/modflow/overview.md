# MODFLOW: groundwater-flow model identity

Scope: USGS MODFLOW 6 groundwater flow (GWF). MODFLOW is a model family; MODFLOW-2005, NWT and other variants are not interchangeable input formats or solver configurations. The lab's executable and revision are unknown. The official framework distinguishes a simulation, timing, solutions, models and exchanges; a simulation can contain multiple models. Confirm which implementation is meant before interpreting a project. [G1](sources.md#g1)

## Processes and scientific choices

The flow calculation represents hydraulic-head response to aquifer properties, imposed stresses/boundaries and, for transient conditions, storage. In MODFLOW 6, flow-property and storage packages have separate responsibilities. Conductivity affects flow between cells; specific storage and specific yield concern water released or taken into storage under the applicable cell formulation. They are not interchangeable calibration knobs. [G2](sources.md#g2), [G3](sources.md#g3)

For a particular study, identify the conceptual aquifer system, initial heads, recharge, pumping and boundary conditions before choosing numerical settings. Recharge is not automatically equal to precipitation or land-model runoff; transferring either requires a physical definition and compatible area/time support. This is research guidance, not a prescribed recharge method or a complete unsaturated-zone model.

## Identify discretization before analysis

The documented flow discretizations include structured layer/row/column cells (DIS), layered vertex-defined cells (DISV), and unstructured connectivity (DISU). Structured spacing can vary. A vertex-defined grid does not imply that simulated head is a nodal finite-element field. Distinguish cell geometry from the location and support of a quantity before applying the shared mesh-analysis rules. [G4](sources.md#g4)

Use [execution](execution.md) for timing, boundary and convergence checks and [outputs](outputs.md) for head, flow and budget interpretation. A converged numerical solution is not evidence that the conceptual boundaries or inferred aquifer parameters are correct; evaluate appropriate observations and study-specific sensitivities separately.

Transport, variable density, energy, advanced well/lake/stream packages and full FloPy automation are outside this first pack. They require their own matching documentation; the name MODFLOW 6 does not establish that such processes were active in a simulation.
