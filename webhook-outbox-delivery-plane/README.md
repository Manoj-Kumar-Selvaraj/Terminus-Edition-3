# Webhook outbox delivery plane

Edition 3 large-system task: durable webhook outbox with SQLite persistence, worker claim leases, HMAC-signed HTTP delivery, tenant quotas, DLQ replay, audit, CLI, and a thin operator UI.

## Why it is hard

Correctness spans several coupled invariants. A lease-safe claim must fence delivery completion; signatures must use the documented canonical string; quotas count successful deliveries in a rolling window; pause blocks claims; DLQ replay requires the operator token when configured; audit must record claim/dlq transitions. Fixing only one axis leaves the others failing.

## Solution approach

Read `/app/outbox/docs/delivery-contract.md`, compare starter behavior on claim/sign/quota/replay/audit/pause/UI, repair the incomplete modules, and rebuild `outboxd` / `outboxctl`.

## Verification

Separate verifier image rebuilds the submitted tree and runs behavioral pytest against a live server (temp DB, local HTTP sink). Oracle installs fixed sources via `solution/solve.sh` and must score reward 1; NOP scores 0.

## Image note

Agent and verifier use the canonical Go 1.24 bookworm digest. Verifier additionally bakes Python/pytest/requests.
