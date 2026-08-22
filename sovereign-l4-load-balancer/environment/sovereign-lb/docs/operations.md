# Operations

Build all binaries with `/app/sovereign-lb/bin/build`. Start the control plane with `/app/sovereign-lb/bin/lb-control-plane`. Start one dataplane with `/app/sovereign-lb/bin/lb-dataplane --config /app/sovereign-lb/config/nodes/dp-01.json`. Use `/app/sovereign-lb/bin/lbctl` for management calls and `/app/sovereign-lb/bin/lab` for deterministic loopback backends.

The control plane listens on separate management HTTP and framed-control TCP addresses. Dataplane status is a local HTTP endpoint. Bind addresses and state roots come from flags or explicit environment variables; defaults remain under `/app/sovereign-lb/state`.

Apply is complete-state replacement and requires both revision and idempotency key. Inspect desired, generations, rollout, nodes, health, audit, readiness, and metrics before and after an apply. A rollout that misses quorum is investigated and retried with a new accepted revision; operators do not edit generation files.

Graceful control-plane shutdown stops accepting mutations, flushes durable state, closes control sessions, and leaves dataplanes serving their active checkpoints. Graceful dataplane shutdown drops readiness, stops accepts, drains owned streams to deadline, checkpoints authority, and then closes workers.

State directories are private operational data. Snapshot content may include internal addresses but no secrets. Metrics and audit data must not include payloads, source addresses, idempotency keys, or unbounded target/generation labels.

The lab binds loopback only. Production deployment, privilege separation, TLS transport, host firewall policy, service supervision, and external secret distribution are operator responsibilities outside this package.