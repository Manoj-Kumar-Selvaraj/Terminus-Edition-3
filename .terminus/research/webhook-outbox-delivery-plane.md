# Research: webhook-outbox-delivery-plane

## CREATION_RULE_CONTEXT
- CONTROL_PLANE_COMMIT: 88e17620d0a13530127d61849557ec01ecdb1687
- CREATION_PROFILE: large_system_strict

## Candidates considered
1. **Webhook outbox delivery plane** (recommended) — durable enqueue, worker claim fencing, HMAC-signed HTTP delivery, backoff/DLQ/replay, tenant quotas, audit. Operator API + CLI.
2. Feature-flag progressive desk — targeting/sticky/%/kill-switch; strong but closer to “config product” and easier to pad evaluators.
3. Secret lease broker — short-lived creds + fencing; narrower F2P surface (~edge of SCENARIO_TOO_SMALL for 25–30 organic F2P).

## Why this one
- Real platform reliability work package (not a single bug report).
- Coupled invariants: claim lease ↔ delivery attempts ↔ signature ↔ quota ↔ DLQ replay ↔ audit.
- Naturally supports 25–30 distinct F2P behaviors and 10k+ seeded outbox/attempt rows.
- Novelty vs Edition 3 inventory: `ansible-ci-control-plane` mentions pipeline webhooks/idempotency but is CI orchestration, not an HTTP outbox delivery plane. No existing task is a signed webhook outbox with claim fencing + DLQ + quotas.

## Non-goals / anti-reskin
- Not Terraform, not payment/EOD/HRIS, not workshop booking, not JetStream continuity, not Stackyard TFC UI.

## Scale fit
- Target substantive LOC: 3500–5000 Go/SQL/JS/sh (reachable).
- Seed: 12_000+ events across tenants/endpoints with varied statuses/attempts.
- Defects: 6–7 root causes, 20–28 manifestations with causal edges (claim→double delivery→quota skew→audit gap).
