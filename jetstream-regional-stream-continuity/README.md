# Regional telemetry continuity service

This repository tree contains the operator control plane used to keep two intermittently connected edge telemetry domains converged with a central JetStream archive. Each edge accepts device events into a local durable journal and JetStream origin stream. The hub sources both origins, processes the combined archive with durable consumers, and records application-side effects and replay/checkpoint state in SQLite.

The service is intentionally stateful. A reconnect is not considered healthy merely because the NATS servers are reachable: the edge journal, origin generation, hub archive membership, consumer checkpoint, effect ledger and retention watermark must agree. The normal operator entrypoint is `/app/continuity/bin/continuityctl`.

## Runtime layout

- `/app/continuity/config/` — JetStream topology and policy configuration.
- `/app/continuity/continuity/` — Python control-plane and worker implementation.
- `/app/continuity/state/continuity.db` — durable journal, checkpoints, replay plans and effect ledger.
- `/app/continuity/log/archive/` — captured incident/controller logs.
- `/app/continuity/ops/` — shift handoff and captured stream state.
- `/app/continuity/docs/` — event-envelope, continuity and operator contracts.
- `/app/continuity/out/` — generated health and reconciliation reports.

`bin/start-lab.sh` starts the hub and both edge JetStream domains. `bin/reset-lab.sh` recreates the inherited starting state from the deterministic SQL seed. `bin/continuityctl inspect` produces a current health snapshot; `bin/continuityctl reconcile` performs a dry-run comparison; `bin/continuityctl recover` applies a safe replay/recovery plan; and `bin/continuityctl verify` checks convergence invariants after recovery.

The edge journals remain the replay authority until the hub archive and all required durable consumers have crossed the same confirmed origin watermark. Stream sequence numbers from the hub aggregate are not interchangeable with an edge origin sequence because sourced streams are interleaved at the destination. Event identity and origin metadata therefore remain explicit throughout the pipeline.
