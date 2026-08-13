# Terminus Edition 3 Workflow State Materialization

Workflow-state policy version: `1.0`

This layer derives the current task workflow view from immutable execution records, their append-only ledger, the selected exact task commit, the selected exact control-plane commit, the canonical stage contracts, the non-executable state contract, and any explicit evidence-freshness overrides. It is a controller aid, not an acceptance authority.

Canonical machine contract: `.terminus/agents/workflow_state_contract.json`.

Schemas:
- `.terminus/agents/schemas/execution_ledger_event.schema.json`;
- `.terminus/agents/schemas/workflow_state.schema.json`;
- `.terminus/agents/schemas/evidence_freshness.schema.json`.

Implementation:
- `.terminus/execution/ledger.py`;
- `.terminus/execution/state.py`;
- `.terminus/execution/controller_cli.py`.

## Authority

The state resolver never turns historical chat, desired outcome, an old session, or a materialized state file into acceptance evidence. The authoritative chain remains:

`stage/role contract -> invocation -> validated execution record -> hash-chained ledger -> derived workflow state`.

A materialized `.terminus/workflows/<task>/state.json` is a deterministic cache/view. It must be discarded or regenerated whenever its task commit, control-plane commit, ledger head, or explicit freshness input changes. `.terminus/workflows/` is intentionally ignored by Git; `.terminus/executions/` is not ignored because its immutable records and ledger are durable provenance.

Legacy `.terminus/sessions/<task>.md` remains useful controller context under existing policy, but it is not silently converted into execution records. Migration requires explicit evidence-backed records; missing history must remain `MISSING` rather than fabricated.

Execution records, execution ledgers and materialized workflow snapshots are not ordinary static RAG sources. The generic repository indexer must leave `.terminus/executions/` and `.terminus/workflows/` outside its automatic control-plane/task scan. Any future retrieval exposure of this state requires an explicit provenance-aware adapter and the normal evidence-visibility authorization path.

## Ledger

Every persisted task-scoped execution record is stored at:

`.terminus/executions/<task>/<invocation_id>.result.json`

and referenced by exactly one append-only ledger event in:

`.terminus/executions/<task>/ledger.jsonl`.

Each event binds sequence, previous event ID, record ID, invocation ID, stage, exact task/control-plane commits, canonical record path, and SHA-256 of the record bytes. The event ID is a SHA-256 over the event payload excluding `event_id`.

The controller writes the immutable record before appending the event. A crash that leaves an orphan record without a ledger event is safe: the state resolver ignores it. Re-appending the same exact record is idempotent. A duplicate record ID with different content, duplicate event ID, broken sequence, broken previous-event link, missing record, record-hash mismatch, or path escape fails closed.

## Record selection

For each stage, state resolution uses the last valid ledger event for that stage. This is how retries and repairs supersede earlier attempts without rewriting history.

A later `RETRY`, `ROUTE`, or `BLOCK` result therefore supersedes an earlier `ADVANCE` for the same stage. A later successful attempt supersedes the earlier failed attempt.

Ledger sequence is also a dependency boundary. For a downstream stage to remain current, its selected ledger event must occur **after** the selected current event of every executable predecessor. Therefore an upstream rerun invalidates older downstream results even when the task commit and control-plane commit did not change. Same-commit semantic repair/review cycles cannot preserve evidence that predates the repaired predecessor merely because hashes still match.

## Currentness

A stage record can be `CURRENT` only when:
- its task ID and exact task commit match the selected task snapshot;
- its exact control-plane commit matches the selected control-plane snapshot;
- its record ID/hash and execution semantics are valid under that control-plane snapshot;
- none of its explicit evidence refs is invalidated by the supplied freshness overlay;
- all predecessor nodes in the canonical workflow are current;
- its ledger event is temporally newer than the latest selected current executable predecessor event;
- its disposition is `ADVANCE` to the exact next registered stage/state/END.

If the latest record exists but its task/control/evidence/temporal binding is no longer current, the stage is `STALE`. If no ledger event exists, it is `MISSING`. A current `ROUTE`, `RETRY`, or `BLOCK` record makes that node `BLOCKED` for forward progress and carries the required controller action.

Once an upstream node is not current, later historical records are marked `STALE` by dependency propagation even if their own hashes still match. Downstream acceptance cannot survive a non-current predecessor.

## FROZEN_CANDIDATE

`FROZEN_CANDIDATE` is a non-executable controller state between `DETERMINISTIC_VALIDATION` and `QUALITY_INTERLOCK`.

The resolver validates it from current predecessor records. At minimum it requires:
- current successful `FORMAT_GATE`;
- current successful `COMPLEXITY_GATE`;
- current successful `RUNTIME_AUTHENTICITY`;
- current successful `DETERMINISTIC_VALIDATION`;
- Oracle reward exactly `1`;
- NOP reward exactly `0`;
- present F2P/P2P empirical matrices;
- no unresolved policy conflicts in the current rule-resolution record.

Failure of that state validation blocks `QUALITY_INTERLOCK`; it never silently jumps over freeze.

## Evidence freshness overlay

Task/control commits are always checked. Additional dynamic freshness may be supplied explicitly through an evidence-freshness object. Each ref may be marked `CURRENT`, `STALE`, or `MISSING` and may supply its current content hash.

An explicit `STALE`/`MISSING` status or a mismatching current hash invalidates every record that cites that ref and propagates staleness downstream. Absence from the overlay does not invent a change; stricter Protocol/packet/domain freshness validators remain authoritative and may still reject the evidence.

## Next action

The resolver emits one deterministic `next` action:
- `INVOKE_STAGE` — first missing/stale executable stage; includes primary role and declared inputs;
- `RETRY_STAGE` — latest current result requires the same stage to rerun;
- `ROUTE` — latest current result requires one registered failure route;
- `BLOCKED` — explicit blocking result or invalid non-executable state;
- `VALIDATE_STATE` — a non-executable state needs controller validation;
- `END` — every stage/state is current and `SUBMISSION_READY` advanced to END.

The primary role is the canonical stage owner, not an arbitrary allowed reviewer/controller role.

## Normal ChatGPT portability

Local Python provides deterministic `status`, `next`, `record`, and `continue` helpers. When unavailable, a normal ChatGPT conversation may read the same ledger/records/contracts through GitHub and apply the same rules. The helper is an execution adapter, not a required service.
