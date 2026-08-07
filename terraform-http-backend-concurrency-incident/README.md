# terraform-http-backend-concurrency-incident

Edition 3 conversion of the Edition 2 offline state-lock simulator into a live
HTTP Terraform backend with SQLite durability and real concurrent CLI clients.

## Why it is hard

Lock tokens, lineage/serial fencing, idempotent commit retries, workspace
isolation, lease expiry on a deterministic clock, and provider mirror provenance
all interact. Fixing only one axis still fails under concurrent applies and
restart barriers.

## Verification

The separate verifier starts the submitted backend, drives Terraform HTTP
clients with barriers (no wall-clock races), and grades live remote state plus
audit export — not narrative reports. Oracle must score 1; NOP must score 0.
