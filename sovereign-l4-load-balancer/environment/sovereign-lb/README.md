# Sovereign LB

Sovereign LB is a self-hosted layer-4 TCP load balancer starter. The Go control plane accepts complete desired state, compiles immutable generations, and coordinates two-phase rollout. The C++ dataplane owns listeners and TCP streams, selects health-eligible targets, and retains generation ownership for established connections.

## Layout

- `cmd/lb-control-plane` and `cmd/lbctl`: management server and client.
- `internal`: model validation, revision authority, snapshots, persistence, sessions, rollout, health, protocol, audit, metrics, and API.
- `dataplane`: C++20 control client, immutable runtime, epoll proxy, selection, health, draining, checkpoints, status, and metrics.
- `config`: deterministic desired state, fleet inventory, and a runnable node profile.
- `tools/lab`: loopback backend processes.
- `docs`: architecture and operational contracts.

The service is TCP-only. It does not inspect HTTP, manipulate host networking, alter DNS, or provision infrastructure.