# CTSM: pitfalls — looks right, is wrong

Scope: each "Why it is wrong" field carries a caution moved from this pack's other topic files,
unchanged in substance, with its original source id where the original had one. The other fields
are editorial framing that adds no model fact; where framing would need a fact absent from the
source record, the field says "not stated in the source record". `Checked:` dates are unchanged.

## Unweighted subgrid average mistaken for grid-cell mean

- What is commonly concluded: averaging column or PFT values directly gives the grid-cell mean.
- Why it looks right: a plain mean is the default operation on a set of values.
- Why it is wrong: landunits, columns and vegetation patches/PFTs form a subgrid hierarchy with
  fractional areas; an unweighted average of columns or PFTs is generally not a grid-cell mean.
- What observation exposes it: combining values at one level requires the appropriate parent
  relation and weights; compare against a mean formed that way.
- Scope and source: [C3](sources.md#c3).

## Grid-cell field re-weighted by a subgrid fraction a second time

- What is commonly concluded: applying a subgrid-fraction weight to an already grid-cell-
  aggregated variable refines the estimate.
- Why it looks right: the fraction is readily available, and fraction weighting is the correct
  step for a genuinely subgrid value.
- Why it is wrong: a value already aggregated to the grid cell must not be weighted by the same
  subgrid fraction a second time.
- What observation exposes it: establish the variable's aggregation level before combining it
  with a fraction.
- Scope and source: [C3](sources.md#c3).

## Missing or excluded subgrid entries silently treated as zero

- What is commonly concluded: absent columns or PFTs contribute zero to a regional aggregate.
- Why it looks right: a gap and a zero look the same once values are summed.
- Why it is wrong: do not silently treat inactive, missing or excluded subgrid entries as zero.
- What observation exposes it: establish the field's area basis and check that fractions are
  referenced to the correct parent and time.
- Scope and source: not stated in the source record; the original statement carried no citation.

## A monthly-looking filename or timestamp assumed to define the averaging period

- What is commonly concluded: a file whose name or timestamp suggests "monthly" holds a plain
  monthly average or total.
- Why it looks right: a name or timestamp reads as a description of the contents.
- Why it is wrong: output frequency and averaging settings must be inspected, not inferred from
  a monthly-looking filename or timestamp; history requests are configurable through the namelist.
- What observation exposes it: check the generated history settings together with file metadata.
- Scope and source: [C5](sources.md#c5).
