# ISSM: pitfalls — looks right, is wrong

Scope: each "Why it is wrong" field carries a caution moved from this pack's other topic files, unchanged in substance, with its original source id where the original had one. The other fields are editorial framing that adds no model fact; where framing would need a fact absent from the source record, the field says "not stated in the source record". `Checked:` dates are unchanged.

## Unweighted mean over a refined mesh mistaken for an area mean

- What is commonly concluded: averaging a scalar over the mesh vertices gives its area mean.
- Why it looks right: a plain vertex average is the default reduction, and every vertex contributes one value, which reads like fair sampling.
- Why it is wrong: do not take an unweighted mean over vertices of a refined mesh: dense sampling would count more than coarse sampling of the same physical area.
- What observation exposes it: compare with the area-weighted alternative; see the limited linear-triangle integration example in [outputs](outputs.md).
- Scope and source: [I4](sources.md#i4).

## A completed velocity solve mistaken for a transient thickness history

- What is commonly concluded: a converged stress-balance/velocity solve explains how ice thickness evolved.
- Why it looks right: velocity is the quantity that transports ice, so a valid velocity field looks like the mechanism behind any thickness change.
- Why it is wrong: a completed velocity solve alone says nothing about how thickness evolved through time.
- What observation exposes it: not stated in the source record.
- Scope and source: [I1](sources.md#i1).

## Water-equivalent and ice-equivalent rates mixed without conversion

- What is commonly concluded: surface-balance and basal-melt rates can be combined or compared directly regardless of the units in which each is reported.
- Why it looks right: both read as rates of the same kind, ready to add or difference.
- Why it is wrong: do not mix water-equivalent and ice-equivalent rates without conversion.
- What observation exposes it: confirm which convention each term uses before combining them.
- Scope and source: [I3](sources.md#i3).

## Integration weights reused after a mesh or mask change

- What is commonly concluded: grounded/floating/all-ice statistics computed once can be reapplied after the grounding line or mask moves.
- Why it looks right: recomputing weights is easy to forget when only a mask or grounding state was updated.
- Why it is wrong: grounded, floating and all-ice statistics need explicit masks and treatment of partial elements; recompute or align integration weights after mesh/mask changes.
- What observation exposes it: not stated in the source record.
- Scope and source: [I6](sources.md#i6).
