# Terminus Dynamic Evidence Ingestion

Dynamic evidence ingestion policy version: `1.0`

This policy defines how evidence that is not part of the default static repository scan may enter the local retrieval store. It specializes `RETRIEVAL_METADATA.md` and `RETRIEVAL_ENGINE.md`; it does not grant evidence visibility, alter packet exclusions, or change Protocol freshness/reuse rules.

## Core invariant

Dynamic evidence is **explicitly projected, never discovered-and-trusted**.

`source provenance -> immutable content identity -> embedded binding verification -> stage-authorized consumer roles -> evidence-visibility check -> freshness metadata -> structural chunks -> local retrieval store`

The ingestor must reject evidence before persistence when any required provenance or projection check fails.

## Supported dynamic source kinds

Repository-backed explicit ingestion:

- `REVIEW_PACKET`
- `REVIEW_RESULT`
- `SESSION_STATE`

Externally supplied explicit ingestion:

- `CI_RUNTIME`
- `MODEL_TRIAL`
- `FINAL_PACKAGE`
- `PUBLIC_REFERENCE`

The default `RepositoryIndexer` continues to exclude review/session/dynamic runtime evidence. This prevents a filesystem glob from converting mere file presence into authority.

## Repository-backed provenance

Repository-backed dynamic sources are read through immutable Git objects from an explicit full `source_commit`; dirty working-tree text is never accepted.

### Review packet

The adapter derives and verifies from the packet JSON:

- `task`
- `task_commit`
- `control_plane_commit`
- `review_id` as `packet_binding`
- `role_contract_hash`
- producer `role`
- `review_scope_hash` when present

The task/control-plane commits must exist in repository history. The file must be under `.terminus/reviews/<task>/` and its filename must equal `<review_id>.packet.json`.

An active packet may be projected only to its own reviewer role and/or `CI_ORCHESTRATOR`, and only when those consumers are authorized for the selected stage. A Q4 packet therefore cannot become a Q6 packet merely because both roles participate in `QUALITY_INTERLOCK`.

### Review result

The adapter derives the same task/control-plane/review/role-contract provenance from the frozen result and verifies that `context_packet` resolves to `<review_id>.packet.json`.

`role_applicability` identifies retrieval consumers, not the role that produced the result. The producer remains bound through the immutable result content plus `role_contract_hash` and `packet_binding`. This permits a submission controller to consume an authorized prior result without relabelling that result as controller-authored evidence.

### Session state

The adapter derives:

- task identity;
- current task commit;
- Agent-system policy version;
- specialist prompt policy version;
- specialist protocol policy version;
- Pre-LLMaJ panel policy version;
- Comprehensive Reviewer policy version.

The session is accepted only when those version claims match the actual policy files at the same immutable `source_commit`. A session may not authenticate its own stale policy identities.

## External provenance

External evidence is not fetched automatically by the local engine. The controller/executor must explicitly provide UTF-8 content and an origin `source_uri` obtained through an authorized connector/tool/runtime.

The ingestor computes `source_version = sha256:<full-content-hash>` for all external evidence. Changing content therefore creates a new immutable source version even when the origin URI is unchanged.

Additional mandatory bindings remain those declared by `retrieval_metadata.json`:

- `CI_RUNTIME`: task ID, task commit, CI run ID;
- `MODEL_TRIAL`: task ID, task commit;
- `FINAL_PACKAGE`: task ID, task commit;
- `PUBLIC_REFERENCE`: external content identity; no task binding unless a future source profile explicitly adds one.

External ingestion records evidence; it does not prove the connector/source itself was legitimate. The controller must obtain the content through the authoritative GitHub/Harbor/model/submission workflow and preserve the exact origin URI/run identity supplied by that workflow.

## Projection identity

Dynamic evidence is stored as a stage/consumer-role projection. The projected `source_uri` appends a deterministic `terminus-projection` fragment derived from:

- one canonical stage ID;
- one or more canonical consumer role IDs authorized for that stage.

This permits the same immutable source content to exist in distinct safe projections without overwriting another stage/role projection. Projection metadata can narrow visibility only; it cannot broaden the stage evidence contract.

## Pre-persistence authorization

Before writing a dynamic document/chunk, the ingestor constructs the same `InvocationContext` used by retrieval and requires `RetrievalPolicy.authorize_chunk(...)` to allow the projection for every declared consumer role.

Consequences:

- a source class excluded by the stage cannot be ingested for that stage;
- a canonical role not authorized for the stage is rejected;
- missing task/packet/run/policy freshness bindings are rejected;
- solver-visible-only stages cannot receive private/control-plane dynamic evidence;
- an active review packet cannot be projected to an unrelated reviewer.

## Producer provenance vs consumer applicability

These concepts must remain distinct:

- **producer provenance** answers who/what generated the evidence and under which immutable packet/role/run binding;
- **consumer applicability** answers which current stage/role may retrieve that evidence.

Do not overwrite producer provenance to make evidence convenient for another consumer. In particular, `role_contract_hash` on review artifacts remains the review artifact's frozen role-contract binding.

## Retrieval and cache interaction

Dynamic evidence enters the same SQLite `documents`/`chunks` tables as static indexed content and is subject to the same authorization-first ranking and candidate-set-bound retrieval cache.

Adding or removing authorized dynamic evidence changes the candidate-set hash and invalidates cached ranking. Cached semantic reviewer verdicts remain forbidden; a review result is evidence content, not a cached acceptance decision.

## CLI

Repository evidence:

```bash
python .terminus/retrieval/cli.py --root . ingest-repository \
  --source-kind REVIEW_PACKET \
  --source-path .terminus/reviews/<task>/<packet>.packet.json \
  --source-commit <commit-containing-packet> \
  --stage QUALITY_INTERLOCK \
  --role Q4_SPEC_TEST_CONTRACT_REVIEWER
```

External evidence:

```bash
python .terminus/retrieval/cli.py --root . ingest-external \
  --source-kind CI_RUNTIME \
  --input /path/to/exact-run-evidence.txt \
  --source-uri github-actions://<repo>/run/<run>/job/<job> \
  --task-id <task> \
  --task-commit <task-sha> \
  --ci-run-id <run> \
  --stage DETERMINISTIC_VALIDATION \
  --role CI_ORCHESTRATOR
```

Normal ChatGPT does not require these commands. It may continue to read dynamic evidence directly through authorized GitHub/CI connectors; the ingestion layer is an optional local persistence/retrieval optimization.

## Failure behavior

Fail closed when:

- a dynamic source kind is unsupported by the selected adapter;
- a repository source is not an immutable Git object at the supplied commit;
- embedded task/control-plane commits are malformed or absent from repository history;
- packet/result path, review ID, context-packet, or producer-role identity is inconsistent;
- a session policy claim disagrees with policy files at its source commit;
- external content is empty or lacks required task/run bindings;
- a consumer role is not authorized for the stage;
- the stage excludes the source evidence class;
- a required freshness binding is missing.

Never repair, infer, or fabricate missing provenance during ingestion.
