# MODFLOW 6: simulation and run checks

Scope: groundwater-flow preparation, not a complete input catalog or a cross-version command recipe. Identify executable version and any preprocessing tool separately.

## Establish time, properties and stresses

MODFLOW 6 temporal discretization defines stress periods and the timesteps within them. These are distinct from output-saving frequency. A storage package can specify steady or transient behavior; do not infer it simply from the existence of several stress periods. [G5](sources.md#g5), [G3](sources.md#g3)

Recharge and wells have different dimensional contracts. The checked array-recharge description uses length per time, whereas a well rate is volume per time; extraction and injection use opposite signs in the well definition. A land-model depth flux cannot be inserted as a volumetric pumping rate without conversion and a justified physical role. [G6](sources.md#g6)

Recommended preflight:

1. Inspect the simulation/model configuration, enabled packages and actual executable. Do not rename a MODFLOW-2005/NWT input file and assume it is MODFLOW 6 compatible.
2. Check top/bottom elevations, thickness, active/pass-through cells, connectivity and boundary placement. Verify that property and stress arrays address the intended cells.
3. Use consistent length/time units across conductivity, storage, recharge and pumping. Check sign conventions and the time intervals represented by each stress dataset.
4. Establish initial heads, steady/transient periods and the scientific reason for their sequence; save the applied input state and output requests.
5. Run a small authorized case in a separate directory. Inspect solver/listing output, reached simulation time, selected head records and water budgets before scaling up.

The iterative-solution documentation has separate controls for outer and inner iteration, including dependent-variable change and residual closure. Their tolerances have different meanings; loosening one to force termination is not an accepted calibration step. [G7](sources.md#g7)

Do not treat a saved head array alone as a universally complete restart for every package and model combination. Establish continuation requirements from the local release and active processes. Solver messages, completion status and budget diagnostics belong in the run evidence. Apply the [Run feature](../../run.md) resource and retry rules; this reference grants no permission to install MODFLOW or submit a job.
