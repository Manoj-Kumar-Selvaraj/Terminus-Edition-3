# Route Control Plane

`route-control-plane` is a Go service for managing desired Linux routing and policy state across a fleet without modifying the host network used to run the task. The service models nodes, interfaces, route tables, IPv4/IPv6 and multipath routes, policy rules, revisions, transactions, drift, rollouts and audit history, and exposes those responsibilities through an HTTP API and operator dashboard.

## State and change lifecycle

Routing changes are prepared as revisioned plans and applied through a transaction boundary. Route and rule identities are normalized so semantically equivalent state converges, policy-rule priorities and table dependencies remain valid, and stale plans cannot overwrite newer accepted revisions. Failed changes preserve the previous desired and observed state, while rollback creates a new monotonic revision rather than moving history backwards.

The durable state directory records desired/observed state, transactions, rollout progress, idempotency bindings and audit sequence. Restart recovery preserves completed authority and converts incomplete historical transaction phases into a safe terminal state before new work proceeds.

## Drift and fleet operations

Observed routing state is tracked independently from desired state. Reconciliation requires a current observation and repairs only route-control-plane-owned objects, leaving unrelated system routes intact. Management-routing protections are evaluated as part of change planning and application.

Fleet rollouts select nodes by labels, use bounded waves and optional canaries, reject stale/offline execution boundaries, and skip nodes already at the target revision. The representative fleet configuration is in `environment/config/fleet.yaml`.

## Deployment and dashboard

The Ansible role under `environment/ansible/roles/routecp` installs and configures the service, keeps generated configuration deterministic across reruns, and combines defaults with host-specific protected-routing input. The TypeScript dashboard in `environment/web` consumes the same API used by other operators and binds mutations to the revision returned by preview.

## Verification

The verifier exercises route/rule normalization, revision and idempotency fencing, failed-apply and rollback behavior, restart recovery, drift ownership/freshness, rollout safety, Ansible projection, dashboard concurrency, and public API/build preservation. The reference solution is deterministic and repeatable through `solution/solve.sh`; empirical Oracle/NOP execution remains owned by the later deterministic-validation lifecycle gate.
