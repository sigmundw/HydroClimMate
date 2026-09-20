# RBM: pitfalls — looks right, is wrong

Scope: each "Why it is wrong" field carries a caution moved from this pack's other topic files,
unchanged in substance, with its original source id where the original had one. The other fields
are editorial framing that adds no model fact; where framing would need a fact absent from the
source record, the field says "not stated in the source record". `Checked:` dates are unchanged.

## A passing build treated as validation of a new option combination

- What is commonly concluded: if a modified RBM configuration builds and runs to completion, that
  combination of options is scientifically validated.
- Why it looks right: a build that completes is the usual informal sign that something works.
- Why it is wrong: the repository characterizes RBM as research software with unevenly tested
  combinations of options. Passing its build is therefore not a validation of a new combination.
- What observation exposes it: not stated in the source record.
- Scope and source: [R4](sources.md#r4).

## Downstream node discharges summed for basin discharge

- What is commonly concluded: summing the discharge reported at every downstream node gives total
  basin discharge.
- Why it looks right: each node reports a discharge value, so adding them looks like a complete
  accounting.
- Why it is wrong: do not sum discharges at all downstream nodes to obtain basin discharge:
  repeated transport along the network can count the same water multiple times.
- What observation exposes it: not stated in the source record.
- Scope and source: not stated in the source record; the original statement carried no citation.

## A realistic seasonal cycle taken as proof of correct network mapping

- What is commonly concluded: because the simulated series shows a plausible seasonal cycle, the
  network mapping and inputs must be correct.
- Why it looks right: a reasonable-looking result is often used informally as a sanity check that
  a model chain is wired correctly.
- Why it is wrong: a realistic seasonal cycle is not proof that all network links were mapped
  correctly.
- What observation exposes it: not stated in the source record.
- Scope and source: not stated in the source record; the original statement carried no citation.

## A daily-specific example edited to a different timestep

- What is commonly concluded: because the broader tutorial discusses daily or subdaily
  temperatures, the historical example can be run at a different timestep by editing one value.
- Why it looks right: the general documentation mentions both resolutions, which reads as
  permission to switch the example's timestep.
- Why it is wrong: treat the difference between the historical Salmon example's daily-specific
  assumptions and the broader tutorial's discussion as a prompt to verify the local
  implementation, not permission to change a timestep by editing one value.
- What observation exposes it: verify the local implementation before changing it.
- Scope and source: [R2](sources.md#r2), [R3](sources.md#r3).
