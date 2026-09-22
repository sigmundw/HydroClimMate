# mizuRoute — version anchor

**Pinned to mizuRoute commit `28514dea3fd28a2f820c7ecaa9014f820c1bb220`, tag `v3.1.1` (2026-04-14).** Every `path:line` in this pack is relative to that tree and holds only at that commit. Scope: the standalone driver; the coupled build only where they differ.

## Checking a checkout

```
git -C <mizuroute> describe --tags   # expect v3.1.1
git -C <mizuroute> log --oneline -1  # expect 28514de
```

## Identifying the build that produced a run

Every history file carries three global attributes — `mizuRoute-version`, `gitBranch`, `gitHash` — written at file creation (`route/build/src/historyFile.f90:216-223`). They are not source constants: the standalone `Makefile` fills the macros `VERSION`, `BRANCH` and `HASH` **at compile time** with `git describe --tag`, `git describe --long --all --always` piped through `sed -e 's/heads\///'`, and `git rev-parse HEAD` (`route/build/Makefile:92-94,101`), which `init_data` copies into the globals only where defined (`route/build/src/standalone/model_setup.f90:75-83`).

They identify the *checkout the binary was built from*, not the code that ran. Built by the shipped `Makefile` outside a git working tree, `git` returns nothing and all three attributes are written **empty**, not `undefined`: every compiler arm passes the macros regardless (`route/build/Makefile:101`). The initialiser `undefined` (`route/build/src/globalData.f90:79-81`) survives only in a binary compiled without those `-D` flags. A build from a dirty tree reports the last tag. `gitHash` is the only unambiguous one; compare it with `28514dea3f...`.

Two further marks in a history file: the coordinates are `time`, `time_bounds`, `reachID` on `seg` and, where an HRU flux is written, `basinID` on `hru`; and the discharge names are `IRFroutedRunoff`, `KWTroutedRunoff`, `KWroutedRunoff`, `MCroutedRunoff` and `DWroutedRunoff`, unless `<outputNameOption> generic` collapsed them.

## What does not carry over to older releases

The pinned tree ships **no release notes and no migration list**. The code records one value changing meaning: the parser prints `WARNING: routOpt=0 is accumRunoff option now` whenever `<route_opt>` is exactly `0` (`route/build/src/read_control.f90:582`), so a `0` carried over from an older configuration does not mean what it did; the tracer output path is marked temporary, dated April 2025 (`:715-717`). Anything else about v1.x or v2.x is **not established** here and must be read in that version's own source.

## Void if the version differs

Every `path:line`; the control keys, defaults and validation rules; the routing digits; output names, units and the mean-versus-last-value rule; file naming and time stamps; the restart contract; and `catalogs/*.yaml`.

## How this pack was verified

Every statement is read in the pinned source; control-file statements are also checked against the two sample control files in `route/settings/` and tagged `source_read + sample`. **No mizuRoute data and no build exist here**, so nothing is graded as observed and no cost claimed.
