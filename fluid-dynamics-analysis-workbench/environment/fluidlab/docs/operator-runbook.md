# Operator Runbook

Build and runtime entrypoints:

- Build: `/app/fluidlab/scripts/build.sh`
- Analyze with wrapper: `/app/fluidlab/scripts/run_analysis.sh`
- Analyze with CLI: `/app/fluidlab/bin/fluidlab analyze --root /app/fluidlab`

The workbench reads:

- `/app/fluidlab/config/system.json`
- every `*.json` file in `/app/fluidlab/cases`

The workbench writes:

- `/app/fluidlab/output/summary.json`
- `/app/fluidlab/output/operating_points.csv`
- `/app/fluidlab/output/checkpoints/current.json`

The CLI and shell wrapper are expected to use the same pipeline and publish the same metrics and status decisions.
