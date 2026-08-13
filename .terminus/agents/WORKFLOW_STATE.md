# Terminus Edition 3 Workflow State Materialization

Workflow-state policy version: `1.0`

This layer derives the current task workflow view from immutable execution records, their append-only ledger, the selected current task commit, the selected control-plane commit, canonical stage/state contracts, machine acceptance predicates and explicit evidence-freshness overrides. It is a controller aid, not an acceptance authority.

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

The state resolver never turns historical chat, desired outcome, an old session, or a **materialized state file into acceptance evidence**. The authoritative derivation remains:

`stage/role contract -> invocation(input task commit) -> validated result(output task commit) -> execution record -> hash-chained ledger -> derived workflow state`.

A materialized `.terminus/workflows/<task>/state.json` is rebuildable. Discard/regenerate it whenever the current task commit, control-plane commit, ledger head or explicit freshness input changes. `.terminus/workflows/` is ignored by Git; `.terminus/executions/` is durable provenance and is not ignored.

Legacy `.terminus/sessions/<task>.md` remains controller/migration context. It is not silently converted into execution history, and missing records remain `MISSING` rather than being fabricated from session prose.

Execution records/ledgers/workflow snapshots are excluded from ordinary static RAG. Any future retrieval exposure requires an explicit provenance-aware adapter and normal evidence authorization.

## Bootstrap and task identity

Before `RULE_RESOLUTION`, the controller reserves the stable task ID and identifies an exact existing Git commit as the bootstrap/input task snapshot. This lets the task ledger begin at stage 0 even before a new task directory has been materialized.

Do not create a taskless durable pre-history and later relabel it. A taskless stage invocation can be an ephemeral preview only.

## Ledger

Every persisted task execution record lives at:

`.terminus/executions/<task>/<invocation_id>.result.json`

and is referenced by exactly one append-only event in:

`.terminus/executions/<task>/ledger.jsonl`.

Each event binds sequence, previous event ID, record/invocation/stage/task IDs, **input task commit**, **output task commit**, control-plane commit, canonical record path and record SHA-256. The event ID hashes the event payload excluding `event_id`.

The record is written before the event. Orphan records are ignored. Exact re-append is idempotent. Duplicate/conflicting identity, broken sequence/hash chain, missing/tampered record or path escape fails closed.

## Record selection and temporal ordering

For each stage, state resolution uses the **last valid ledger event for that stage**. Later retry/route/block/success attempts supersede earlier attempts without rewriting history.

Ledger sequence remains a dependency boundary. A downstream selected event must occur after the latest selected current executable predecessor. Therefore an upstream rerun invalidates older downstream results **even when the task/control commits are unchanged**. The resolver explicitly reports that the downstream record **predates the latest current predecessor execution**.

This preserves the invariant that **downstream acceptance cannot survive a non-current predecessor**.

## Task commit lineage

A workflow is not a set of records that all happen to mention the final Git SHA. It is an attributable chain:

`bootstrap A -> stage A→A -> producer A→B -> reviewer B→B -> fixer B→C -> controller C→C ...`

For a stage to be current:

1. `task_lineage.input_task_commit` must equal the invocation authority task commit;
2. except for the first current record, that input commit must equal the previous current executable stage's output commit;
3. the output commit must equal or descend from the input commit;
4. the output commit must remain on the ancestry of the selected current task commit;
5. only producer/fixer role classes may change input→output commit;
6. record identity, transition semantics and machine acceptance predicates must remain valid;
7. explicit evidence freshness must remain current;
8. predecessor and ledger temporal order must remain current.

This solves the producer false-staleness problem: a valid producer record `A→B` is not invalid simply because later stages advance the task to `C`. What matters is that the current execution chain is `A→B→...→C`.

### Unattributed task change

If the current Git task commit is ahead of the latest current recorded output commit and the next stage has no execution record accounting for that change, the workflow does **not** silently absorb the new commit or rerun everything from stage 0. It returns `BLOCKED` with `UNATTRIBUTED_CHANGE` lineage so the controller can identify the responsible producer/fixer action and record/reconcile it.

If the recorded output commit is not on the current task lineage, lineage is `BROKEN` and advancement is blocked/stale as applicable.

The derived snapshot exposes:

```text
LINEAGE.STATUS: UNINITIALIZED | CURRENT | UNATTRIBUTED_CHANGE | BROKEN
LINEAGE.BOOTSTRAP_TASK_COMMIT:
LINEAGE.RECORDED_TASK_COMMIT:
LINEAGE.CURRENT_TASK_COMMIT:
```

## Currentness

A stage node is:

- `CURRENT` only when its authority, lineage, value predicates, evidence, predecessor dependency and temporal order all validate;
- `STALE` when a selected historical record no longer fits current control/task/evidence/lineage state;
- `MISSING` when no event exists and no unattributed commit needs reconciliation;
- `BLOCKED` for a current route/retry/block result, invalid state entry, or unattributed task mutation.

A record may legitimately have an input/output commit older than the current HEAD when later current records connect it to HEAD. Exact-current equality is required at the **end of the attributable chain**, not independently for every historical stage.

## Machine acceptance predicates

When a selected record has `ADVANCE`, state reconstruction re-evaluates `.terminus/agents/stage_acceptance_predicates.json`. A stored flag saying “predicate passed” is not trusted by itself.

This prevents a hand-forged or stale aggregate record from advancing merely because it says `PASS` and contains the required keys. Semantic judgments still come from their owning reviewer evidence; predicates only ensure the aggregate faithfully reflects those judgments/facts.

## FROZEN_CANDIDATE

`FROZEN_CANDIDATE` is the non-executable controller state between `DETERMINISTIC_VALIDATION` and `QUALITY_INTERLOCK`.

It requires current successful FORMAT, COMPLEXITY, RUNTIME_AUTHENTICITY and DETERMINISTIC_VALIDATION records, Oracle reward 1, NOP reward 0, present F2P/P2P empirical matrices and no unresolved rule conflict. Failure blocks `QUALITY_INTERLOCK`; freeze is never inferred from branch freshness or prose.

## Evidence freshness overlay

Task commit lineage is always checked. Additional evidence may be explicitly marked `CURRENT | STALE | MISSING` and may carry a content hash. Explicit stale/missing or changed hash invalidates the citing record and downstream dependencies. Absence from the overlay does not override stricter Protocol/packet freshness rules.

## Next action

The resolver emits exactly one:

- `INVOKE_STAGE` — first genuinely missing/stale stage;
- `RETRY_STAGE` — current result requires the same stage again;
- `ROUTE` — current result requires a registered failure route;
- `BLOCKED` — explicit block/state failure/**unattributed commit**;
- `VALIDATE_STATE` — non-executable state needs controller validation;
- `END` — all stages/states are current and the recorded output lineage equals current task commit.

The primary role is always the canonical stage owner, not any role that happens to have retrieval visibility.

## Controller recording rule

When `controller_cli.py record` accepts a producer/fixer result, it appends the immutable record and then rematerializes workflow state against the record's **output task commit**. Do not rematerialize against the invocation's older input commit after the stage created a new commit.

## Normal ChatGPT portability

Local Python provides deterministic `status`, `next`, `record` and `continue` helpers. When it is unavailable, a **normal ChatGPT conversation** may read the same Git commits, ledger, records and contracts through connected GitHub and apply the same rules. The helper is an execution adapter, not a required service.
