# CTSM sources

Checked: 2026-09-16. Lab checkout/compset: unknown. The main site is explicitly labeled latest development code; a CLM5.0 selector exists. No developer option is asserted to be available in a historical release. No CTSM case was run.

## C1

[CTSM documentation](https://escomp.github.io/CTSM/): retrieved; version warning and guide organization. [Repository](https://github.com/ESCOMP/CTSM) checked for model identity.

## C2

[Technical-note introduction](https://escomp.github.io/CTSM/tech_note/Introduction/CLM50_Tech_Note_Introduction.html): retrieved; CLM5.0 description and biogeophysical/biogeochemical processes. The page is hosted under the rolling site: its title does not pin every linked chapter to a release.

## C3

[Surface characterization](https://escomp.github.io/CTSM/tech_note/Ecosystem/CLM50_Tech_Note_Ecosystem.html): retrieved; section 2.2.1, subgrid hierarchy and fractional aggregation. Numerical counts of classes/layers were not copied as defaults.

## C4

[Choosing a compset](https://escomp.github.io/CTSM/users_guide/setting-up-and-running-a-case/choosing-a-compset.html): retrieved; data-atmosphere, active-atmosphere and coupled alternatives. Compset names and availability require the actual case tools/revision.

## C5

[Customizing the namelist](https://escomp.github.io/CTSM/users_guide/setting-up-and-running-a-case/customizing-the-clm-namelist.html): retrieved; user versus generated namelist, history requests and examples. Example paths and development defaults are deliberately not adopted.

## C6

[History fields, non-FATES](https://escomp.github.io/CTSM/users_guide/setting-up-and-running-a-case/history_fields_nofates.html): retrieved; variable meanings and units as a reference route. Not every field was audited; FATES-specific outputs require their separate list and matching code.

## Gaps

Complete namelist catalogs, machine ports, exact restart/branch recipes, FATES internals, and laboratory convergence criteria remain outside this pack. Linked documentation is upstream material, not redistributed under this repository's license.
