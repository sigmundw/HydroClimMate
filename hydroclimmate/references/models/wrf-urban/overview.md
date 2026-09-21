# WRF-Urban: model and scheme identity

Scope: urban physics within WRF-ARW, using the official rolling Users' Guide checked 2026-09-16. Exact WRF/WPS release, land-surface scheme and urban option must be identified for a real experiment; this is not a lab configuration.

## Urban physics is a selection, not a separate fixed model

The guide describes single-layer UCM, multilayer BEP, and BEP with building-energy modeling. Building-energy treatment adds processes such as heating and air-conditioning to the urban representation. Availability and compatibility with land-surface and boundary-layer schemes must be checked for the target release. The presence of urban land-use cells alone does not identify which explicit urban scheme is active. [W1](sources.md#w1)

The wider WRF workflow still matters: geographic and meteorological inputs are prepared with WPS before initialization and atmospheric integration. A change to urban properties is embedded in this atmospheric experiment, including its domain, forcing and other physics. [W2](sources.md#w2), [W3](sources.md#w3)

## Questions to settle before interpreting an experiment

- Is this an urban-parameter sensitivity, a land-cover change, a forcing comparison or a physics-scheme comparison? Changing several at once makes attribution harder.
- Are the geographic categories and urban fractions consistent with the chosen urban representation? Category codes are not interchangeable between datasets.
- Is the claimed response a grid-cell mean, an urban-only diagnostic, near-surface air temperature or a surface temperature? These answer different physical questions.
- Are comparisons aligned in time, domain and observation support? Keep a baseline fixed while changing the intended factor.

These are recommended experimental checks, not a universal urban configuration. The official physics chapter also documents urban parameter tables and local-climate-zone support, but this pack does not select table values or a compatibility combination. [W1](sources.md#w1)

Use [execution](execution.md) for input consistency and staged run checks, and [outputs](outputs.md) for spatial support, staggering and time semantics. HRLDAS can also host urban components, but a WRF-coupled atmospheric experiment and an offline land experiment are not equivalent. See the [HRLDAS identity note](../hrldas-noahmp/card.md) only if that distinction is relevant. No additional model is loaded by default.
