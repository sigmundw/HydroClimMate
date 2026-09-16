# Analyze hydrological data

Use for processing, evaluating, plotting and diagnosing observations or model outputs.
Read [the shared checklist](../SKILL.md#shared-plan-to-execution-checklist) as the input
contract; a clear request can supply it directly without a separate planning stage.

## Establish the quantity and evidence

- Identify the requested mean, total, flux, change or metric and the spatial/temporal support it represents.
- Start with metadata and a small sample: source/version, variables, units, dimensions, missing values and masks.
- Inspect the existing analysis entry point and adopted definitions; reuse scripts or notebooks rather than creating a parallel workflow.
- Resolve only missing choices that affect this calculation. Use [Plan](plan.md) for a new scientific choice or expanded resource/irreversibility boundary.

## Identify grid or mesh before spatial processing

Inspect coordinate dimensions, CRS/grid mapping, cell bounds or mesh connectivity, cell
versus node values, and supplied cell areas (such as CF cell_measures). Curvilinear coordinates
or fixed projected spacing do not by themselves establish equal ground area.

For area means of cell-based fields:

- Regular degree-spaced latitude–longitude grids: use supplied cell areas or areas from bounds. cos(latitude) is an approximation only for a suitable regular equal-angle grid, not a general weighting rule.
- Confirmed equal-area cells: use equal area weights; do not add latitude/longitude or cosine-latitude weighting. Basin overlap and valid coverage can still differ.
- Other curvilinear grids or meshes: use supplied areas or areas derived from validated cell geometry; do not assume equal area or apply latitude-only weights.
- Node-based values need a documented integration rule; do not treat nodes as equal-area cells.

Check area units, positivity and alignment with the data. Use effective area (cell area ×
included fraction), excluding missing values consistently from numerator and denominator.
Report valid coverage; a zero effective denominator is missing, not zero. Distinguish an
area mean from an integral or a sum of quantities already expressed as cell totals.
Unresolved geometry requires investigation before weighting. See [CF cell measures](https://cfconventions.org/Data/cf-conventions/cf-conventions-1.3/build/ch07s02.html).

For remapping, identify which physical quantity must be preserved and verify coordinate,
mask and coverage alignment rather than selecting a method solely because it runs.

## Time, evaluation and scientific checks

- Check represented intervals, time alignment, time steps, calendars, leap days and time zones where relevant.
- Integrate interval-mean rates over the represented duration; cumulative counters require explicit differencing and reset rules. Variable names alone do not establish either.
- Preserve storage/flux distinctions, signs and units. For water balance, name control volume, time window, included terms and tolerance; missing terms may prevent full closure assessment.
- Verify aggregation order, calibration/validation splits, missing-data handling and metric definitions; avoid temporal/spatial information leakage.
- Set acceptance tolerances from units, precision, reference uncertainty or research needs before evaluating results.
- Use an independent case, calculation or appropriate physical/numerical property. Plausible ranges and agreement with old results alone do not establish correctness.

## Diagnose, deliver and stop

For “why is simulated runoff too high?”, trace inputs, units, time matching, masks,
aggregation and model behavior. Separate facts from hypotheses and allow the surprising
result to be valid. Borrow [Understand](understand.md) for a code question; use Plan only
when evidence requires choosing a new method or experiment. Do not silently tune or rerun.

Produce the requested reproducible analysis and figures with actual data, units, labels
and provenance. Notebooks must run in order from a clean kernel. Preserve original outputs;
keep diagnostic artifacts separate. Capture commands, code/configuration state, input
versions, environment and checks in existing output records, or a small run-info.md.

Report execution, verified properties and scientific support separately, including failed
checks and limits. Stop after the requested outputs and relevant checks are complete.
Update only affected project facts and existing task state; apply the shared decision and
handover policy. Consequential results require independent validation/review, not automatic
review of every plot or routine calculation.
