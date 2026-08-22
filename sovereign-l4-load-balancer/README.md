# sovereign-l4-load-balancer

Self-hosted layer-4 TCP load-balancing platform modeled after AWS NLB-style control and dataplane separation. A Go control plane distributes immutable listener and target-group snapshots to C++ userspace dataplanes that forward real TCP streams with health-aware selection, draining, zonal policy, and restart recovery.

## System boundary

The platform covers canonical desired-state validation, generation-scoped rollout, node-session fencing, connection ownership, PROXY protocol v2 emission, and checkpoint continuity. It does not implement HTTP routing, WAF/CDN behavior, DNS cutover, host route or firewall management, or cloud provisioning.

## Solver-visible layout

- `/app/sovereign-lb/bin/lb-control-plane` — management and control API
- `/app/sovereign-lb/bin/lbctl` — operator CLI
- `/app/sovereign-lb/bin/lb-dataplane` — epoll TCP dataplane
- `/app/sovereign-lb/bin/lab` — deterministic loopback backend lab
- `/app/sovereign-lb/docs` — architecture, protocol, configuration, rollout, recovery, and operations contracts
- `/app/sovereign-lb/config` — node profiles, fleet inventory, and scenario catalog

## Operational state model

Persistent and runtime state includes accepted revisions, idempotency records, compiled generation snapshots, rollout phases, node session fences, target health and drain runtime, padded dataplane checkpoints, and the three-zone fleet inventory. The loopback lab provides echo, slow-reader, half-close, reset, and PROXY inspection backends for end-to-end TCP verification.
