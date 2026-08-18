# Runtime architecture

The edge router is a single Go process with a public data plane and a local operator plane. The executable is `edge-router-runtime`; source lives under `/app/edge-router` in the task image.

## Package responsibilities

- `cmd/edge-router-runtime` owns command parsing and process startup.
- `internal/bootstrap` wires lifecycle, recovery, background managers, listeners, and shutdown.
- `internal/config` parses complete desired state, accepts source snapshots, normalizes input, and performs semantic validation.
- `internal/compiler` converts validated desired state into immutable route and upstream-pool views.
- `internal/reconcile` serializes accepted generation work and coordinates runtime publication.
- `internal/runtime` owns serving snapshots, endpoint runtime handles, pool continuity state, and snapshot leases.
- `internal/router` matches requests and drives selection/retry/upstream execution.
- `internal/selection` owns weighted choice, affinity lookup, retry exclusion, and failover traversal.
- `internal/upstream` owns reusable HTTP transports and endpoint request accounting.
- `internal/health` observes endpoint health and updates runtime handles.
- `internal/drain` advances removed endpoint runtime objects through draining and retirement.
- `internal/checkpoint` stores accepted desired state and restart metadata under the configured state directory.
- `internal/telemetry` owns bounded process/generation/endpoint metric series.
- `internal/admin` exposes status, update submission, checkpoint visibility, and metrics.

## Control plane

Configuration arrives as a complete source snapshot. Each source supplies a source name and monotonically ordered revision. The ingress layer retains the accepted material for all sources and constructs one merged desired state. A candidate is normalized and validated before compilation.

Compilation creates a complete route graph and complete pool view. Reconciliation is the serialized owner of generation acceptance. A serving generation is represented by one `RuntimeSnapshot`, containing routes, pools, source revision metadata, and the normalized desired state used to produce it.

## Data plane

A request resolves a route by host, path prefix, method, and route priority. The selected route points to a generation-scoped upstream pool. Pool configuration carries selection, affinity, retry, failover, health, and drain policy.

Endpoint configuration and endpoint runtime state are intentionally separate concepts. Configuration is immutable within a serving generation. Mutable health, membership, request counts, transport lifetime, and continuity state live behind runtime handles.

## Runtime ownership

`PublicationStore` is the process-wide serving-generation owner. `Registry` owns reusable pool and endpoint runtime handles. `RuntimeSnapshot` references those handles while exposing immutable routing configuration.

A snapshot lease represents request reachability. Long-running requests may retain a generation while a newer generation becomes current. Endpoint runtime objects may also outlive the generation that originally introduced them when they are still referenced by active work.

## Process lifecycle

Startup performs these phases:

1. validate the state directory and bootstrap configuration;
2. recover an accepted generation when durable state exists, otherwise compile bootstrap state;
3. publish a complete initial serving generation;
4. start health, drain, data-plane, and admin-plane loops;
5. mark public serving ready.

SIGINT and SIGTERM stop new readiness, shut down both listeners, stop reconciliation/background loops, close transports, and wait for owned goroutines within the shutdown budget.

## Concurrency model

Request readers are concurrent. Reconciliation is logically single-writer. Health and drain managers mutate runtime handles through their synchronized methods. Metric registration and snapshots are protected by the telemetry registry.

The architecture does not require privileged containers, host networking, a Docker socket, kernel capabilities, or external state services. Runtime state is local to the configured state directory and all network interfaces are ordinary unprivileged TCP listeners.
