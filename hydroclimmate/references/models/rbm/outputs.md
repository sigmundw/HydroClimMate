# RBM: network and temperature outputs

Identity status: UW-Hydro candidate; exact column layout and temporal resolution require the actual implementation. This pack provides no universal output parser.

## Keep producers separate

The coupled tutorial distinguishes gridded land-model quantities, routed streamflow and stream temperature at network locations. An RBM workflow can therefore contain files from several producers with different spatial and temporal support. Identify the producer before assigning meaning to a variable or averaging records. [R2](sources.md#r2)

The historical Salmon example's output description includes reach, node and segment identifiers. It distinguishes simulated stream temperature from headwater and air temperature fields. Confluence cells can contain multiple nodes, so coordinates alone are not a unique record key. [R3](sources.md#r3)

## Recommended evaluation

- Match observations to the relevant river reach/segment and timestamp. A nearby grid center is not necessarily the same river location or sampling support.
- Check whether temperatures are instantaneous, daily/subdaily means or another statistic before comparing them with observed maxima or irregular samples.
- For a point-temperature comparison, do not apply geographic cell-area weights. For a network aggregate, define the target measure explicitly: equal sites, stream length, water volume or another justified weighting answer different questions.
- See [pitfalls](pitfalls.md#downstream-node-discharges-summed-for-basin-discharge) before summing discharges at all downstream nodes. Use the intended outlet or non-overlapping control boundaries.
- Examine upstream flow/meteorological input, headwater boundaries and network mapping alongside a thermal bias. Separate structural limitations from corrupted preprocessing.
- When an input/output table mixes unit systems, record conversions at the interface and verify one record against the reader/writer before bulk analysis.

These are physical and data-consistency checks, not claims that a particular fork has every listed field. A river-temperature average is not a land-area mean. See [pitfalls](pitfalls.md#a-realistic-seasonal-cycle-taken-as-proof-of-correct-network-mapping) before treating a plausible seasonal cycle as proof of correct network mapping.

Preserve original files and write diagnostics separately. Report which observed quantity, locations and intervals were evaluated and what remained unmatched. If the branch or file schema is unconfirmed, state that limitation instead of assuming the historical example's column order. See [sources](sources.md) for the exact inspected example.
