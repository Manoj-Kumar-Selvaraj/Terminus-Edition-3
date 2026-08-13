# Terminus Retrieval Metadata and Indexing Contract

Retrieval metadata policy version: `1.0`

This policy defines the canonical metadata envelope for any repository/control-plane content that may later participate in exact, lexical, semantic/vector retrieval or retrieval caching.

It does **not** authorize access to content. Authorization is resolved first from `.terminus/agents/evidence_visibility.json`, role policy, Protocol, and packet-specific allowed/excluded evidence. Retrieval metadata only describes an already-classified source and provides enough provenance/freshness information to filter it safely.

## Core rule

Future retrieval MUST apply this order:

`stage/role/packet authority -> evidence visibility filter -> freshness/provenance filter -> exact/structured lookup -> lexical/vector ranking -> context assembly`

Never search the whole corpus and remove forbidden material after ranking. Excluded evidence must not enter the candidate pool.

## Canonical machine contract

The machine-readable field contract is `.terminus/agents/retrieval_metadata.json`.

A concrete indexed unit must conform to `.terminus/agents/schemas/retrieval_chunk.schema.json`.

A generated index manifest must conform to `.terminus/agents/schemas/retrieval_manifest.schema.json`.

The metadata contract is validated by `.terminus/validate_retrieval_metadata.py` and is also invoked from Agent System CI.

## Identity and provenance

Every indexed unit has two identities:

- `document_id` — stable identity for the source version, derived from repository/source identity + canonical path/location + immutable source version such as git blob SHA, packet hash, run/artifact ID, or external-content hash;
- `chunk_id` — stable identity for the exact indexed unit, derived from `document_id` + canonical structural/span locator + chunk content hash.

Path, filename, heading text, task name, or semantic similarity alone are never sufficient identity.

Repository-backed sources should record both `git_blob_sha` and `content_hash`. Non-repository evidence must record an equivalent immutable `source_version` and `content_hash`.

## Required metadata envelope

Every concrete retrieval chunk records:

### Source identity

- `document_id`
- `chunk_id`
- `source_uri`
- `source_path` when repository-backed
- `source_kind`
- `source_version`
- `content_hash`
- `git_blob_sha` when repository-backed

### Evidence classification

- `evidence_class` — exactly one class declared by `evidence_visibility.json`;
- `sensitivity` — `PUBLIC | SOLVER_VISIBLE | CONTROL_PLANE | PRIVATE | RESTRICTED`;
- `solver_visible` — explicit boolean, never inferred only from directory location.

### Commit/policy binding

Where applicable:

- `task_id`
- `task_commit`
- `control_plane_commit`
- `policy_versions`
- `role_contract_hash`
- `packet_binding`

Fields that do not apply are omitted rather than filled with invented sentinel values.

### Applicability

- `stage_applicability` — explicit registered stage IDs or `ALL_AUTHORIZED_STAGES` only for genuinely global control-plane material;
- `role_applicability` — explicit role names/classes or `ALL_AUTHORIZED_ROLES` only when appropriate;
- `freshness_scope` — what change invalidates reuse of this indexed unit for retrieval decisions.

Applicability is a secondary narrowing mechanism. It never expands the evidence visibility granted by the stage/role/packet contract.

### Structural chunk location

- `chunk_type`
- `section_path`
- `symbol` when code/symbol-oriented
- `line_start` / `line_end` when a stable text range exists
- `ordinal` for deterministic ordering inside the document

## Source kinds

The v1 contract recognizes these source kinds:

- `CONTROL_PLANE_MARKDOWN`
- `CONTROL_PLANE_JSON`
- `CONTROL_PLANE_CODE`
- `TASK_INSTRUCTION`
- `TASK_DOCUMENTATION`
- `TASK_CODE`
- `TASK_CONFIGURATION`
- `PRIVATE_DESIGN`
- `SOLUTION_ORACLE`
- `VERIFIER_PRIVATE`
- `REVIEW_PACKET`
- `REVIEW_RESULT`
- `SESSION_STATE`
- `CI_RUNTIME`
- `MODEL_TRIAL`
- `FINAL_PACKAGE`
- `PUBLIC_REFERENCE`

Adding a source kind requires updating the machine contract and validator; indexers must not silently invent arbitrary categories.

## Chunking policy

Chunking is structural before it is token-count based.

Preferred boundaries:

- Markdown policy/docs: heading subtree, preserving heading ancestry in `section_path`;
- stage/visibility/metadata JSON: one stage/evidence-class/profile object per chunk where practical;
- source code: module/class/function/symbol boundary, with file/module context attached;
- instruction: whole instruction when within the Edition 3 concise limit; otherwise paragraph/bullet groups without separating a requirement from its qualifiers;
- review packet: packet identity/allowed evidence/excluded evidence/result schema as deterministic sections, never mixed with prior results;
- CI/runtime logs: run/job/step or bounded error-event windows with immutable run/job identity;
- session state: identity, gate registry, conflicts, and next-action sections rather than arbitrary token windows;
- public references: page/section units with canonical source URL/content hash and retrieval timestamp where available.

Token-window splitting may be used only inside an oversized structural unit and must preserve overlap/span provenance. It must not be the primary chunking strategy for policy, packet, or stage-contract material.

## Freshness scopes

`freshness_scope` is one or more of:

- `CONTENT_HASH`
- `GIT_BLOB_SHA`
- `TASK_COMMIT`
- `CONTROL_PLANE_COMMIT`
- `POLICY_VERSION`
- `ROLE_CONTRACT_HASH`
- `PACKET_BINDING`
- `REVIEW_SCOPE_HASH`
- `CI_RUN_ID`
- `EXTERNAL_CONTENT_HASH`

Retrieval/cache reuse is valid only while every declared scope remains current for the invocation.

## Retrieval filtering contract

Before ranking, a retrieval controller must resolve:

```text
STAGE_ID
ROLE
TASK_ID / TASK_COMMIT when applicable
CONTROL_PLANE_COMMIT
ROLE_CONTRACT_HASH when applicable
PACKET_BINDING when applicable
REQUIRED_EVIDENCE_CLASSES
ALLOWED_OPTIONAL_EVIDENCE_CLASSES
EXCLUDED_EVIDENCE_CLASSES
CURRENT_FRESHNESS_BINDINGS
```

A chunk is eligible only when:

1. its `evidence_class` is required/allowed for the invocation and not excluded by any higher-precedence contract;
2. its sensitivity is permitted for the role;
3. all applicable task/control-plane/policy/packet freshness bindings match;
4. stage/role applicability matches;
5. solver-only executions see only solver-visible task content plus the minimum execution contract explicitly permitted by policy.

Only then may exact, lexical, BM25, embedding/vector, reranker, or cached retrieval scores be considered.

## Caching implication

Future caches should key at minimum on:

`content_hash + metadata_contract_version` for parsing/chunk/embedding reuse;

and on:

`stage_id + role + task_commit + control_plane_commit + evidence_policy_hash + freshness_bindings + query_hash` for retrieval-result reuse.

A cached retrieval result must be re-filtered/revalidated against current authorization and freshness before use. A cache hit never grants visibility.

## Anti-leakage invariants

- `SOLUTION_ORACLE`, `VERIFIER_PRIVATE`, private creator design, prior reviews, and model-trial evidence remain inaccessible to solver-visible-only executions even if their embeddings are colocated physically.
- A changed task/control-plane commit must not reuse stale chunks merely because the path and text similarity remain high.
- A role/packet exclusion always wins over stage applicability metadata.
- Semantic ranking must never infer authority or provenance.
- Retrieval metadata and index manifests are control-plane artifacts and must not be packaged into solver-visible tasks unless explicitly required by Edition 3 rules.

## What this step intentionally does not implement

This policy does not choose a vector database, embedding model, BM25 implementation, reranker, storage backend, or remote service. Those are retrieval-engine implementation choices to be made only after this metadata/authorization contract is stable.