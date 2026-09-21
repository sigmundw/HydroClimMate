# Catalog validation summary

Run against one regional offline HRLDAS/Noah-MP run built from the pinned commit (paths and run identifiers withheld). Confirms or disagrees with source-derived catalog facts; does not judge scientific acceptability.

## outputs
- In catalog, not in this file's variable list: 81 (81 have a recorded gating condition that plausibly explains the absence; the rest have none recorded).
- In this file, not in the catalog: 0.
- Dimension order: 98 variables match the catalog's source-declared order reversed (the expected Fortran-nf90_def_var-vs-netCDF4-python relationship); 0 match literally; 0 disagree with both.
- Units attribute mismatches: 0.
- _FillValue/missing_value declared on 0 of 98 matched variables.
- Kind empirical sample (12 files, 85 variables checked, 35 tested against a curated kinds_overlay.yaml true_kind rather than the generated kind): 0 inconsistent.

## restart
- In catalog, not in this file's variable list: 117 (117 have a recorded gating condition that plausibly explains the absence; the rest have none recorded).
- In this file, not in the catalog: 0.
- Dimension order: 58 variables match the catalog's source-declared order reversed (the expected Fortran-nf90_def_var-vs-netCDF4-python relationship); 0 match literally; 0 disagree with both.
- Units attribute mismatches: 0.
- _FillValue/missing_value declared on 0 of 58 matched variables.

## forcing
- Forcing names matched in this LDASIN file: 8; not found: 11.

