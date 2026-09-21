# RBM: execution boundaries and input checks

Identity status: UW-Hydro candidate only. The checked Salmon River guide explicitly targets VIC_RBM2.2 with VIC 4.2.d; its recipes are not a current, universal RBM command interface. [R3](sources.md#r3)

## Establish the implementation first

Recover repository/branch, input producer and one existing successful case from the actual project. If those are absent, explain the model and inspect candidate data, but do not invent a compiler command, control-file layout or restart capability.

The tutorial separates hydrological forcing, routing/network inputs and temperature-model inputs. Flow direction and routing response information establish network transport; the thermal setup also requires headwater-temperature and hydraulic relationships. [R2](sources.md#r2)

## Recommended preflight

1. Check the network's topology, outlet, reach/node identifiers and the ordering expected by the input reader. Matching latitude/longitude alone is insufficient at confluences.
2. Trace discharge, meteorological/heat inputs and boundary temperatures back to their producers. Confirm units, sign, timestamps, interval meaning and missing values.
3. Check whether hydraulics are supplied or derived and which parameters control that relationship. Preserve adopted coefficients while diagnosing operational issues.
4. Select a small existing case and verify that preprocessing, routing and thermal output can be followed separately. Write into a new directory within the agreed budget.
5. Inspect completion and expected network/time coverage; then compare a simple boundary or internal consistency case before scaling the run.

The historical Salmon example contains daily-specific assumptions, whereas the broader tutorial discusses daily or subdaily temperatures. See [pitfalls](pitfalls.md#a-daily-specific-example-edited-to-a-different-timestep) before changing its timestep by editing one value. [R2](sources.md#r2), [R3](sources.md#r3)

If inputs came from a newer hydrological driver, establish the conversion explicitly; the old example is not evidence that its preprocessing scripts accept the new format. Record executable revision, network, control data, upstream run identifiers and logs. Use the [Run feature](../../run.md) for retries and submission authority.

No laboratory routing choice, parameter calibration, reservoir setup or recovery recipe is adopted by this knowledge pack. An unresolved identity or format blocks dependent execution, not a conceptual explanation of river-temperature modeling.
