# Changelog

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
