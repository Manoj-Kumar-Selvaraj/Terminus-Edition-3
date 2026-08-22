# Case Schema

Each file in `/app/fluidlab/cases` is one JSON case definition.

Required top-level fields:

- `case_id` string
- `family` string
- `fluid` object
- `geometry` object
- `mesh` object
- `solver_monitor` object
- `limits` object
- `operating_points` array

`fluid` fields:

- `model`: `incompressible_liquid` or `ideal_gas`
- `name`
- `density_kg_m3`
- `dynamic_viscosity_pa_s`
- `cp_j_kgk`
- `thermal_conductivity_w_mk`
- `reference_temperature_k`
- `thermal_expansion_per_k`
- `gamma`
- `gas_constant_j_kgk`

For liquid cases, `density_kg_m3`, `reference_temperature_k`, and `thermal_expansion_per_k` are authoritative. For gas cases, `gamma` and `gas_constant_j_kgk` must be present and the density model must remain internally consistent with the pressure and temperature used for the same operating point.

`geometry` fields:

- `hydraulic_diameter_m`
- `flow_area_m2`
- `wetted_perimeter_m`
- `length_m`
- `roughness_m`
- `minor_loss_coefficient`
- `heat_exchange_area_m2`
- `characteristic_cell_length_m`

`mesh` fields:

- `cell_count`
- `max_aspect_ratio`
- `mean_skewness`
- `max_skewness`
- `min_orthogonality`
- `negative_volume_cells`

`solver_monitor` fields:

- `iterations`
- `target_iterations`
- `time_step_s`
- `continuity_residual`
- `momentum_residual`
- `energy_residual`
- `mass_imbalance_percent`
- `energy_imbalance_percent`

`limits` fields:

- `max_mach`
- `max_cfl`
- `min_mesh_score`
- `max_pressure_drop_pa`
- `max_bulk_temperature_k`
- `max_mass_imbalance_percent`
- `max_energy_imbalance_percent`
- `max_final_residual`

Each entry in `operating_points` must provide:

- `point_id`
- `mass_flow_kg_s`
- `inlet_temperature_k`
- `wall_temperature_k`
- `inlet_total_pressure_pa`
- `outlet_static_pressure_pa`
- `heat_load_w`

All published values are SI. Every case and operating point must preserve its original identity in the output artifacts.
