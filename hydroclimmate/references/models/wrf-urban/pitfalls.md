# WRF-Urban: pitfalls — looks right, is wrong

Scope: each "Why it is wrong" field carries a caution moved from this pack's other topic files,
unchanged in substance, with its original source id where the original had one. The other fields
are editorial framing that adds no model fact; where framing would need a fact absent from the
source record, the field says "not stated in the source record". `Checked:` dates are unchanged.

## Perturbation, base-state or accumulated fields plotted as if directly usable

- What is commonly concluded: an output variable that appears on the expected grid can be plotted
  as-is.
- Why it looks right: the variable has the expected name and dimensions, so it appears ready to
  plot.
- Why it is wrong: a variable that looks directly plottable may require a diagnostic
  transformation or time differencing first.
- What observation exposes it: read the actual file header's dimensions and definitions before
  plotting.
- Scope and source: [W5](sources.md#w5).

## Missing diagnostic assumed to mean the process was disabled

- What is commonly concluded: if a desired diagnostic is absent from the output, the underlying
  process was not active in the run.
- Why it looks right: an active process is expected to leave an output field, so its absence
  reads as evidence it did not run.
- Why it is wrong: the absence of a desired diagnostic does not establish that the process was
  disabled.
- What observation exposes it: check the history configuration and corresponding model
  implementation.
- Scope and source: [W4](sources.md#w4).

## Accumulated quantity divided by a nominal timestep

- What is commonly concluded: dividing an accumulated output field by the model's nominal
  timestep gives its rate.
- Why it looks right: the field accumulates over time, so a timestep is the obvious divisor.
- Why it is wrong: do not divide by a nominal timestep when output intervals vary.
- What observation exposes it: check the actual saved output intervals rather than assuming a
  fixed nominal one.
- Scope and source: not stated in the source record; the original statement carried no citation.

## Fixed nominal grid spacing treated as equal ground area

- What is commonly concluded: a domain with fixed nominal grid spacing, or one carrying
  two-dimensional latitude/longitude fields, has equal-area cells.
- Why it looks right: a single spacing value and explicit coordinate arrays look like enough
  geographic information for area weighting.
- Why it is wrong: fixed nominal grid spacing or two-dimensional latitude/longitude is not proof
  of equal ground area.
- What observation exposes it: not stated in the source record.
- Scope and source: not stated in the source record; the original statement carried no citation.
