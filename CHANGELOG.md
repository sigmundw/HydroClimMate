# Changelog

## Unreleased

Model knowledge layer rebuild for one pack (`hrldas-noahmp`), plus a repository-wide format
change. Not yet measured against the earlier layer; see `references/models/SCHEMA.md` for what
changed and why.

- `hrldas-noahmp` is now a "generation 2" pack (`references/models/SCHEMA.md`): a one-page
  `card.md`, a `processes.md` question/switch/module/variable map, a `failures.md` list indexed
  by symptom (each entry: what is happening, how to confirm it, the remedy, its source), bounded
  `recipes.md` procedures that state their cost, and a `version.md` anchor -- all cited to a
  pinned source-tree commit pair or to real output, never from memory. Indexing failure knowledge
  by symptom, and stating a checkable data-interface contract, are ideas taken from KISS
  (arXiv 2605.17856v1); this pack's schemas, file names, field names and content are its own, not
  copied from that project.
- New `catalogs/` directory for that pack: output, restart, forcing, setup, namelist,
  physics-option, parameter and constant tables extracted mechanically from the pinned source by
  `tools/extract_pack.py`, each fact citing an exact source `file:line@commit` and an evidence
  grade (`source_read` / `observed_in_output` / `both`); `tools/validate_catalogs.py` confronts
  them with real output/restart/forcing files and upgrades evidence in place, deterministically.
  Query with `tools/hcm_lookup.py --pack hrldas-noahmp <name>` rather than reading a catalog file
  whole.
- Pack layers a person or agent reads are now YAML, not JSON, across all eight model packs (owner
  decision, for readability): the curated layers (`interface`, `switches`, `pitfalls`,
  `workflows`, `pack` manifest, `selftest`) and, for `hrldas-noahmp`, the generated catalogs.
  Only machine-only build artifacts (`index.json`, `catalogs/MANIFEST.json`) stay JSON. A strict,
  restricted YAML subset is used throughout, implemented in `tools/_miniyaml.py`, so every file
  also loads identically under PyYAML when it is available; `tools/selftest.py` checks this for
  every pack YAML file in the repository. `tools/build_index.py`, `hcm_check.py`, `hcm_lookup.py`
  and `evals/check_knowledge.py` read either format; a pack declares which one it uses (its
  "generation") in its manifest.
- The other seven packs are unchanged in content, marked as the older, thinner generation in
  `references/models/index.md`, and had their existing JSON layers mechanically converted to the
  same YAML subset (verified equal by loading both encodings).
- `references/models/index.md` and `core.md`'s local-model-knowledge paragraph now give a
  separate reading order for a generation-2 pack (card first, then a lookup tool query, then the
  process/failure/recipe files by need); the pack's own former five-topic files
  (`overview.md`/`outputs.md`/`execution.md`/`pitfalls.md`) are kept only as redirects so older
  links and the pitfalls id namespace still resolve.
- `evals/check_knowledge.py` extended for the new generation: required files and size caps,
  source-citation and generated-catalog checks when `--source-root` is given, and the existing
  structured-layer/link/anchor checks generalized to load either format.

## 0.9

Structural release. The effect of these changes has not been measured yet, and the machine-readable
layers are deliberately sparse: they restate only what each pack already said, so most tool output for
most variables reads "NO DECLARATION". Filling them from real model source and output is later work.

- Review added as a fifth feature (`references/review.md`): when an independent check is proportionate, how to
  call a fresh agent or session, what a reviewer may and may not receive, per-claim three-state output, no
  authority to modify, re-run or recover, and final acceptance by the research owner.
- `tools/` added (optional; numpy and netCDF4 needed to read files): `hcm_check.py` with `paired-response`,
  `accumulation-and-fill`, `describe`, `lookup`, `pack-info` and `pitfall-scan`; `hcm_review_packet.py`, which
  assembles what a reviewer may see and refuses executor narrative; `build_index.py`; self-tests on synthetic
  data. Checks print observations first, then VERIFIED / VIOLATED / UNVERIFIED; without project thresholds the
  verdict is UNVERIFIED and the numbers are still shown.
- `templates/EXPERIMENT.md`: a project-owned experiment record (claim, what varies and what must stay identical,
  expected response, what would count against it, acceptance and who set it).
- Core and feature references: the four questions (what was established, how it was checked, what is the owner's
  to decide, does this need Review) and a uniform closing block in Understand, Plan, Run and Analyze.
- All eight model packs: five-topic layout with a new `pitfalls.md` built only from cautions each pack already
  contained, and machine-readable layers (`pack.json`, `interface.json`, `switches.json`, `pitfalls.json`,
  `workflows.json`, generated `index.json`, `selftest.json`) whose every fact carries source, scope, basis and
  the sentence it restates. No new model claim was added; two independent audits removed the ones that crept in.
  Packs carry no acceptance thresholds. See `references/models/SCHEMA.md`.
- Evaluation assets: trigger fixtures that restated routing-table prompts or named non-existent paths were
  rewritten (originals kept in `previous_query`); `evals/README.md` gained a dated correction of the earlier
  account of why trigger measurement had produced no valid result; `evals/check_knowledge.py` validates the new
  layers and that the committed index equals a fresh build.
- No new model packs, no installation, no model execution.

## 0.8

Changes drawn from the first evaluation of the four features on a real single-model case. Their effect
has not yet been measured; a before/after comparison is planned for the next stage.

- HRLDAS/Noah-MP outputs: added a version-scoped note that enabling urban physics reassigns the Noah-MP
  column on urban cells to the table's natural class, that the urban routine tile-weights only surface
  energy and radiative fields, and that snow state is never passed to it; added source record H6 and a
  cross-reference from the WRF-Urban pack.
- HRLDAS/Noah-MP outputs: noted that a layer-mass identity may not hold in a zero-layer snow state, and that
  water-body cells can carry a large negative value with no declared fill attribute, so masking must be explicit.
- Run: after enabling a physics option, verify that the intended quantity changed for the intended reason
  rather than concluding from the absence of errors.
- Plan: a recommendation names its deciding criterion and what evidence would reverse it; value, budget and
  risk judgements are handed back to the research owner.
- Core and SKILL.md: read the applicable model topic before tracing source code; verifying an existing input
  archive before a run is Run preflight.
- No new model packs, no change to the four-topic layout, no installation or model execution.

## 0.7

- Added source-attributed VIC5 and mizuRoute offline packs using the existing four-topic layout.
- Covered driver distinctions, runoff-to-routing contracts, remapping and avoiding duplicate area conversion/routing.
- Preserved v0.6 vocabulary and near-miss evaluations; added new model-specific scenarios.
- Made model counts/version checks extensible and rejected future source-review dates.
- Clarified that stale sources do not disable offline use and reachable URLs do not establish content validity.
- Kept RBM lab-identity uncertainty consistent between the index and its existing source record.

### 0.7 small additions

- Added MODFLOW 6 groundwater-flow knowledge, with explicit legacy-version and transport limits.
- Centralized stale-source behavior: review reminder, offline continuation, claim-level verification and honest Checked-date updates.
- Made SKILL.md the sole shared entrypoint; reduced package AGENTS.md to a compatibility pointer. Project instruction templates remain.
- Kept version 0.7 and existing project records; no installation or model execution.

## 0.6

- Added five offline model knowledge packs, topic routing, source records and coverage limits.
- Included ISSM ice flow/mass change and targeted model learning without a project.
- Documented native Codex skills and corrected submodule/package paths.
- Allowed justified cross-feature reads; annotated historical probe claims without rerunning them.
- Added separate knowledge cases and offline evaluation protocol; static checks are not agent pass rates.
- Existing project records remain valid; choose one entry path and retain project-specific settings.

### 0.6 follow-up fixes

- **Restored trigger vocabulary lost in the description rewrite.** Adding RBM and ISSM had
  shortened the description from 791 to 565 characters and squeezed out eight domain terms,
  including `basin`, `catchment`, `netCDF`, `calibration`, `streamflow`, `water balance`,
  `area weighting` and `time semantics`. Two of those — basin means and calibration — are
  contrasting prompts in the routing table itself. Now 798 characters against a 1,536 cap.
- **Rewrote four ISSM eval prompts that named their own answer.** "Discuss an ISSM mesh
  refinement experiment; do not run it" telegraphs Plan; "Compute an area mean..." telegraphs
  Analyze. They are now in researcher register, without the routing verb. A prompt that
  states its expected feature inflates routing accuracy the same way a prompt copied from
  the routing table does.
- **Added the gray zone v0.6 created.** Supporting offline model questions made the operative
  rule "textbook question about a documented model fires; otherwise it does not". Four cases
  now sit on that line — a grounding-line concept question and BEP vs BEM (fire), generic
  spin-up and Penman-Monteith with no model named (do not fire).
- **Restored negative coverage.** Negatives had fallen to 9 while scope broadened, leaving
  15:9. Five near-misses inside the new scope were added — installing ISSM, a CTSM literature
  search, MATLAB-to-Python translation, an HPC admin email, generic type hints — giving 33
  cases at 17:16.
- **`check_knowledge.py` now detects link rot and staleness.** It reports each pack's
  `Checked:` age against a 180-day limit, and `--network` verifies all 36 cited URLs.
  The network mode prefers `curl` and probes a control URL first, because a bare macOS
  Python has no CA bundle: without that guard the first run reported *36 of 36 cited URLs
  did not resolve*, which was a broken TLS transport, not rot. A uniform total failure is
  now reported as UNMEASURED.
- **Fixed `.gitignore`.** It had been deleted from the index and recreated untracked as
  `.DS_store`, which matches only because macOS sets `core.ignorecase=true`; on a Linux HPC
  node it would not match `.DS_Store`, and being untracked no colleague received it.

## 0.5

Installable for the first time, and usable from both Claude Code and Codex.

**Added**

- **Two entry points over shared references.** `SKILL.md` (Claude Code) and `AGENTS.md`
  (Codex and other AGENTS.md tools) carry the same routing table and point at the same
  `references/`. The routing table is duplicated between them by design and marked as such;
  everything else lives once.
- **`references/core.md`** — the cross-feature rules lifted out of `SKILL.md`: context checks,
  the shared five-field checklist, project-record policy and stopping rules. Both entry points
  are now ~30 lines.
- **Install instructions**, which the project had never had. 0.1 through 0.4 were revised four
  times without ever being installed or run.
- **"What the researcher does"** in `README.md`, restored from 0.2 and lost in the 0.4 rewrite.
  It lives in the repo README rather than the workflow files because it addresses the human and
  should not consume agent context.
- **Trial log** in `README.md`, restored from 0.1.
- **LICENSE** (MIT) and a version marker in the body of both entry points. `SKILL.md`
  frontmatter has no `version` field, so it cannot go there.

**Changed**

- Renamed throughout to **HydroClimMate**, matching the repository. The skill is
  `hydroclimmate`; ACT Hydro Lab is named as author rather than stamped on every template.
- Package directory `act-hydro-lab-starter/` → `hydroclimmate/`; `README.md` and
  `CHANGELOG.md` moved to the repository root so the package can be symlinked into
  `~/.claude/skills/` without them.
- `templates/AGENTS.md` → `templates/PROJECT_AGENTS.md`, parallel to the existing
  `PROJECT_README.md`, so it is not confused with the workflow-level `AGENTS.md`.
- **`PROJECT_AGENTS.md` cut from 52 lines to project-specific boundaries only.** It had
  restated eight rules the workflow already carried — Ran/Verified/Supported, equal-area
  weighting, clean-kernel notebooks, escalation, evidence capture, sample-is-not-full-run,
  decision ownership, do-not-rerun-costly-work. It now holds entry points, paths, budgets,
  authorization scope, owner, and project-specific scientific constraints, plus the pointer
  line that carries the workflow into Codex.
- **`description` rewritten** from 329 to 791 characters (cap is 1,536). It contained no
  domain noun a hydrologist would type; it now names runoff, streamflow, basin and catchment
  means, water balance, netCDF and forcing data, spin-up, restart, calibration, grid and area
  weighting, HPC jobs, and the models VIC, mizuRoute, WRF-urban, HRLDAS/Noah-MP and CTSM.
- Feature files point at `references/core.md` rather than `SKILL.md`, so they read correctly
  under both tools.

- Migration: existing projects keep their records. Update the template path if you referenced
  `templates/AGENTS.md`, and move any universal rules out of your project `AGENTS.md`.

## 0.4

- Packaged one skill with four on-demand features: Understand, Plan, Run and Analyze.
- Added explicit routing, exclusions, shared context checks and proportional stopping rules.
- Aligned discussion and execution around the same five-field checklist in TASK.md.
- Integrated existing templates with conditional updates and decision ownership across features.
- Moved detailed spatial weighting guidance into Analyze; retained grid sanity checks in Run.
- Migration: keep existing project records and template paths; merge changed rules and task fields. No automatic installation or project initialization.

## 0.3

- Added grid/mesh identification and area-weighting rules, including no extra latitude weighting for confirmed equal-area cells.

- Reduced the adoption guide and introduced document size budgets and single-source records.
- Made handovers, decision logs and task records conditional; removed duplicate template fields.
- Replaced automatic restarts and failure-count escalation with evidence, scope and budget criteria.
- Added compute/retry budgets and a stop condition after acceptance; prefer logs to costly reruns.
- Kept hydrological checks, result provenance and independent validation for consequential work.
- Migration: retain existing records; update active rules and link existing commands. No file renames required.

## 0.2

*Section numbers below refer to the pre-0.4 README, which was a single numbered
document. That structure no longer exists; the content moved into SKILL.md and
references/ in 0.4, and into the two entry points in 0.5.*

Documentation only. No change to the four-document structure, and nothing in 0.1 was
removed — a project already running 0.1 can adopt this by merging.

**Added**

- **§0, what the harness assumes.** 0.1 was silent on two preconditions it depended on:
  that the project is under version control, and that raw data is protected by filesystem
  permissions rather than by prose. Section 5's provenance rules cannot be satisfied
  without the first, and the read-only rules have no floor without the second.
- **§6, sessions and the researcher's role.** 0.1 addressed the agent almost entirely.
  Added guidance on session length and when to restart from the handover, and an explicit
  list of what the researcher has to do: read the diff rather than the summary, reproduce
  one number by hand, ask which command produced a result, own the scientific choices.
- **Ran / Verified / Supported.** 0.1 drew this distinction in prose in §3 but gave it no
  vocabulary, so the distinction could not be carried into handovers and task records.
  Now defined once in §3 and referenced from `AGENTS.md`, `HANDOVER.md`, and `TASK.md`.
- **`AGENTS.md`: a "Stop and ask when" section.** Escalation triggers existed only inside
  the optional `TASK.md`, so they were absent from the rules that load every session.
- **`AGENTS.md`: a "Reporting" section**, covering what to name when reporting a check and
  the acceptability of answering "unverified".
- **A fourth prompt template**, for writing the handover at the end of a session. §3 lists
  handover as a workflow stage; §8 had no prompt for it.
- **A default path for task records**, `tasks/YYYY-MM-DD-short-name.md`. 0.1 referred to
  "the project's existing task directory", which most projects do not have.

**Changed**

- `templates/README.md` renamed to `templates/PROJECT_README.md`. As named, it read as
  documentation *for* the templates directory rather than a template for the project's own
  README, and it collided with this starter's README in conversation.
- `AGENTS.md`: the project-specific commands and boundaries moved from the bottom of the
  file to the top. It is the section that must be filled in per project and the one an
  agent most needs early; at the bottom it received the least weight and was most often
  left as placeholders.
- `HANDOVER.md`: entries under "Completed and verified" must now name the check that was
  run. Code that ran but whose output nobody checked belongs under "In progress or
  unverified".
- §9 now asks for a running log of harness failures during the trial, rather than a
  retrospective judgment at the end of it.

## 0.1

Initial version for lab trials.
