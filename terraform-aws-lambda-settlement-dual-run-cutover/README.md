# Lambda settlement dual-run cutover

Edition 3 Terraform + Go incident: repair a broken settlement cutover controller and Lambda deployment so a twelve-stage workflow runs against a sealed local effect plane (ledger, report, notify, archive, DLQ) with generation-pinned aliases, exactly-once journals, poison isolation, and Jenkins as a read-only shadow.

## Why it is hard

Correctness spans Terraform package/alias identity, durable controller state, and live runtime effects. Fixing only the plan, only retries, or only cutover leaves interacting failures (stale generation pins, duplicate ledger writes, Jenkins writes after Lambda primary, partial batches without DLQ).

## Solution approach

Align stage contracts and published `live` aliases in Terraform, then repair the controller so deploy/run/resume/cutover/rollback/reconcile honor journals, locks, poison DLQ, and generation pinning against `/opt/settlement-runtime`.

## Verification

The separate verifier replans submitted Terraform, rebuilds `settlementctl`, drives hidden batches (poison, lost replies, restart, cutover/rollback, protocol variants), and grades runtime effects plus the cutover report — not source spelling.

Final base is the canonical Go Bookworm image so agents can rebuild the controller while Terraform and the sealed runtime are baked at build time.
