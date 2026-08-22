# Architecture

Sovereign LB is a self-hosted layer-4 TCP load balancer. A single logical Go control plane accepts complete desired documents, validates them, compiles immutable snapshots, and coordinates publication to C++ dataplane nodes. Dataplanes own listeners and established streams; they do not mutate desired state.

## Authority boundaries

The desired revision is the authority for configuration writes. A node acknowledgement sequence is authority only within one registered node session. These counters are independent. A replacement session fences all messages from an older process, even when the old process reports a newer generation.

An accepted desired document compiles to exactly one generation and SHA-256 digest. The snapshot contains every listener, target group, target incarnation, and policy needed to serve traffic. A dataplane never composes runtime state from multiple generations.

## Control plane

`lb-control-plane` owns the HTTP management API, control-stream listener, snapshot repository, node registry, rollout coordinator, health aggregation, audit ring, metrics, and durable state. `lbctl` is a thin API client. All mutation commands carry a revision and idempotency key.

The control plane validates before assigning a generation. It writes generation content before moving durable pointers, preserves prior active authority when prepare fails, and treats replay as an idempotent observation rather than a new transition.

## Dataplane

Each `lb-dataplane` has a control client, immutable active snapshot, prepared candidate, listener set, epoll worker, target selector, health state, connection registry, drain manager, checkpoint store, metrics, and local status endpoint. Accepted connections retain a shared runtime reference until teardown.

## Lifecycle

1. An operator applies a complete document at a monotonic revision.
2. Validation and canonical compilation produce a generation and digest.
3. The coordinator sends `prepare` to current sessions and records fenced responses.
4. A configured quorum of live current sessions must report `prepared` for the exact generation and digest.
5. The coordinator sends `activate` only to sessions that prepared that candidate.
6. Nodes atomically publish the candidate and report `active`.
7. The control plane advances acknowledged rollout state without deleting runtime generations still owned by streams.

## Resource bounds

Configuration limits listeners, targets, frame bytes, queue depth, retained generations, audit events, health samples, connection metadata, and per-stream buffering. Status and metrics use bounded dimensions. Traffic payload is never logged, audited, or returned by management APIs.

## Exclusions

The service does not parse HTTP, route by host or path, implement WAF/CDN policy, alter DNS, manage host routing or firewalls, or provision cloud resources.