# Local model knowledge

Choose the model **and topic**; these files are not a reading sequence. Read a source
record only when checking attribution, version coverage or a missing detail. The
[core knowledge policy](../core.md#local-model-knowledge) applies offline and online.


| Model / aliases                             | Identity and mechanisms               | Setup and run checks                    | Output interpretation               | Provenance                          |
| --------------------------------------------- | --------------------------------------- | ----------------------------------------- | ------------------------------------- | ------------------------------------- |
| HRLDAS / Noah-MP / NoahMP                   | [Overview](hrldas-noahmp/overview.md) | [Execution](hrldas-noahmp/execution.md) | [Outputs](hrldas-noahmp/outputs.md) | [Sources](hrldas-noahmp/sources.md) |
| WRF-Urban / UCM / BEP / BEP+BEM             | [Overview](wrf-urban/overview.md)     | [Execution](wrf-urban/execution.md)     | [Outputs](wrf-urban/outputs.md)     | [Sources](wrf-urban/sources.md)     |
| CTSM / CLM                                  | [Overview](ctsm/overview.md)          | [Execution](ctsm/execution.md)          | [Outputs](ctsm/outputs.md)          | [Sources](ctsm/sources.md)          |
| RBM — UW-Hydro                             | [Overview](rbm/overview.md)           | [Execution](rbm/execution.md)           | [Outputs](rbm/outputs.md)           | [Sources](rbm/sources.md)           |
| ISSM / Ice-sheet and Sea-level System Model | [Overview](issm/overview.md)          | [Execution](issm/execution.md)          | [Outputs](issm/outputs.md)          | [Sources](issm/sources.md)          |

Understand usually needs overview; Run needs execution; Analyze needs outputs. Plan
selects the topic affecting the actual choice, not every file. Model comparisons may
require two overviews. A known output question can go directly to outputs.

Coverage is conceptual and task-oriented, not a complete parameter/API catalog. Exact
lab versions and settings are unknown. VIC and mizuRoute retain workflow support without
dedicated packs; do not imply that a linked coupling description documents their full use.

Each pack records a `Checked:` date and cites floating branch URLs, which move without
notice. Re-check a pack when its date is over 180 days old, when a cited upstream release
changes, or before relying on it for a consequential result; `evals/check_knowledge.py`
reports packs past that limit, and `--network` confirms the cited URLs still resolve.
A re-check is a deliberate source-checked update, not an automatic rewrite during a task.

Scientific summaries are original paraphrases with local source IDs. Links to upstream
material do not relicense it under this repository's MIT license. Source records distinguish
retrieved material from navigation-only links and floating documentation from fixed releases.
