# MODFLOW 6: heads, flows and water budgets

Scope: GWF interpretation. Units, discretization, active packages and save settings must
be established from the actual simulation; no universal binary-file parser is supplied.

## Head is not stored-water volume

Hydraulic head is a potential expressed as a length. Multiplying head by cell area does
not generally give groundwater storage. Storage response depends on the appropriate
confined/convertible formulation and storage properties; specific yield and specific
storage have different roles. Use the storage budget and model definitions before
interpreting head changes as water gain or loss. [G3](sources.md#g3)

For a deliberately simplified unconfined illustration with constant specific yield,
uniform water-table rise and no elastic contribution, released/added volume can be
estimated as `Sy * area * delta_head`. For Sy=0.2, area=1000 m2 and rise=1 m, that is
200 m3. This is a conditional dimensional example, not a substitute for a MODFLOW budget.

## Establish grid and saved output

Use row/column widths for structured cell footprints, vertex polygons for DISV geometry,
or the supplied areas/connectivity for DISU. Active and pass-through status affect which
cells participate in the solution. Do not apply latitude weights to a confirmed equal-area
model grid or count inactive/dry output sentinels as valid head observations.
[G4](sources.md#g4)

Output Control selects whether and when head and budget information is saved or printed.
The absence of a saved budget record is not proof of zero exchange. Preserve the output
requests and saved-time mapping with the analysis. [G8](sources.md#g8)

## Recommended interpretation checks

- Distinguish boundary/package fluxes from internal cell-to-cell exchanges. Summing all
  exchanges as external inflow double-counts internal transfers; define a control volume.
- Establish whether a budget item is a volume rate or cumulative volume before integrating.
  Compare storage change and boundary terms over the same period, with consistent signs.
- Match observations to datum, layer/screen interval and sampling time. A grid-wide average
  head need not represent a particular well's measurement.
- Examine local residuals and physical plausibility as well as global budget discrepancy.
  A small discrepancy demonstrates numerical balance, not correct recharge or boundaries.

Use the [shared analysis checks](../../analyze.md) for missing values and spatial support.
No arbitrary universal budget-error threshold or groundwater calibration target is adopted.
