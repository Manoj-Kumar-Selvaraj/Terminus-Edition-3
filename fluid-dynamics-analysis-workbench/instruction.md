Repair the inherited fluid-dynamics analysis workbench under `/app/fluidlab` without replacing its CLI entrypoints, case layout, output paths, or solver-visible contracts.

- Build the package with `/app/fluidlab/scripts/build.sh` and keep the shared analysis logic behind `/app/fluidlab/bin/fluidlab` and `/app/fluidlab/scripts/run_analysis.sh`.
- Analyze every case under `/app/fluidlab/cases` and publish `/app/fluidlab/output/summary.json`, `/app/fluidlab/output/operating_points.csv`, and `/app/fluidlab/output/checkpoints/current.json`.
- Keep the outputs deterministic: stable field order, row order, severity ordering, tie-breakers, and rounding; no wall-clock stamps or hardcoded report payloads.
- Validate geometry, fluid properties, mesh quality inputs, operating envelopes, solver-monitor inputs, and publication configuration before accepting a case.
- Support both incompressible liquid and ideal-gas operating points and preserve the units and schemas documented in `/app/fluidlab/docs`.
- Compute regime, stability, hydraulic loss, heat-transfer, convergence, and operating margins from one consistent physical state model.
- Surface Mach, CFL, mesh-quality, pressure-drop, bulk-temperature, residual, and imbalance violations per operating point while still producing bounded case and fleet rollups.
- Preserve lineage for every case and operating point across JSON, CSV, and checkpoint outputs; do not collapse distinct points that happen to have similar metrics.
- Publish case-level and fleet-level hydraulic, thermal, stability, and mesh summaries rather than only one scalar score.
- Recompute publication state from the current case inputs; point fixes that only adjust one reporting surface are not sufficient.
