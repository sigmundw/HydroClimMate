# mizuRoute: input contract and run checks

Scope: basic river routing using rolling `stable` guidance, excluding specialized reservoir,
water-management or coupled-driver recipes. No lab machine configuration is assumed.

## Establish the exchange contract

The input guide requires river-network and runoff information and conditionally a remapping
file. Variable and dimension names can be configured, so do not identify their semantics by
spelling alone. Runoff already expressed on network HRUs should not be remapped as if it
were a different grid. [M2](sources.md#m2)

The control file connects paths, time settings, input metadata, routing decisions and output
choices. Recover the actual control file and associated parameter information from the
project rather than copying a stable-doc example into an unknown release.
[M5](sources.md#m5)

Recommended preflight:

1. Identify the producer, included runoff components, units, interval definition and
   calendar. Establish whether data are depth or volume quantities before conversion.
2. Join source IDs, mapped HRUs and receiving reaches explicitly; do not rely on file order.
   Verify downstream connections and the intended outlet, including any excluded domain.
3. Inspect mapping coverage, duplicate contributors, missing values and the area convention.
   Use a constant field and integrated-volume check on a small mapping sample.
4. Check whether hillslope transport was already applied. Avoid repeating a delay or area
   multiplication merely because an option appears in an example control file.
5. Match restart state, network, methods and time with the intended continuation; inspect
   active jobs and output paths before submitting anything.

For the documented depth-based workflow, HRU area participates in converting runoff to
volume, followed by selected hillslope handling. See
[pitfalls](pitfalls.md#depth-to-discharge-conversion-applied-a-second-time) before repeating
that conversion. [M3](sources.md#m3)

Start with an authorized short interval and inspect completion, expected reach IDs, timing
and finite outputs. Separate file-read success, numerical routing success and validation of
the resulting hydrograph. Apply the [Run feature](../../run.md) budget/retry boundaries.
If an unrecognized interface expects different units or variables, inspect local code rather
than assuming this basic standalone contract also defines a coupled experiment.
