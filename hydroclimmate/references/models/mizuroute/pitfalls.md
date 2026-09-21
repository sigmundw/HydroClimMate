# mizuRoute: pitfalls — looks right, is wrong

Scope: each "Why it is wrong" field carries a caution moved from this pack's other topic files, unchanged in substance, with its original source id where the original had one. The other fields are editorial framing that adds no model fact; where framing would need a fact absent from the source record, the field says "not stated in the source record". `Checked:` dates are unchanged.

## Depth-to-discharge conversion applied a second time

- What is commonly concluded: passing an already-converted field through the standard depth-to-volume conversion step is harmless or required by the workflow.
- Why it looks right: for the documented depth-based workflow, HRU area participates in converting runoff to volume, so that step looks like the expected preprocessing stage.
- Why it is wrong: a preprocessing step that has already converted depth to discharge cannot be passed unchanged through that conversion.
- What observation exposes it: establish whether the supplied data are depth or volume quantities before conversion.
- Scope and source: [M3](sources.md#m3).

## Upstream-accumulation output mistaken for routed discharge

- What is commonly concluded: an outlet time series produced by the model is a routed, attenuated hydrograph.
- Why it looks right: the series comes out of the routing model, so it is read as routed.
- Why it is wrong: the channel guide explicitly allows upstream runoff accumulation without routing. It is useful for separating volume production from transport, but is not evidence that timing or attenuation has been simulated.
- What observation exposes it: check the configured routing method before comparing timing or attenuation with observations.
- Scope and source: [M4](sources.md#m4).

## Reach discharges summed to get basin outflow

- What is commonly concluded: summing every reach's discharge gives total basin outflow.
- Why it looks right: every reach reports a discharge value, so summing them all reads like a complete accounting.
- Why it is wrong: do not sum every reach's discharge to obtain basin outflow: upstream water appears again in downstream reaches.
- What observation exposes it: not stated in the source record.
- Scope and source: not stated in the source record; the original statement carried no citation.

## Accumulated depth compared directly with an instantaneous discharge sample

- What is commonly concluded: two series describing the same reach can be compared timestep by timestep.
- Why it looks right: they refer to the same place, so a direct comparison looks natural.
- Why it is wrong: a depth accumulated over one interval cannot be compared directly with an instantaneous discharge sample.
- What observation exposes it: compare the same timestamp convention and temporal statistic.
- Scope and source: not stated in the source record; the original statement carried no citation.
