# mizuRoute: routing rather than runoff generation

Scope: standalone routing concepts from the official `stable` documentation checked
2026-09-16. That alias moves; the actual checkout, routing options and coupling are unknown.

## Model roles

mizuRoute represents a river network and transports supplied runoff toward downstream
reaches. Its current official repository is ESCOMP/mizuRoute; the older NCAR URL redirects
there. Identifying an upstream hydrological model is separate from identifying the routing
configuration. [M1](sources.md#m1)

The documentation separates hillslope routing from channel routing. In the documented
workflow, runoff on the river-network HRUs is area-converted, and a hillslope response can
delay delivery to channels. Determine whether the supplied quantity already includes that
delay before enabling another one. [M3](sources.md#m3)

Channel choices include impulse-response and wave-based approaches. The guide also provides
an upstream-accumulation option without channel routing; accumulated runoff and routed
discharge must not be treated as interchangeable hydrographs. Channel geometry and method
choices affect propagation, so changing a routing option is a scientific decision, not
merely an I/O switch. [M4](sources.md#m4)

## Network HRUs need not match the source grid

The input guide distinguishes runoff already on river-network HRUs from runoff on another
hydrological HRU system or grid. The latter cases require mapping into the river-network
HRUs. Source row order or matching array lengths do not establish spatial correspondence.
[M2](sources.md#m2)

For a bias or timing problem, recommended diagnosis proceeds from the supplied runoff and
its units to spatial mapping, network topology, hillslope treatment and channel transport.
An outlet hydrograph alone may not distinguish errors in those stages. Keep upstream model
outputs fixed when isolating a routing change, and define the evaluation locations and period.

Use [execution](execution.md) for the input contract and [outputs](outputs.md) for reach
statistics. [VIC](../vic/overview.md) is one possible runoff producer, not a mandatory
component. Reservoirs, water management, solute transport and coupled CTSM interfaces are
not implemented or validated by this knowledge pack; their exact behavior needs local evidence.
