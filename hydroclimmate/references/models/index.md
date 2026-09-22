# Local model knowledge

Choose the model **and topic**; these files are not a reading sequence. Read a source record only when checking attribution, version coverage or a missing detail. The [core knowledge policy](../core.md#local-model-knowledge) applies offline and online.

Every pack declares a `depth` in its `pack.yaml` ([SCHEMA.md](SCHEMA.md)): **reference** (source-extracted catalogs, line-cited against a pinned checkout, and cross-checked against real output where any exists) or **outline** (orientation from public documentation, not source-verified — confirm against your own checkout before relying on a version-sensitive detail).

| Model / aliases | Depth | Identity and mechanisms | Setup and run checks | Output interpretation | Looks right, is wrong | Provenance |
|---|---|---|---|---|---|---|
| HRLDAS/Noah-MP | reference | [Card](hrldas-noahmp/card.md), [Processes](hrldas-noahmp/processes.md) | [Recipes](hrldas-noahmp/recipes.md) | `tools/hcm_lookup.py --pack hrldas-noahmp <NAME>` | [Failures](hrldas-noahmp/failures.md) | [Sources](hrldas-noahmp/sources.md), [Version](hrldas-noahmp/version.md) |
| WRF-Urban / UCM / BEP / BEP+BEM | outline | [Overview](wrf-urban/overview.md) | [Execution](wrf-urban/execution.md) | [Outputs](wrf-urban/outputs.md) | [Pitfalls](wrf-urban/pitfalls.md) | [Sources](wrf-urban/sources.md) |
| CTSM / CLM | outline | [Overview](ctsm/overview.md) | [Execution](ctsm/execution.md) | [Outputs](ctsm/outputs.md) | [Pitfalls](ctsm/pitfalls.md) | [Sources](ctsm/sources.md) |
| RBM — UW-Hydro candidate; lab identity unconfirmed | outline | [Overview](rbm/overview.md) | [Execution](rbm/execution.md) | [Outputs](rbm/outputs.md) | [Pitfalls](rbm/pitfalls.md) | [Sources](rbm/sources.md) |
| ISSM | outline | [Overview](issm/overview.md) | [Execution](issm/execution.md) | [Outputs](issm/outputs.md) | [Pitfalls](issm/pitfalls.md) | [Sources](issm/sources.md) |
| VIC / Variable Infiltration Capacity | reference | [Card](vic/card.md), [Processes](vic/processes.md) | [Recipes](vic/recipes.md) | `tools/hcm_lookup.py --pack vic <NAME>` | [Failures](vic/failures.md) | [Sources](vic/sources.md), [Version](vic/version.md) |
| mizuRoute | reference | [Card](mizuroute/card.md), [Processes](mizuroute/processes.md) | [Recipes](mizuroute/recipes.md) | `tools/hcm_lookup.py --pack mizuroute <NAME>` | [Failures](mizuroute/failures.md) | [Sources](mizuroute/sources.md), [Version](mizuroute/version.md) |
| MODFLOW / MODFLOW 6 — groundwater flow focus | outline | [Overview](modflow/overview.md) | [Execution](modflow/execution.md) | [Outputs](modflow/outputs.md) | [Pitfalls](modflow/pitfalls.md) | [Sources](modflow/sources.md) |

**A `depth: reference` pack** (HRLDAS/Noah-MP, VIC, mizuRoute): read that pack's `card.md` only, look up any variable/option/parameter/constant with `tools/hcm_lookup.py --pack <pack> <NAME>`, then open its `failures.md` by symptom, `processes.md` by process, or `recipes.md` by bounded task. Version pin: its `version.md`. Never read a `catalogs/*.yaml` file wholesale. Each reference pack also has a `README.md` written for people, not for this reading path.

**A `depth: outline` pack** (the other five): Understand usually needs overview; Run needs execution; Analyze needs outputs; read pitfalls before finalizing a result the pack already warns can look right and be wrong. Coverage is conceptual and task-oriented, not a complete parameter/API catalog; exact lab versions and settings are unknown; separate model packs do not establish a working coupling, so verify the actual exchange contract before connecting models.

Scientific summaries are original paraphrases with local source IDs. Links to upstream material do not relicense it under this repository's MIT license. Source records distinguish retrieved material from navigation-only links and floating documentation from fixed releases.
