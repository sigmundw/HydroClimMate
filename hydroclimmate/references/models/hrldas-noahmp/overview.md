# HRLDAS / Noah-MP: identity and mechanisms — moved

This file is a redirect stub. Start at **[card.md](card.md)** (the only must-read file), then
**[processes.md](processes.md)** for question → switch → module → variable. Version scope:
**[version.md](version.md)**. Provenance: **[sources.md](sources.md)**.

## Two components, different jobs

Noah-MP is the column land-surface physics — one independent column per grid cell, no lateral
flow. HRLDAS is the offline host: it reads the setup file and the forcing, runs the time loop,
calls Noah-MP and writes NetCDF. Host arrays are mapped to Noah-MP column variables in a
transfer layer, so an internal name and a written name are often different. An offline HRLDAS
experiment has no atmospheric feedback to altered land conditions.
Full detail, with `path:line` citations at the pinned commit pair, is in
[card.md](card.md) and [processes.md](processes.md).
