# HRLDAS / Noah-MP: identity and mechanisms

Scope: offline HRLDAS with Noah-MP, emphasizing the v5.0 refactoring boundary. The lab's
release, host modifications and physics choices are unknown. Sources were checked on
2026-09-16; this is not a claim of compatibility with every later release.

## Two components, different jobs

HRLDAS supplies the offline host: forcing, initialization, time integration workflow and
I/O. Noah-MP supplies land-surface process calculations. Meteorological forcing includes
precipitation, radiation, wind, humidity, temperature and pressure. HRLDAS can use WRF
preprocessed geographic information without running an interactive atmosphere. Consequently,
an HRLDAS experiment does not by itself measure atmospheric feedback to altered land
conditions. The official repository includes Noah-MP as a submodule. [H1](sources.md#h1)

Noah-MP separates process options rather than defining a single universally fixed physics
configuration. The v5.0 modernization reorganized process code and data structures and
introduced a host interface around a column calculation. Thus a two-dimensional output
array does not establish how lateral flow or routing was represented. The actual host,
options and external components matter. [H3](sources.md#h3)

## Version and scientific choices

The maintainers describe v5.0 as a code refactoring of v4.5 physics, not permission to
interchange their variable names, parameter files or driver interfaces. Keep the HRLDAS
revision and Noah-MP submodule revision together when identifying a run. Treat examples
from older WRF-integrated code separately. [H2](sources.md#h2)

For an explanation, first identify which process the question concerns: canopy exchange,
snow, soil water/heat, runoff, vegetation or a coupled component. For an experiment,
preserve the selected options while tracing the effect being tested. A difference between
two outputs can originate in forcing, state initialization, physics selection or the host
interface, not just a changed equation. This is a diagnostic recommendation, not a model
default or a claim that all these causes are present in a particular run.

Use [execution](execution.md) for forcing/time/restart checks and [outputs](outputs.md)
for storage, flux and spatial interpretation. Use the v5.0 paper for the architecture;
the full technical notes and glossary are navigation resources in [sources](sources.md).
This pack does not select a runoff scheme, spin-up duration or calibration parameter.
