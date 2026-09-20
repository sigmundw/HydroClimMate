# Local model knowledge

Choose the model **and topic**; these files are not a reading sequence. Read a source
record only when checking attribution, version coverage or a missing detail. The
[core knowledge policy](../core.md#local-model-knowledge) applies offline and online.


| Model / aliases | Identity and mechanisms | Setup and run checks | Output interpretation | Looks right, is wrong | Provenance |
|---|---|---|---|---|---|
| HRLDAS / Noah-MP / NoahMP | [Overview](hrldas-noahmp/overview.md) | [Execution](hrldas-noahmp/execution.md) | [Outputs](hrldas-noahmp/outputs.md) | [Pitfalls](hrldas-noahmp/pitfalls.md) | [Sources](hrldas-noahmp/sources.md) |
| WRF-Urban / UCM / BEP / BEP+BEM | [Overview](wrf-urban/overview.md) | [Execution](wrf-urban/execution.md) | [Outputs](wrf-urban/outputs.md) | [Pitfalls](wrf-urban/pitfalls.md) | [Sources](wrf-urban/sources.md) |
| CTSM / CLM | [Overview](ctsm/overview.md) | [Execution](ctsm/execution.md) | [Outputs](ctsm/outputs.md) | [Pitfalls](ctsm/pitfalls.md) | [Sources](ctsm/sources.md) |
| RBM — UW-Hydro candidate; lab identity unconfirmed | [Overview](rbm/overview.md) | [Execution](rbm/execution.md) | [Outputs](rbm/outputs.md) | [Pitfalls](rbm/pitfalls.md) | [Sources](rbm/sources.md) |
| ISSM | [Overview](issm/overview.md) | [Execution](issm/execution.md) | [Outputs](issm/outputs.md) | [Pitfalls](issm/pitfalls.md) | [Sources](issm/sources.md) |
| VIC / Variable Infiltration Capacity | [Overview](vic/overview.md) | [Execution](vic/execution.md) | [Outputs](vic/outputs.md) | [Pitfalls](vic/pitfalls.md) | [Sources](vic/sources.md) |
| mizuRoute | [Overview](mizuroute/overview.md) | [Execution](mizuroute/execution.md) | [Outputs](mizuroute/outputs.md) | [Pitfalls](mizuroute/pitfalls.md) | [Sources](mizuroute/sources.md) |
| MODFLOW / MODFLOW 6 — groundwater flow focus | [Overview](modflow/overview.md) | [Execution](modflow/execution.md) | [Outputs](modflow/outputs.md) | [Pitfalls](modflow/pitfalls.md) | [Sources](modflow/sources.md) |

Understand usually needs overview; Run needs execution; Analyze needs outputs. Plan
selects the topic affecting the actual choice, not every file. Model comparisons may
require two overviews. A known output question can go directly to outputs. Read the
pitfalls file before accepting a result or an inference as final — not for every question —
when a conclusion rests on a paired comparison, a budget closure, an accumulated-vs-
instantaneous quantity, or any other "looks right" claim the pack already warns about.

Coverage is conceptual and task-oriented, not a complete parameter/API catalog. Exact
lab versions and settings are unknown. Separate model packs do not establish a working
coupling; verify the actual exchange contract before connecting models.

Packs also carry optional machine-readable declarations ([SCHEMA.md](SCHEMA.md)) that
`tools/hcm_check.py --pack` confronts with actual files — a declaration is not proof.

Source age and revalidation follow the [shared freshness policy](../core.md#source-freshness).
The repository checker reports review dates older than 180 days; its optional `--network`
check tests URL reachability only. Neither check automatically refreshes source records.

Scientific summaries are original paraphrases with local source IDs. Links to upstream
material do not relicense it under this repository's MIT license. Source records distinguish
retrieved material from navigation-only links and floating documentation from fixed releases.
