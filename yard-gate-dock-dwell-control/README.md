# yard-gate-dock-dwell-control

Operations / Logistics task: repair a DC yard gate-to-dock dwell control plane so Chicago appointment windows, exclusive occupancy, chassis, holds/detention, journal fences, and warehouse-isolated publish all agree with `/app/yard/docs/yard-contract.md`.

## Layout

- `environment/yard/` — agent workdir (`/app/yard`)
- `solution/solve.sh` — copies fixed modules and republishes
- `tests/` — separate verifier image; drives `yardctl`

## Local checks

Oracle must score 1 and NOP 0 under Harbor with `environment_mode=separate`. Artifacts transfer the full `/app/yard` tree.
