# HRLDAS / Noah-MP: pitfalls — looks right, is wrong

Scope: each "Why it is wrong" field carries a caution moved from this pack's other topic files,
unchanged in substance, with its original source id where the original had one. The other fields
are editorial framing that adds no model fact; where framing would need a fact absent from the
source record, the field says "not stated in the source record". `Checked:` dates are unchanged.

## Paired urban on/off snow difference attributed to canopy physics

- What is commonly concluded: a paired run with `SF_URBAN_PHYSICS` on vs off that shows a
  snow-variable difference on urban cells demonstrates the urban canopy's effect on snow.
- Why it looks right: the only configuration change was urban physics, so a remaining difference
  looks attributable to the urban canopy.
- Why it is wrong: at source commit `d9f5b205` (`noahmp` submodule `9fbe672`), `drivers/hrldas`
  build path: enabling urban physics (`SF_URBAN_PHYSICS>0`) reassigns the Noah-MP column
  vegetation type for urban cells to the parameter table's `NATURAL` class (class 14 in the MODIS
  table; `GVFMAX` forced to 96%) before the urban routine runs. That routine then tile-weights
  only surface energy and radiative fields (`TSK`, `HFX`, `QFX`, `LH`, `GRDFLX`, `ALBEDO`,
  `EMISS`, `QSFC`) by `FRC_URB2D`; snow-state variables are never passed to it. A paired on/off
  difference in snow variables on urban cells can reflect the vegetation-table swap rather than
  urban canopy physics.
- What observation exposes it: a genuine tile effect should scale with `FRC_URB2D`; a flat or
  non-monotonic response is a warning sign, not confirmation — flux scaling with `FRC_URB2D` was
  not established here.
- Scope and source: verified only for this source version and driver path; not verified for other
  Noah-MP drivers or releases. [H6](sources.md#h6).

## Snow-water-equivalent identity and unmasked fill values

- What is commonly concluded: snow water equivalent should equal ice plus liquid layer stores,
  and snow fields whose numbers read back without complaint are valid data.
- Why it looks right: both are default expectations — that an identity holds, and that a reader
  masks fill values for you.
- Why it is wrong: a layer-mass identity such as snow water equivalent equal to ice plus liquid
  layer stores may not hold in a zero-layer state, where a scalar total can carry mass while the
  layer arrays read zero. Some outputs carry a large negative fill (order `-1e33`) on water-body
  cells for snow fields with no declared `_FillValue`/`missing_value` attribute, so standard
  libraries will not mask them automatically.
- What observation exposes it: check the layer-count variable before assuming the identity,
  especially in a mass budget; confirm the fill convention and mask explicitly.
- Scope and source: not stated in the source record; the original statement carried no citation.

## Existing restart filename assumed to prove a successful restart

- What is commonly concluded: if a restart file with the expected name exists, the run
  successfully restarted.
- Why it looks right: the job ended and a file with the expected name is present.
- Why it is wrong: a successful restart reads and advances the intended state; merely finding a
  restart filename is not that evidence.
- What observation exposes it: check restart time and configuration and forcing continuity, not
  the filename alone.
- Scope and source: not stated in the source record; the original statement carried no citation.
