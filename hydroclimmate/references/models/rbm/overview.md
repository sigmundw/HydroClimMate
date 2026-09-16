# RBM: candidate river-temperature implementation

Identity status: **UW-Hydro RBM is a candidate, not a confirmed match to the lab model**.
Before executable commands or file-format assumptions, identify the actual repository,
branch and any coupling/reservoir modifications. Do not confuse this model with other
uses of the acronym RBM or treat all related forks as one implementation.

## Physical purpose

The UW-Hydro overview describes a one-dimensional stream-temperature model using a
semi-Lagrangian numerical approach for thermal-energy transport and exchange at the
air-water interface. Its documented lineage includes adaptations to hydrological outputs
from VIC and DHSVM. It is not itself a general land-surface rainfall-runoff model.
[R1](sources.md#r1)

In the VIC-RBM tutorial, the hydrological model produces land fluxes, a routing component
produces streamflow, and RBM combines flow and meteorological information to calculate
river temperature. The thermal boundary conditions include a headwater-temperature
relationship, while hydraulic quantities relate to discharge. This describes that coupled
workflow, not a requirement that every RBM application must use VIC.
[R2](sources.md#r2)

## What follows for a research question

Recommended checks distinguish three possible sources of disagreement: hydrological
forcing, routing/network representation and the temperature calculation. A temperature
bias alone does not identify which component caused it. Compare the actual applied inputs
at matched network locations and times before adjusting a thermal parameter.

Network topology is part of the physical setup, not merely a plotting coordinate system.
The checked Salmon River example has reach/node/segment relationships and can represent
multiple nodes in a confluence cell. It also documents limitations of its network builder.
Those details must not be generalized to an unconfirmed fork. [R3](sources.md#r3)

The repository characterizes RBM as research software with unevenly tested combinations
of options. Passing its build is therefore not a validation of a new combination.
[R4](sources.md#r4)

Use [execution](execution.md) to identify required evidence before running and
[outputs](outputs.md) for network-based interpretation. Reservoir stratification, alternate
routing schemes and exact lab file conventions are not established here. The source
record separates the inspected repository documentation from the online documentation
endpoint that could not be fetched during this review.
