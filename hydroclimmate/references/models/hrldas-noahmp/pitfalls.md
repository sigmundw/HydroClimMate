# HRLDAS / Noah-MP: pitfalls — moved

This file is a redirect stub. Failure knowledge for this pack now lives in
**[failures.md](failures.md)**, indexed by symptom, with every entry re-verified against the
pinned source tree and, where possible, against real output ([sources.md](sources.md), `L0`-`L6`).
The three headings below are kept so existing links and structured-layer anchors resolve.

## Paired urban on/off snow difference attributed to canopy physics

Moved, and **corrected**, to
[failures.md: A paired urban on/off run differs in snow, soil or radiation](failures.md#a-paired-urban-onoff-run-differs-in-snow-soil-or-radiation).
Corrections against the earlier text: `EMISS` is **not** tile-weighted in the single-layer
(`SF_URBAN_PHYSICS = 1`) path, `UST` **is**, the weighted set is exactly eight fields, and the
urban-fraction table fallback is now stated. See also
[failures.md: Urban physics is on but nothing changes](failures.md#urban-physics-is-on-but-nothing-changes)
and the urban section of [processes.md](processes.md).

## Snow-water-equivalent identity and unmasked fill values

Split and re-verified into
[failures.md: Snow water equivalent does not equal the sum of the snow layers](failures.md#snow-water-equivalent-does-not-equal-the-sum-of-the-snow-layers)
(now with the 0.025 m layering threshold from source and counts from real output) and
[failures.md: Everything over water is a huge negative number](failures.md#everything-over-water-is-a-huge-negative-number-or-the-mean-is-nonsense)
(now with the reason — `missing_value` is a **global** attribute only — and with the integer
and 2-D-restart writers that apply no mask at all).

## Existing restart filename assumed to prove a successful restart

Moved to
[failures.md: A restart file exists, so the run "restarted successfully"](failures.md#a-restart-file-exists-so-the-run-restarted-successfully),
now with the namelist and driver lines that govern when restart files are written, and with
the concrete checks to run instead. See also
[failures.md: A restart file's variables are not where you expect](failures.md#a-restart-files-variables-are-not-where-you-expect).
