# Changelog

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
