# Architecture

The plugin follows a capture, normalize, reduce, analyze, publish, project pipeline. Six source adapters copy Jenkins-visible values into immutable canonical records. Full scans and listener hints enter a shared reducer. Analysis engines consume a snapshot and emit observational queue, build, lineage, and plugin views. A generation repository publishes typed files, checksums, a checkpoint, and analysis under one generation identifier.

Queries acquire one published snapshot. Authorization projection is part of the query boundary and precedes any response material visible to a caller. Both Jenkins transports and the standalone operator call the same query service and use canonical JSON.

## Ownership

Jenkins remains authoritative for jobs, runs, queue items, nodes, fingerprints, and plugin metadata. The plugin owns only its event journal, immutable generation directories, leases, and `CURRENT` pointer. Derived state may always be rebuilt from source state plus durable post-checkpoint hints.

## Runtime graph

`Initializer -> InsightsRuntime -> recovery -> journal replay -> health`

`AsyncPeriodicWork -> sources -> reducer -> analysis -> generation publication`

`listeners -> bounded ingress -> journal -> reducer -> generation publication`

`CLI/RootAction/operator HTTP -> authorization -> query -> canonical JSON`

Removal of any source adapter removes one canonical family. Removal of the journal loses restart continuity. Removal of generation verification removes crash-safe selection. Removal of authorization projection makes aggregate and correlation output unsafe.
