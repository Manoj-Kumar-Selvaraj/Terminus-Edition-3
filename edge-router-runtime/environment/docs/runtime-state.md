# Runtime state and recovery

The serving generation is an immutable `RuntimeSnapshot`. Mutable health, affinity, balancer cursor, transport, membership, and request-lifecycle state belong to runtime handles referenced by snapshots.

## Generations

A candidate update is not a serving generation until semantic validation, compilation, generation fencing, runtime reconciliation, and publication complete. Runtime generations are monotonically increasing identifiers for accepted serving snapshots.

A request obtains one generation lease. Route lookup, primary pool selection, retry policy, and failover pool references are interpreted from that same leased generation. A newer publication does not rewrite an older leased snapshot.

The publication store exposes one current snapshot. A replaced snapshot becomes retired but remains reachable while leases or lifecycle owners still reference it.

## Endpoint identity

Endpoint identity consists of stable pool identity, canonical network identity, and transport compatibility. Cosmetic address spelling does not create a new logical endpoint.

An endpoint that remains continuously present across accepted generations may preserve compatible health, selection, affinity, and transport state. An endpoint that is accepted as removed and later re-added is a new membership incarnation even when its canonical network address is the same.

Endpoint membership transitions are:

`ACTIVE -> DRAINING -> RETIRED`

Health transitions are independent:

`UNKNOWN <-> HEALTHY <-> UNHEALTHY`

Membership eligibility and health eligibility are both considered before assigning new work.

## Pool continuity

Pool runtime state is reusable only when the stable pool identity and selection/affinity compatibility fingerprint are compatible. Semantic equivalence is independent of declaration-only ordering and descriptive metadata.

Affinity entries are bounded by TTL and capacity. Every affinity lookup is validated against the current generation's membership, endpoint incarnation, lifecycle eligibility, and health. An invalid entry is removed or replaced by normal selection.

## Draining

An endpoint removed by an accepted generation enters draining before that generation becomes eligible to assign new work. Draining endpoints do not receive new initial selections, retries, or sticky assignments.

Already-owned work may finish. Retirement waits until the endpoint is unreachable by retained serving snapshots and owned request/transport work is complete, or until the configured lifecycle deadline requires cleanup. A rapid re-add creates a distinct active incarnation instead of reviving the draining incarnation.

## Durable checkpoints

The state directory contains generation checkpoint bodies and small pointer files. A checkpoint body contains:

- checkpoint schema version;
- accepted runtime generation;
- normalized desired state;
- accepted per-source revisions and digests;
- compatible bounded continuity material when present;
- content digest and checksum;
- creation metadata.

The durable acceptance point is represented by `CURRENT`. `PREVIOUS` may retain the prior committed pointer for recovery fallback.

A checkpoint body must be completely written and made durable before a pointer can make it authoritative. Publication and durable acknowledgement follow one ordered acceptance transaction. Directory metadata is synchronized when pointer replacement is part of the acceptance boundary.

## Crash semantics

Before publication, the previous `CURRENT` remains authoritative. If a process dies after an in-memory generation became visible but before durable acceptance, restart may legitimately recover the previous accepted generation. After `CURRENT` is durably committed, restart recovers the new accepted generation.

Startup validates pointer shape, checkpoint schema, checksum, generation metadata, and complete desired state. If `CURRENT` is unusable, recovery tries `PREVIOUS`, then the supplied bootstrap state. The runtime stays not-ready if no complete source is recoverable.

Recovered desired state is normalized, semantically validated, and recompiled as a whole before one complete snapshot is published. Only compatible, non-expired continuity state may be restored. Provider/source fences are installed before new watcher traffic can race with recovered state.

## Bounded state

Affinity tables, status history, generation observations, retired lifecycle records, reusable transports, and metric ownership all have explicit lifecycle owners. Retirement removes state whose owner is no longer reachable so repeated configuration changes do not create unbounded process growth.
