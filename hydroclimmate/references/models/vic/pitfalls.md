# VIC: pitfalls — looks right, is wrong

Scope: each "Why it is wrong" field carries a caution moved from this pack's other topic files,
unchanged in substance, with its original source id where the original had one. The other fields
are editorial framing that adds no model fact; where framing would need a fact absent from the
source record, the field says "not stated in the source record". `Checked:` dates are unchanged.

## Local runoff treated as gauge discharge

- What is commonly concluded: the runoff a VIC cell generates can be compared directly with a
  downstream gauge's discharge.
- Why it looks right: both are water on its way to a river, so the comparison looks natural.
- Why it is wrong: VIC's standard land calculation and river routing are separate
  responsibilities: runoff generated in a cell is not yet discharge at a downstream gauge.
- What observation exposes it: check whether a routing step was applied between the land output
  and the point of comparison.
- Scope and source: [V1](sources.md#v1), [V2](sources.md#v2).

## Catalog unit assumed to fix the output interval and aggregation

- What is commonly concluded: a variable's documented unit is enough to know its output interval
  and whether it is a mean, total or instantaneous value.
- Why it looks right: the unit is in the catalog, and it is tempting to read it as the complete
  definition of the field.
- Why it is wrong: a catalog unit alone does not specify the actual output interval or
  aggregation operator.
- What observation exposes it: inspect the actual output configuration rather than the catalog's
  unit alone.
- Scope and source: [V7](sources.md#v7).

## Grid-cell aggregate weighted by vegetation or band fractions a second time

- What is commonly concluded: applying vegetation-tile or elevation-band fraction weights to an
  already grid-cell-aggregated output refines the estimate.
- Why it looks right: fraction weighting is the correct step for genuinely subgrid fields, so it
  looks safe wherever fractions are available.
- Why it is wrong: do not weight a grid-cell aggregate by its vegetation/band fractions again.
- What observation exposes it: inspect the output support before applying a second set of weights.
- Scope and source: [V2](sources.md#v2).

## Land output area-converted a second time by the receiving routing model

- What is commonly concluded: a land-model runoff field can pass through the same area conversion
  twice, once when produced and once when the routing model ingests it, without harm.
- Why it looks right: area conversion is a standard preprocessing step, so applying it at each
  interface looks like normal defensive practice.
- Why it is wrong: an already converted land output must not be area-converted again by the
  receiving interface.
- What observation exposes it: identify what the receiving input contract expects before
  converting again.
- Scope and source: not stated in the source record; the original statement carried no citation.
