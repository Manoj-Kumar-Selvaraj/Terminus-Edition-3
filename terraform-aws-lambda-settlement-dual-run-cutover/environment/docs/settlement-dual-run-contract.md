# Settlement dual-run cutover contract

Offline dual-run cutover for bank settlement batches. Terraform publishes one Lambda function per stage with immutable package hashes and a `live` alias. The Go controller (`settlementctl`) deploys generations into the sealed runtime at `/opt/settlement-runtime` and drives stage side effects through that runtime only. Authoritative ledger, report, notify, archive, and DLQ state lives in the runtime — local controller files alone are not proof.

## Stages (exact order)

1. `intake`
2. `verify_manifest`
3. `acquire_lock`
4. `fetch_inputs`
5. `validate_inputs`
6. `transform_records`
7. `precheck_ledger`
8. `write_ledger`
9. `build_report`
10. `notify_partner`
11. `archive_batch`
12. `release_lock`

Item fan-out stages: `fetch_inputs`, `validate_inputs`, `transform_records`, `precheck_ledger`, `write_ledger`.

Per-stage timeout, memory, reserved concurrency, and IAM actions are defined in `/app/terraform/workspaces/settlement/stages.json` and must match the documented resource contracts in evidence. Function names are `settlement-pipeline-<stage>`. Alias must be `live` (never `$LATEST`). Package hashes must be unique. Wildcard actions and wildcard invoke principals are forbidden. Runtime is `provided.al2023` with handler `bootstrap` and `publish = true`.

## CLI

`/app/bin/settlementctl` (built from `/app/cmd/settlementctl`) must support:

```text
settlementctl deploy --infra <directory>
settlementctl run --request <json-file>
settlementctl resume --execution <execution-id>
settlementctl cutover --generation <n> --writer lambda
settlementctl rollback --generation <n>
settlementctl jenkins-shadow --request <json-file>
settlementctl reconcile
settlementctl inspect --what cutover|execution|runtime [--execution <id>]
```

`run` / `resume` exit 0 only for terminal `SUCCEEDED` or `PARTIAL`. Exhausted transient retries print a durable `RETRY_PENDING` checkpoint and exit nonzero. Reuse of an `execution_id` with a different batch, owner, or artifact digest must fail with a diagnostic containing `conflicting`.

## Durable controller state

Under `/app/var/settlement`:

- `operations.journal.jsonl` — `STARTED` then `COMMITTED`/`FAILED` per operation
- `executions/<execution_id>.json` — checkpoint
- `deployment-<generation>.json`
- `cutover.json`
- `requests/<execution_id>.json`

Operation identity is `execution/stage` or `execution/stage/item`. External effect keys: `{batch}/ledger/{item}`, `{batch}/report`, `{batch}/notify`, `{batch}/archive`.

## Retry and poison

Retry budget is 3 attempts (`/app/config/retry-policy.json`). Resume continues at `next_stage` (zero-based index of first unfinished stage). Poison items fail permanently on `validate_inputs`; after 3 attempts they enter the runtime DLQ. Valid siblings continue. Terminal status is `PARTIAL` when any item is DLQ'd, else `SUCCEEDED`. One execution owns a batch lock; unrelated batches may run concurrently. Locks release on success or partial completion.

## Cutover and protocols

Generation is pinned when an execution starts. `deploy` reads `deployment.json.generation`. Cutover and rollback change only new work; in-flight executions keep their starting generation and epoch. When Lambda is primary, `jenkins-shadow` must not write settlement effects. Lost alias-shift replies must be reconciled from runtime inspect before adopting local cutover state.

Protocol v1 may omit owner (`legacy-jenkins/<batch_id>`). Protocol v2 requires a non-blank owner. Unsupported versions are rejected before mutation.

## Reconcile

`reconcile` truncates a torn journal tail, redeploys on confirmed generation drift, and resumes `RUNNING` / `RETRY_PENDING` executions. A second identical reconcile is a no-op on the summary fields.

## Operator entrypoint

`/app/bin/settlement-dual-run` regenerates `/app/var/settlement/plan.json`, builds and runs the controller against the sealed runtime, and writes `/app/output/cutover-report.json` with:

- `status` (`READY` on success)
- `report_digest` (stable SHA-256 over the documented stable fields)
- `active_generation`, `writer`, `epoch`
- `execution_status`, `effect_counts`, `plan_resource_count`
- `runtime_writer`, `runtime_effects`

Success requires `status: READY`, Lambda writer, matching controller/runtime writer, and a second identical run preserving `report_digest`.
