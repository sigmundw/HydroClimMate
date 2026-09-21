# MODFLOW: pitfalls — looks right, is wrong

Scope: each "Why it is wrong" field carries a caution moved from this pack's other topic files, unchanged in substance, with its original source id where the original had one. The other fields are editorial framing that adds no model fact; where framing would need a fact absent from the source record, the field says "not stated in the source record". `Checked:` dates are unchanged.

## Head change multiplied by area treated as storage volume

- What is commonly concluded: multiplying a hydraulic-head change by cell area gives the groundwater volume gained or lost.
- Why it looks right: a length times an area has units of volume, which looks like the right dimensional operation.
- Why it is wrong: multiplying head by cell area does not generally give groundwater storage.
- What observation exposes it: use the storage budget and model definitions before interpreting head changes as water gain or loss.
- Scope and source: [G3](sources.md#g3).

## Absence of a saved budget record taken as evidence of zero exchange

- What is commonly concluded: if no budget record for a term appears in the saved output, that exchange was zero.
- Why it looks right: a missing entry reads like "nothing happened" rather than "not saved".
- Why it is wrong: the absence of a saved budget record is not proof of zero exchange.
- What observation exposes it: check the output requests and saved-time mapping preserved with the analysis.
- Scope and source: [G8](sources.md#g8).

## Internal cell-to-cell exchanges summed as external inflow

- What is commonly concluded: summing all reported flow exchanges gives total external inflow to the model domain.
- Why it looks right: every exchange term is expressed as a flow, so adding them all looks like a complete inventory.
- Why it is wrong: summing all exchanges as external inflow double-counts internal transfers; define a control volume.
- What observation exposes it: not stated in the source record.
- Scope and source: not stated in the source record; the original statement carried no citation.

## Small global budget discrepancy taken as evidence of a correct model

- What is commonly concluded: a small overall water-budget discrepancy confirms the recharge and boundary conditions are correctly specified.
- Why it looks right: a near-zero global imbalance is what a working numerical model is expected to show, so it reads as a validity check.
- Why it is wrong: a small discrepancy demonstrates numerical balance, not correct recharge or boundaries.
- What observation exposes it: not stated in the source record.
- Scope and source: not stated in the source record; the original statement carried no citation.
