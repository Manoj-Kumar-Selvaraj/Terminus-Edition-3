# Operational Insights Plugin

Operational Insights derives a read-only, restartable view of controller state. It correlates nested jobs, build history, queue demand, executor capacity, artifact fingerprints, and installed plugin metadata without changing Jenkins scheduling or configuration.

The repository is an HPI-shaped Maven project. The production core deliberately has no Jenkins runtime dependency and can be compiled with `bin/build-core`; `io.jenkins.plugins.insights.jenkins.OperationalInsightsPlugin` supplies the Jenkins initializer, terminator, periodic work, listener, CLI, and RootAction bindings. The same core is exercised outside Jenkins through `bin/insights`.

## Layout

- `src/main/java/.../model` contains canonical records and identities.
- `source` owns six read-only adapters over controller exports.
- `journal` and `reconcile` own listener hints and state convergence.
- `analysis` computes queue, build, lineage, and plugin views.
- `storage` owns immutable generations, recovery, migration, leases, and retention.
- `query` owns authorization, filtering, ordering, pagination, and response shape.
- `runtime` owns lifecycle, scheduling, health, and publication orchestration.
- `operator` exposes deterministic CLI and local HTTP workflows.

All derived files belong under the configured insight state directory. Jenkins-owned files are source material and are never rewritten. See `docs/` for protocol and operational contracts.
