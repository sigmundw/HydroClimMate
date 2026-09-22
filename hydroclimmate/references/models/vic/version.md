# VIC — version anchor

**Pinned to VIC commit `14a371a8`, tag `5.1.0` (2021-12-14), with the `samples/data` submodule at `3f2dcb4`.** Every `path:line` in this pack is relative to that tree and holds only at that commit. Scope: the classic and image drivers.

## Checking a checkout

```
git -C <vic> describe --tags      # expect 5.1.0
git -C <vic> log --oneline -1     # expect 14a371a8
git -C <vic> submodule status     # expect 3f2dcb4... samples/data
```
The tag commit **changes no file**: 5.1.0 and its parent have identical source.

## Identifying the VIC that produced a run

`vic/drivers/shared_all/include/vic_version.h:13-19` defines the version strings `5.0.1 February 1, 2017` and `5.0.1` only as `#ifndef` fallbacks, and **neither driver Makefile defines either macro** (`vic/drivers/classic/Makefile:49-53`, `vic/drivers/image/Makefile:70-75`). So a build of *this* commit reports **5.0.1** in all three places a user looks: `-v` on either executable (`vic/drivers/shared_all/src/cmd_proc.c:97-101`), the image attribute `VIC_Model_Version` (`vic/drivers/shared_image/src/vic_init_output.c:637`) and the classic header line `# MODEL_VERSION:` (`vic/drivers/classic/src/write_header.c:273-276`).

The only string that identifies the real code is the git description compiled in as `GIT_VERSION`, from `git describe --abbrev=4 --dirty --always --tags` — printed by `-v` and written as `VIC_GIT_VERSION` (`vic_init_output.c:638`). It is the literal `unset` when the build was not made inside a git checkout (`vic_version.h:21-23`); a `-dirty` suffix means a modified tree.

Other marks. Image history carries fixed global attributes — `source = "VIC Image Driver"`, `VIC_Driver = "Image"`, `Conventions = "CF-1.6"` and a `history` naming the build user and host (`vic_init_output.c:606-641`). A classic ASCII file opens with `# SIMULATION:`, `# MODEL_VERSION:`, then a tab-separated date-plus-name row (`write_header.c:273-309`).

## What this pack does not carry over to VIC 4.x

A VIC 4 global parameter file cannot run here: of nineteen VIC 4 keys the classic parser rejects, eighteen are fatal unconditionally and `ARC_SOIL` only when its value is `TRUE`, each with a message naming the replacement (`vic/drivers/classic/src/get_global_param.c:568-674`; the full list is in the catalogs under `removed_since_vic4`). The release notes record that the forcing-disaggregation documentation was removed for 5.1.0 and that the version check changed from `vicNl -v` to `vic_{classic,image}.exe -v` (`docs/Development/ReleaseNotes.md:13-15,31-35`).

## How this pack was verified, and what is void elsewhere

Every statement is read in the pinned source; input-format statements are additionally confirmed against the VIC sample inputs (Stehekin, both drivers). **No VIC output exists here**, so nothing is graded as observed and no runtime cost is measured. Void at any other commit: every `path:line`; option names, values and validation rules; output names, units and aggregation types; file naming and headers; and all of `catalogs/*.yaml`.
