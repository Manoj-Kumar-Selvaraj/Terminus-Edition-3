# Analysis Contract

The workbench publishes three artifacts under `/app/fluidlab/output`:

- `summary.json`
- `operating_points.csv`
- `checkpoints/current.json`

`summary.json` must be a deterministic JSON object with these top-level fields in this order:

1. `schema_version` string
2. `system_name` string
3. `publication_revision` string
4. `status` string
5. `fleet_rollup` object
6. `cases` array

`fleet_rollup` must include:

- `case_count` integer
- `operating_point_count` integer
- `status_counts` object keyed by `FAIL`, `WARN`, `PASS`
- `worst_mach_margin`
- `worst_cfl_margin`
- `worst_pressure_margin_pa`
- `worst_temperature_margin_k`
- `worst_mesh_score`

Each entry in `cases` must include:

- `case_id`
- `family`
- `source_digest`
- `status`
- `mesh`
- `aggregates`
- `operating_points`

Each `operating_points` entry must include:

- `point_id`
- `status`
- `flow_regime`
- `metrics`
- `margins`
- `convergence`
- `findings`

`metrics` must report density, velocity, Reynolds number, Mach number, CFL, pressure drop, outlet temperature, and heat-transfer coefficient using SI units. `margins` are signed values where negative means the point violates its configured limit.

`operating_points.csv` must contain one row per analyzed operating point, sorted by `case_id`, then descending severity using `FAIL`, `WARN`, `PASS`, then `point_id`. Columns and column order are controlled by `/app/fluidlab/config/system.json`.

`checkpoints/current.json` must summarize the current publication revision, overall status, per-case digests, and the artifact paths produced in this publication. It must describe the same analyzed state as `summary.json` and `operating_points.csv`.
