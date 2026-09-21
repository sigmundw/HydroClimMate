# HRLDAS / Noah-MP: execution — moved

This file is a redirect stub. Namelist items, their allowed values and their meanings are in
`catalogs/namelist.yaml` and `catalogs/physics_options.yaml` (query with
`tools/hcm_lookup.py --pack hrldas-noahmp <NAME>`); what each option actually changes is
in **[processes.md](processes.md)**; version checks are in **[version.md](version.md)**.

## Prepare a consistent experiment

Keep the host and submodule revisions together and check them before diagnosing anything
([version.md](version.md)). `NOAH_TIMESTEP` must evenly divide both `FORCING_TIMESTEP` and
`OUTPUT_TIMESTEP`. Exactly one of `KDAY` / `KHOUR` sets the length. `SPINUP_LOOPS > 0` writes
files with a `.loop` suffix that must not be mixed into an analysis series. Several options are
silently inert unless a gate is open — see
[failures.md: A switch was turned on and the output is identical](failures.md#a-switch-was-turned-on-and-the-output-is-identical).

## Minimal preflight and continuation

1. Confirm the commit pair, or the five header facts in [version.md](version.md).
2. Confirm the forcing variable names, units and time convention against
   [card.md](card.md) — precipitation forcing is mm/s, humidity is specific.
3. Record the adopted physics options; check each one's gate, not just the namelist line.
4. State whether the run starts from prescribed fields, spin-up loops or a restart, and choose
   an equilibration diagnostic — a number of loops is not proof of equilibrium.
5. Inspect the first output records for time stamps, `-9999` fields and fill values before
   trusting anything ([failures.md](failures.md)).
6. Before continuation, verify restart state time, configuration, forcing continuity and
   accumulator continuity — not the restart file name
   ([failures.md](failures.md#a-restart-file-exists-so-the-run-restarted-successfully)).

Execution authority, queues and submission boundaries stay in the [Run feature](../../run.md);
nothing here authorizes a job.
