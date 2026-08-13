# Terminus Retrieval Engine

Retrieval engine policy version: `1.0`

This policy defines execution semantics for local exact, lexical/BM25, vector and hybrid retrieval. It specializes `.terminus/agents/RETRIEVAL_METADATA.md` without changing evidence authority. The stage/role/packet contract decides what may be considered; the retrieval engine only ranks the already-authorized candidate pool.

## Core execution order

Every retrieval invocation applies this sequence:

`registered stage + stage-authorized canonical role + packet/role restrictions -> evidence visibility -> freshness/provenance -> authorized candidate set -> exact/structured | lexical/BM25 | vector | hybrid ranking -> bounded context assembly`

A canonical stage ID and a canonical role ID are not sufficient independently. The role must be permitted for that stage. A valid role must not borrow another stage's evidence authority.

No ranker may search an unrestricted corpus and filter forbidden results afterward.

## Mandatory exact reads

Files explicitly named by a stage contract in `policy_files` or `prompt_files` are authoritative exact-read inputs. Similarity search never substitutes for reading those files.

The retrieval engine returns `mandatory_exact_reads` separately from ranked evidence. An executor may satisfy those exact reads through normal repository tooling (GitHub connector, local Git, Codex/Work, or another authorized source). This preserves the workflow when no local retrieval index exists.

## Local implementation

The reference implementation lives in `.terminus/retrieval/` and uses:

- SQLite for documents/chunks/manifests/caches;
- SQLite FTS5 when available, with deterministic in-process BM25 fallback;
- structural chunking from the metadata contract;
- explicit provenance-aware dynamic evidence ingestion;
- a pluggable embedding interface;
- dependency-free signed feature hashing as the default offline vector provider;
- optional local `sentence-transformers` embeddings when that package/model is explicitly installed;
- reciprocal-rank fusion for hybrid exact + lexical + vector ranking.

The baseline workflow therefore requires no OpenAI API key, hosted vector database, background service or external embedding endpoint.

## Commit-bound indexing

Repository indexing reads immutable Git blobs, not dirty working-tree content. The control-plane snapshot and task snapshot are independent bindings:

- `control_plane_commit` selects authoritative control-plane sources;
- `task_commit` selects task-scoped sources;
- `--commit` exists only as a compatibility shorthand when both intentionally share one Git snapshot.

The index manifest binds:

- metadata contract version;
- evidence visibility version;
- control-plane commit;
- task ID/task commit when applicable;
- source-set hash;
- source/evidence counts;
- lexical backend/version;
- embedding-provider declaration.

Task-specific private design and sanitized requirement-contract sources must match the selected task identity. An indexer must not silently rebind artifacts from another task.

The default repository scanner intentionally excludes review packets/results, session state and external runtime/trial/package evidence. File presence alone is not provenance.

## Dynamic evidence ingestion

`.terminus/retrieval/ingestion.py` implements the explicit dynamic path governed by `.terminus/agents/DYNAMIC_EVIDENCE_INGESTION.md`.

Repository-backed dynamic evidence is accepted only through an explicit full Git `source_commit`:

- `REVIEW_PACKET` derives task/control-plane commits, review ID, role contract and producer role from the packet itself;
- `REVIEW_RESULT` preserves the frozen producer packet/role bindings while allowing a separately authorized retrieval consumer;
- `SESSION_STATE` derives task/policy identities and cross-checks those policy versions against the actual policy files at the same source commit.

Externally supplied dynamic evidence is never auto-fetched by the local engine:

- `CI_RUNTIME` requires task ID, task commit and CI run ID;
- `MODEL_TRIAL` requires task ID and task commit;
- `FINAL_PACKAGE` requires task ID and task commit;
- `PUBLIC_REFERENCE` is content-addressed and stage/role projected.

All external evidence uses a content-addressed `source_version`, so changing the content creates a new immutable version even when the origin URI is unchanged.

Dynamic evidence is stored as an explicit stage/consumer-role projection. Before persistence, the ingestor calls the same authorization policy used at retrieval time for every declared consumer. An excluded evidence class, wrong stage-role pair, missing freshness binding or packet-role mismatch blocks ingestion.

An active packet may be projected only to its own reviewer role and/or `CI_ORCHESTRATOR`. Review-result producer provenance is not rewritten to match a later controller consumer.

## Stage-role authorization

Retrieval resolves the executable role set for the selected stage before evidence filtering.

- the stage owner is permitted;
- the CI Orchestrator may perform bounded retrieval for routing/reconciliation;
- the Creation Controller may perform bounded retrieval for creation stages;
- declared semantic reviewers are permitted only where they actually belong to that stage;
- `SYSTEM_ARCHITECTURE` and `ENVIRONMENT_BUILD` resolve to their distinct A2 executable roles;
- `PRE_LLMAJ` expands the prose label `Stage-B specialists` only to the explicit seven specialist roles in `PRE_LLMAJ.md`, plus the Comprehensive Reviewer and routed Adjudicator.

A grouped display label never becomes a retrieval wildcard. Unknown or ambiguous participant mappings fail closed.

## Authorization and freshness

`.terminus/agents/evidence_visibility.json` is the stage visibility contract. `.terminus/agents/retrieval_metadata.json` is the source/freshness contract. Role/packet allowed/excluded evidence may only narrow stage access.

A chunk is eligible only when all applicable conditions pass:

- the invocation role is authorized for the selected stage;
- source profile matches evidence class, sensitivity and `solver_visible` value;
- evidence class is required/allowed and not excluded;
- stage and canonical role applicability match;
- solver-visible-only stages receive only `solver_visible=true` chunks;
- task identity/commit matches for task-scoped sources;
- control-plane commit matches when declared;
- role-contract, packet, review-scope and CI-run bindings match when declared;
- policy-version bindings match when declared.

Missing required invocation bindings fail closed. Task-scoped CLI retrieval requires an explicit `--task-commit`; it never guesses the task commit from the control-plane commit.

## Ranking modes

### `EXACT_ONLY`

Use metadata/path/symbol/section filters and exact text/phrase matching only. A stage contract declaring `EXACT_ONLY` cannot be upgraded to semantic/vector retrieval by a caller.

### `FILTERED_HYBRID`

After authorization, combine:

1. exact/structured ranking;
2. lexical BM25 ranking;
3. vector ranking;
4. reciprocal-rank fusion.

A caller may request one narrower ranker for diagnostics, but no request may broaden the stage's evidence pool.

### `SOLVER_VISIBLE_ONLY`

Apply the normal authorized retrieval path with the additional mandatory `solver_visible=true` constraint. Control-plane shadow contracts, private creator state, verifier material and Oracle material remain out of the candidate set even if physically colocated in the same SQLite database.

### `EXTERNAL_BOUND`

The local engine may return exact authorized preparation/context references, but it does not claim to replace the external model/evaluation boundary defined by the stage.

## Structural parse/cache identity

The parse/chunk cache uses immutable Git blob identity plus the structural strategy, parser/file-type discriminator and chunker version. This matters because the same bytes stored under different language/file-type semantics can require different structural parsing.

Cache reuse reuses parsing work only. Current task/control-plane bindings are attached again when the source is indexed for the active snapshots.

## Caching

The implementation has three safe reuse layers:

- **parse/chunk cache** keyed by immutable Git blob + parser-aware structural strategy + chunker version;
- **embedding cache** keyed by chunk ID + provider + provider version + content hash;
- **retrieval-result cache** keyed by authority hash + query hash + the actual authorized pre-rank candidate-set hash.

A global or merely latest manifest is not sufficient cache identity. If an eligible candidate is added, removed or changes content, the candidate-set hash changes and the ranking cache misses.

A retrieval cache stores chunk identities, not permission. Every cache hit is reloaded and re-authorized against the current invocation before use. Any stale/unauthorized chunk invalidates that cache hit.

Cached `SearchResult` score values are diagnostic ranking telemetry, not evidence, gate status or acceptance input. Current cache reuse preserves authorized result ordering; callers must not make control-plane decisions from score magnitude. If score components ever become a decision-bearing interface, they must be persisted exactly or recomputed rather than reconstructed from cached rank order.

Semantic reviewer verdicts are not cached by this retrieval engine. A `REVIEW_RESULT` may be indexed as provenance-bound evidence only where the stage visibility contract permits it; that does not convert the verdict into reusable acceptance authority.

## Bounded context assembly

`context_bundle(..., max_chars=N)` never emits more than `N` retrieved-content characters. If the final eligible chunk does not fit, the engine includes only the remaining prefix, carries the full chunk `content_hash`, and marks the item `truncated=true`.

`mandatory_exact_reads` are references to authoritative files and are outside this retrieved-content character budget because the executor must exact-read them separately.

## Normal ChatGPT portability

The retrieval engine is an optimization and context-selection layer, not a required execution surface. Normal ChatGPT can continue the workflow by exact-reading the stage contract/policy files and authorized repository/dynamic evidence through connected GitHub/CI tools even when `.terminus/cache/retrieval.sqlite3` does not exist.

When a local checkout/Work/Codex execution surface is available, the same stage invocation may build/query the local index through:

```bash
python .terminus/retrieval/cli.py --root . build \
  --task-path <task-path> \
  --task-id <task-id> \
  --task-commit <task-sha> \
  --control-plane-commit <control-plane-sha>

python .terminus/retrieval/cli.py --root . ingest-repository \
  --source-kind REVIEW_PACKET \
  --source-path .terminus/reviews/<task>/<review>.packet.json \
  --source-commit <commit-containing-packet> \
  --stage QUALITY_INTERLOCK \
  --role Q4_SPEC_TEST_CONTRACT_REVIEWER

python .terminus/retrieval/cli.py --root . ingest-external \
  --source-kind CI_RUNTIME \
  --input /path/to/exact-run-evidence.txt \
  --source-uri github-actions://<repo>/run/<run>/job/<job> \
  --task-id <task-id> \
  --task-commit <task-sha> \
  --ci-run-id <run> \
  --stage DETERMINISTIC_VALIDATION \
  --role CI_ORCHESTRATOR

python .terminus/retrieval/cli.py --root . context \
  --stage <STAGE_ID> \
  --role <CANONICAL_ROLE_ID> \
  --task-id <task-id> \
  --task-commit <task-sha> \
  --control-plane-commit <control-plane-sha> \
  --query '<evidence question>'
```

Controllers must treat retrieval output as bounded evidence context, not as an authority source or PASS verdict.

## Agent integration

Before invoking a registered role, a controller should:

1. resolve the stage contract and verify the canonical role is authorized for that stage;
2. exact-read mandatory policy/prompt files;
3. resolve packet/role evidence exclusions and freshness bindings;
4. optionally ingest explicitly sourced dynamic evidence when local persistence/retrieval is useful;
5. use retrieval, when available, only for additional authorized evidence selection;
6. include retrieved chunk provenance in the invocation packet or handoff when material;
7. continue using direct exact reads when retrieval/ingestion is unavailable or unnecessary.

Reviewers with packet-bound evidence remain packet-bound. The existence of an index or ingested dynamic evidence never expands the packet.

## Failure behavior

Return/block rather than guess when:

- stage or role ID is unknown;
- a valid role is not authorized for the selected stage;
- a grouped/ambiguous stage participant cannot resolve to an explicit canonical role set;
- required task/control-plane/packet/role freshness binding is missing;
- task and control-plane snapshots are incorrectly conflated when their commits differ;
- a dynamic repository artifact contradicts its embedded task/review/session provenance;
- a session policy identity does not match policy files at its source commit;
- external dynamic evidence lacks required task/run provenance;
- an active packet is projected to an unrelated reviewer;
- an indexed chunk contradicts its registered source profile;
- an index manifest is bound to the wrong task/control-plane commit;
- a solver-visible-only invocation would require a private/control-plane shadow source;
- a requested ranker would broaden an `EXACT_ONLY` or external-bound stage.

Never repair, infer or fabricate missing dynamic-evidence provenance during ingestion.
