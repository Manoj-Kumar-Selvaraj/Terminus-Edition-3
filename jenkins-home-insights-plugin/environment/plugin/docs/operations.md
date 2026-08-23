# Operations

`bin/insights generate --home PATH --records 14536` creates a deterministic sanitized home. `reconcile` scans it and publishes a generation. `query` reads a published view. `event` appends and applies one listener-shaped transition. `restart` closes and reconstructs runtime state. `compact --retain N` applies generation retention. `health` emits readiness and lag. `serve --port N` exposes local JSON endpoints.

All state-changing operator commands print one JSON object and return nonzero on rejected input or failed persistence. Query and health are read-only. Paths may be set with `--home` and `--state`, or through `JENKINS_HOME` and `INSIGHTS_STATE`.

Before maintenance, capture health and generation inventory. During shutdown, ingress closes first, scheduled work is cancelled, durable journal writes are flushed, and publication is fenced. After restart, health is ready only when `CURRENT` verifies, replay has caught up, and required source capabilities are available.

Compaction is safe to repeat. Operators should retain at least two generations when filesystem failure fallback is required. A lease file means a reader still owns that generation and prevents deletion.

The runtime never contacts update centers or other network services. Plugin compatibility and dependency status come only from installed metadata.
