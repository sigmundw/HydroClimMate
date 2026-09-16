# MODFLOW sources and coverage

Checked: 2026-09-16. Scope: MODFLOW 6 GWF concepts and floating `stable` input documentation.
Lab version: unknown. No executable, FloPy workflow or model dataset was run or installed.

## G1

[USGS MODFLOW 6 code](https://github.com/MODFLOW-ORG/modflow6)
and [framework report](https://pubs.usgs.gov/publication/tm6A57):
retrieved; identity, model-family incompatibilities and framework structure. The report
is the 2017 publication, DOI 10.3133/tm6A57; it is not a current package catalog.
USGS www landing pages were readable through the research tool but returned HTTP 403
to the URL checker; the links above use the developer repository and publication record.

## G2

[NPF flow-property package](https://modflow6.readthedocs.io/en/stable/_mf6io/gwf-npf.html):
retrieved; hydraulic properties and cell flow behavior. Exact options depend on the release.

## G3

[STO storage package](https://modflow6.readthedocs.io/en/stable/_mf6io/gwf-sto.html):
retrieved; specific storage/yield, cell conversion and period-specific steady/transient
behavior. The simplified volume example in outputs.md is a dimensional derivation under
stated assumptions, not an exact storage equation for every package configuration.

## G4

[DIS](https://modflow6.readthedocs.io/en/stable/_mf6io/gwf-dis.html),
[DISV](https://modflow6.readthedocs.io/en/stable/_mf6io/gwf-disv.html) and
[DISU](https://modflow6.readthedocs.io/en/stable/_mf6io/gwf-disu.html): retrieved;
grid dimensions, geometry, connectivity and domain status. Package support for pass-through
cells differs; inspect the chosen discretization rather than transferring flags blindly.

## G5

[Temporal discretization](https://modflow6.readthedocs.io/en/stable/_mf6io/sim-tdis.html):
retrieved; periods, steps and time units. Output times are a separate configuration.

## G6

[Array recharge](https://modflow6.readthedocs.io/en/stable/_mf6io/gwf-rcha.html) and
[wells](https://modflow6.readthedocs.io/en/stable/_mf6io/gwf-wel.html): retrieved;
dimensional distinctions and well-rate signs. No physical coupling from a land model is assumed.

## G7

[Iterative Model Solution](https://modflow6.readthedocs.io/en/stable/_mf6io/sln-ims.html):
retrieved; iteration and convergence definitions. No solver tolerance is recommended universally.

## G8

[Output Control](https://modflow6.readthedocs.io/en/stable/_mf6io/gwf-oc.html): retrieved;
head and budget selection and saving. Binary layouts are not distilled here.

## Limits

MODFLOW-2005/NWT syntax, GWT transport, density/energy coupling, detailed advanced packages
and lab calibration/restart recipes remain outside coverage. These summaries are original
paraphrases with explicit diagnostic recommendations, not a full redistributed USGS manual.
