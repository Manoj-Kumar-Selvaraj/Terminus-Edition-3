# Terminus Retrieval Engine

Retrieval engine policy version: `1.0`

This policy defines execution semantics for local exact, lexical/BM25, vector and hybrid retrieval. It specializes `.terminus/agents/RETRIEVAL_METADATA.md` without changing evidence authority. The stage/role/packet contract decides what may be considered; the retrieval engine only ranks the already-authorized candidate pool.

## Core execution order

Every retrieval invocation applies this sequence:

`registered stage + canonical role + packet/role restrictions -> evidence visibility -> freshness/provenance -> authorized candidate set -> exact/structured | lexical/BM25 | vector | hybrid ranking -> bounded context assembly`

No ranker may search an unrestricted corpus and filter forbidden results afterward.

## Mandatory exact reads

Files explicitly named by a stage contract in `policy_files` or `prompt_files` are authoritative exact-read inputs. Similarity search never substitutes for reading those files.

The retrieval engine returns `mandatory_exact_reads` separately from ranked evidence. An executor may satisfy those exact reads through normal repository tooling (GitHub connector, local Git, Codex/Work, or another authorized source). This preserves the workflow when no local retrieval index exists.

## Local implementation

The reference implementation lives in `.terminus/retrieval/` and uses:

- SQLite for documents/chunks/manifests/caches;
- SQLite FTS5 when available, with deterministic in-process BM25 fallback;
- structural chunking from the metadata contract;
- a pluggable embedding interface;
- dependency-free signed feature hashing as the default offline vector provider;
- optional local `sentence-transformers` embeddings when that package/model is explicitly installed;
- reciprocal-rank fusion for hybrid exact + lexical + vector ranking.

The baseline workflow therefore requires no OpenAI API key, hosted vector database, background service or external embedding endpoint.

## Commit-bound indexing

Repository indexing reads immutable Git blobs from a selected commit, not dirty working-tree content. The index manifest binds:

- metadata contract version;
- evidence visibility version;
- control-plane commit;
- task ID/task commit when applicable;
- source-set hash;
- source/evidence counts;
- lexical backend/version;
- embedding-provider declaration.

Task-specific private design and sanitized requirement-contract sources must match the selected task identity. An indexer must not silently rebind artifacts from another task.

Dynamic evidence such as CI logs, review packets/results, session snapshots, model trials and final package evidence requires an explicit provenance adapter or metadata-valid ingestion path. The default repository scanner must not invent packet bindings, run IDs, role hashes or review-scope hashes.

## Authorization and freshness

`.terminus/agents/evidence_visibility.json` is the stage visibility contract. `.terminus/agents/retrieval_metadata.json` is the source/freshness contract. Role/packet allowed/excluded evidence may only narrow stage access.

A chunk is eligible only when all applicable conditions pass:

- source profile matches evidence class, sensitivity and `solver_visible` value;
- evidence class is required/allowed and not excluded;
- stage and canonical role applicability match;
- solver-visible-only stages receive only `solver_visible=true` chunks;
- task identity/commit matches for task-scoped sources;
- control-plane commit matches when declared;
- role-contract, packet, review-scope and CI-run bindings match when declared;
- policy-version bindings match when declared.

Missing required invocation bindings fail closed.

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

## Caching

The implementation has two safe caches:

- **embedding cache** keyed by chunk ID + provider + provider version + content hash;
- **retrieval-result cache** keyed by authority hash + query hash + current index source-set hash.

A retrieval cache stores chunk identities, not permission. Every cache hit is reloaded and re-authorized against the current invocation before use. Any stale/unauthorized chunk invalidates that cache hit.

Semantic reviewer verdicts are not cached by this retrieval engine. Review reuse remains governed exclusively by Protocol provenance/scope rules.

## Normal ChatGPT portability

The retrieval engine is an optimization and context-selection layer, not a required execution surface. Normal ChatGPT can continue the workflow by exact-reading the stage contract/policy files and authorized repository evidence through connected GitHub tools even when `.terminus/cache/retrieval.sqlite3` does not exist.

When a local checkout/Work/Codex execution surface is available, the same stage invocation may build/query the local index through:

```bash
python .terminus/retrieval/cli.py --root . build --task-path <task-path> --task-id <task-id>

python .terminus/retrieval/cli.py --root . context \
  --stage <STAGE_ID> \
  --role <CANONICAL_ROLE_ID> \
  --task-id <task-id> \
  --task-commit <sha> \
  --control-plane-commit <sha> \
  --query '<evidence question>'
```

Controllers must treat retrieval output as bounded evidence context, not as an authority source or PASS verdict.

## Agent integration

Before invoking a registered role, a controller should:

1. resolve the stage contract and canonical role;
2. exact-read mandatory policy/prompt files;
3. resolve packet/role evidence exclusions and freshness bindings;
4. use retrieval, when available, only for additional authorized evidence selection;
5. include retrieved chunk provenance in the invocation packet or handoff when material;
6. continue using direct exact reads when retrieval is unavailable or unnecessary.

Reviewers with packet-bound evidence remain packet-bound. The existence of an index never expands the packet.

## Failure behavior

Return/block rather than guess when:

- stage or role ID is unknown;
- required task/control-plane/packet/role freshness binding is missing;
- an indexed chunk contradicts its registered source profile;
- an index manifest is bound to the wrong task/control-plane commit;
- a solver-visible-only invocation would require a private/control-plane shadow source;
- a requested ranker would broaden an `EXACT_ONLY` or external-bound stage.
