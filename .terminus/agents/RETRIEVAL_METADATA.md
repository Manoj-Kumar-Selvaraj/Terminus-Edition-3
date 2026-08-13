# Terminus Retrieval Metadata and Indexing Contract

Retrieval metadata policy version: `1.0`

This policy defines the canonical metadata envelope for repository/control-plane content participating in exact, lexical, vector/hybrid retrieval or retrieval caching.

It does **not** authorize access to content. Authorization is resolved first from `.terminus/agents/evidence_visibility.json`, the selected stage's permitted role set, role policy, Protocol, and packet-specific allowed/excluded evidence. Retrieval metadata only describes an already-classified source and provides enough provenance/freshness information to filter it safely.

The executable reference engine is defined by `.terminus/agents/RETRIEVAL_ENGINE.md` and `.terminus/retrieval/`.

## Core rule

Retrieval MUST apply this order:

`stage + stage-authorized role + packet authority -> evidence visibility filter -> freshness/provenance filter -> authorized candidate pool -> exact/structured | lexical/BM25 | vector/hybrid ranking -> bounded context assembly`

The legacy shorthand **stage/role/packet authority** refers to this same first step; it does not mean that any canonical role may use any canonical stage.

Never search the whole corpus and remove forbidden material after ranking. Excluded evidence must not enter the candidate pool.

Retrieval metadata is **fail closed**. A chunk whose source kind, evidence class, sensitivity, solver visibility, applicability, or required freshness binding disagree with the registered source profile is invalid and must not enter any retrieval result.

## Canonical machine contract

The machine-readable field/source-profile contract is `.terminus/agents/retrieval_metadata.json`.

A concrete indexed unit must conform to `.terminus/agents/schemas/retrieval_chunk.schema.json` **and** the semantic checks in `.terminus/validate_retrieval_metadata.py`.

A generated index manifest must conform to `.terminus/agents/schemas/retrieval_manifest.schema.json`.

The metadata contract is validated by `.terminus/validate_retrieval_metadata.py`; the executable engine is separately validated by `.terminus/validate_retrieval_engine.py`. Both run from Agent System CI.

## Identity and provenance

Every indexed unit has two identities:

- `document_id` — stable identity for the source version, derived from repository/source identity + canonical path/location + immutable source version such as git blob SHA, packet hash, run/artifact ID, or external-content hash;
- `chunk_id` — stable identity for the exact indexed unit, derived from `document_id` + canonical structural/span locator + chunk content hash.

Path, filename, heading text, task name, or semantic similarity alone are never sufficient identity.

Repository-backed sources record `source_path`, `git_blob_sha` and `content_hash`. Non-repository evidence records an equivalent immutable `source_version` and `content_hash` plus the source-profile bindings that apply.

Control-plane and task freshness are independent. A task-scoped index may read task artifacts from `task_commit` while authoritative policy is read from a different `control_plane_commit`; a shared commit is a valid special case, not an implicit assumption.

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

- `evidence_class` — exactly one class declared by `evidence_visibility.json` and fixed by the source profile;
- `sensitivity` — `PUBLIC | SOLVER_VISIBLE | CONTROL_PLANE | PRIVATE | RESTRICTED`, fixed by the source profile;
- `solver_visible` — explicit boolean fixed by the source profile, never inferred from path or chosen by the indexer.

For example, `SOLUTION_ORACLE` can only be indexed as evidence class `SOLUTION_ORACLE`, sensitivity `RESTRICTED`, `solver_visible=false`. An indexer may not relabel it as solver-visible merely because it is textually relevant.

### Commit/policy binding

Where required by the source profile:

- `task_id`
- `task_commit`
- `control_plane_commit`
- `policy_versions`
- `role_contract_hash`
- `packet_binding`
- `review_scope_hash`
- `ci_run_id`

If a freshness scope is declared, its corresponding binding field must exist. A chunk cannot claim `TASK_COMMIT` freshness without carrying `task_commit`, or `PACKET_BINDING` freshness without carrying `packet_binding`.

### Applicability

- `stage_applicability` — only canonical stage IDs from `stage_contracts.json`, or `ALL_AUTHORIZED_STAGES` by itself;
- `role_applicability` — only canonical role IDs declared by `retrieval_metadata.json`, or `ALL_AUTHORIZED_ROLES` by itself;
- `freshness_scope` — what changes invalidate reuse of this indexed unit.

Human display names are mapped to stable canonical role IDs through `role_aliases`; arbitrary role strings are not legal retrieval metadata.

Applicability is a secondary narrowing mechanism. It never expands the evidence visibility granted by the stage/role/packet contract. Likewise, `ALL_AUTHORIZED_ROLES` means all roles already authorized for the selected stage; it is not permission for an unrelated canonical role to borrow that stage's authority.

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
- `SOLVER_VISIBLE_REQUIREMENT_CONTRACT`
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

`SOLVER_VISIBLE_REQUIREMENT_CONTRACT` is the sanitized controller-owned A7 handoff defined by `INSTRUCTION_POLICY.md`. Its content is solver-safe requirement material, but the durable control-plane artifact remains `solver_visible=false`; it is not a second solver-facing specification.

Adding a source kind requires updating the machine contract, chunk schema and validator. Indexers must not invent arbitrary categories.

## Source-profile constraints

Each source kind declares:

- fixed evidence class;
- fixed sensitivity;
- fixed `solver_visible` value;
- whether it is repository-backed;
- whether it is task-scoped;
- preferred structural chunk strategy;
- mandatory binding fields;
- mandatory freshness scopes.

Both the JSON Schema and the Python validator enforce these constraints. Retrieval backends consume already-validated chunks; they do not reinterpret source classification.

## Chunking policy

Chunking is structural before it is token-count based.

Preferred boundaries:

- Markdown policy/docs: heading subtree, preserving heading ancestry in `section_path`;
- stage/visibility/metadata JSON: one stage/evidence-class/profile object per chunk where practical;
- solver-visible requirement projection: one coherent requirement family/object without mixing private design material;
- source code: module/class/function/symbol boundary, with file/module context attached;
- instruction: whole instruction when within the Edition 3 concise limit; otherwise paragraph/bullet groups without separating a requirement from its qualifiers;
- review packet: packet identity/allowed evidence/excluded evidence/result schema as deterministic sections, never mixed with prior results;
- CI/runtime logs: run/job/step or bounded error-event windows with immutable run/job identity;
- session state: identity, gate registry, conflicts, and next-action sections rather than arbitrary token windows;
- public references: page/section units with canonical source URL/content hash and retrieval timestamp where available.

Token-window splitting may be used only inside an oversized structural unit and must preserve overlap/span provenance. It must not be the primary chunking strategy for policy, packet, or stage-contract material.

The reference indexer caches structural parse/chunk results by immutable Git blob SHA + parser-aware chunk strategy + chunker version. The parser/file-type discriminator is part of cache identity because identical bytes can require different structural parsing under different language/file semantics.

Reuse of cached chunks does **not** reuse task/control-plane authority: current invocation metadata bindings are attached again when the document is indexed for a new commit/scope.

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

Retrieval/cache reuse is valid only while every declared scope remains current for the invocation and every scope has its required binding value.

## Retrieval filtering contract

Before ranking, a retrieval controller must resolve:

```text
STAGE_ID
CANONICAL_ROLE_ID
STAGE_AUTHORIZED_ROLE_SET
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

1. the canonical role is authorized to retrieve under the selected stage;
2. it passes the source-profile/schema/semantic metadata validator;
3. its `evidence_class` is required/allowed for the invocation and not excluded by any higher-precedence contract;
4. its sensitivity is permitted for the role;
5. all applicable task/control-plane/policy/packet freshness bindings match;
6. canonical stage/role applicability matches;
7. solver-only executions see only `solver_visible=true` chunks.

Only then may exact, lexical/BM25, embedding/vector, hybrid fusion, reranking, or cached retrieval scores be considered.

## Caching implication — Implemented caching contract

The reference local engine implements three reuse layers:

- **parse/chunk cache** — immutable Git blob + parser-aware chunking strategy/version -> structural chunks;
- **embedding cache** — chunk ID + embedding provider/version + content hash -> vector;
- **retrieval-result cache** — authority hash + query hash + the current authorized pre-rank candidate-set hash -> ordered chunk IDs.

The candidate-set hash is derived from the actual authorized chunk identities/content hashes for the invocation. A global or latest manifest hash is not sufficient retrieval-cache identity.

A cached retrieval result is reloaded and re-authorized against the current invocation before use. A cache hit never grants visibility.

Cached ranking scores are diagnostic only and are not evidence or gate inputs. Current result-cache reuse preserves ordering/authorization rather than promising byte-for-byte equality of fresh component score telemetry.

Semantic judgments, reviewer verdicts and acceptance decisions are not cached by this engine. Any permitted reviewer reuse remains governed exclusively by Protocol provenance/scope rules.

## Reference retrieval engine

`.terminus/retrieval/` currently provides:

- independent commit-bound Git-blob indexing for control-plane and task snapshots;
- SQLite document/chunk/manifests storage;
- exact metadata/path/symbol/section/text retrieval;
- SQLite FTS5 lexical retrieval with deterministic Python BM25 fallback;
- a pluggable embedding interface;
- dependency-free deterministic hashing vectors as the default offline vector provider;
- optional local `sentence-transformers` semantic embeddings when explicitly installed;
- reciprocal-rank fusion across exact + lexical + vector ranking;
- strictly bounded context-bundle generation with full-chunk content hash and truncation marker when the final excerpt is clipped;
- `mandatory_exact_reads` separated from retrieved evidence;
- the three authorization-bound caches above.

The default hashing provider is a portable vector baseline, **not** a claim of state-of-the-art semantic embeddings. Higher-quality local/hosted embedding providers may implement the same provider interface without changing evidence authorization.

The reference engine does not require an OpenAI API key, a hosted vector database or a background service. Normal ChatGPT can continue the workflow through direct authorized GitHub reads when the local index is unavailable.

## Dynamic evidence boundary

The default repository scanner intentionally does not auto-ingest review packets/results, CI logs, session snapshots, model trials or final package evidence merely because those files/data exist. Those evidence types require exact provenance such as packet binding, role-contract hash, review-scope hash, CI run ID or external trial identity.

A future/provenance-aware ingestion adapter may add them only when it can supply the required metadata truthfully. Until then, packet-bound and dynamic evidence remains directly read through the existing GitHub/CI/controller workflow.

## Anti-leakage invariants

- a valid canonical role cannot borrow the evidence authority of an unrelated stage;
- `SOLUTION_ORACLE`, `VERIFIER_PRIVATE`, private creator design, prior reviews, and model-trial evidence remain inaccessible to solver-visible-only executions even if their vectors/cache rows are physically colocated;
- a `SOLUTION_ORACLE` chunk cannot be metadata-valid with `solver_visible=true` or evidence class `SOLVER_VISIBLE_TASK`;
- task and control-plane commits are separate freshness bindings and must not be silently conflated;
- a changed authorized candidate pool invalidates retrieval-result cache reuse even if no new global manifest was written;
- a changed task/control-plane commit must not reuse stale chunks merely because the path and text similarity remain high;
- a role/packet exclusion always wins over stage applicability metadata;
- arbitrary/typo role or stage identifiers are invalid metadata, not empty-result fallbacks;
- semantic ranking must never infer authority or provenance;
- retrieval metadata, SQLite indexes and cache/manifests are control-plane artifacts and must not be packaged into solver-visible tasks.
