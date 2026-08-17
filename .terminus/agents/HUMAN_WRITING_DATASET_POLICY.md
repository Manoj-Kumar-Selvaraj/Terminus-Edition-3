# Dataset-Backed Human Writing Calibration Policy

Policy version: `1.2`

This policy specializes Terminus instruction writing and instruction review with a
provenance-aware calibration, evaluation and learning layer. It does **not**
authorize per-task model-weight fine-tuning, copying source prose into task
packages, or weakening correctness to sound more human.

## Governing priority

1. preserve every material solver-visible requirement;
2. preserve technical precision, fairness, safety, output/schema/path contracts;
3. select and group information like a real engineer in the applicable domain;
4. remove synthetic benchmark cadence and unnecessary explanation.

Naturalness never outranks #1 or #2.

## Canonical implementation

Machine-readable policy lives under `.terminus/human_writing/`:

- `dataset_registry.json` — dataset enablement, role permissions, weights,
  provenance and cache policy;
- `seed_catalog.json` — compact generalized human/preference/hard-case signals;
- `domain_profiles.json` — domain retrieval profiles;
- `adapter_policy.json` — fail-closed future adapter gate;
- `dataset_audits/` — explicit source/license decisions;
- `calibration.py` / `validate_calibration.py` — deterministic planner and validator;
- `corpus_cache.py` / `materialize.py` — approved local retrieval/materialization;
- `contamination.py` — source-copy guard;
- `evaluation.py` — blind independent A/B evaluation;
- `preference_store.py` / `learning_loop.py` — durable no-text learning evidence.

The execution specialization is
`.terminus/agents/human_writing_stage_overlay.json`. `RetrievalPolicy` applies that
overlay before building stage invocations. The effective A6 status contract is:

`CALIBRATION_READY | INSUFFICIENT_SOURCE_DIVERSITY | SOURCE_QUALITY_BLOCKED | BLOCKED`

`INSTRUCTION_DRAFT` requires `VALIDATED_HUMAN_WRITING_CALIBRATION`.

## Dataset roles

The registry is authoritative. A dataset may be consumed only by a role listed in
its `allowed_roles` field. Role authorization is enforced both during cache ingest
and retrieval; caller-provided `role_signal` cannot promote reviewer-only evidence
into writer evidence.

Current roles:

- `terminus-human-engineering` — writer + reviewer high-precision local anchor;
- `h4-stack-exchange-preferences` — writer + reviewer primary real-human technical
  signal;
- `tulu3-constraint-preferences` — writer + reviewer constraint-preservation signal;
- `human-like-dpo` — low-weight writer/reviewer anti-template contrast only;
- `code-review-bench-human-annotations` — **reviewer only**;
- `terminus-reviewer-hard-cases` — **reviewer only**;
- `github-human-codereview` — disabled pending a clean license/provenance decision.

Disabled or unaudited corpora cannot contribute samples, cache rows or weight.

## Calibration planning

For each task:

```bash
python .terminus/human_writing/calibration_cli.py --root . validate
python .terminus/human_writing/calibration_cli.py --root . plan \
  --task-id <task> \
  --domain "<technologies and engineering domain>" \
  --output .terminus/research/<task>-dataset-calibration.json
```

The pair binds current registry/catalog/domain-profile hashes, one writer
calibration ID, one reviewer calibration ID, disjoint local samples, role-specific
external targets and directives.

The planner may blend up to two materially matching domain profiles. The first is
the primary profile; the second exists only when it has meaningful token overlap.
Profiles influence evidence selection and artifact types, never sentence templates.

## Reproducible external materialization

Raw external corpora are never committed. `.terminus/cache/` is the ignored local
boundary.

Approved external snapshots are materialized through:

```bash
python .terminus/human_writing/materialize_cli.py --root . \
  --dataset-id <enabled-dataset> \
  --input <normalized-jsonl-snapshot> \
  --source-revision <exact-source-revision> \
  --role-signal writer|reviewer|both
```

A materialization records:

- dataset ID and exact source revision;
- role scope;
- normalized input SHA-256;
- source-ID-set SHA-256;
- cache/registry schema versions;
- a local materialization ID/manifest.

The normalized rows must satisfy dataset-specific provenance and retained-text
requirements from `dataset_registry.json`. A missing source revision or required
attribution field is a hard error.

## Cache and retrieval

`corpus_cache.py` enforces:

- dataset enablement;
- dataset role permissions at ingest and search;
- dataset-specific provenance/retained-text requirements;
- writer/reviewer source exclusions;
- minimum relevance score;
- bounded candidate prefiltering;
- FTS5 prefilter when available, with bounded fallback;
- no raw text in search results.

A sparse cache must return no evidence rather than unrelated zero-score rows.

Normal A6 retrieval order:

1. deterministic local calibration pack;
2. approved local cache/index;
3. bounded live retrieval only for missing domain/artifact diversity, inaccessible
   enabled sources, or a specific observed writing failure.

Do not automatically research 20–40 fresh sources for every task.

## Writer/reviewer independence

Writer and reviewer local sample IDs and external source IDs must be disjoint for
the task. The reviewer does not receive writer rationale or writer-only examples
before fixing its independent verdict.

Writer receives only its calibration ID, manifest/profile hashes, writer-only
source/sample IDs/generalized observations, requirement-preservation warnings and
the approved solver-visible requirement contract.

Reviewer receives its own calibration ID, reviewer-only evidence, extra constraint
contrasts and hard positives/negatives. Structured precision is not a defect when
required; natural prose is not a pass when it omits material semantics.

## Deterministic calibration validation

Before instruction drafting, run:

```bash
python .terminus/human_writing/validate_calibration.py --root . \
  --pair .terminus/research/<task>-dataset-calibration.json \
  --profile .terminus/research/<task>-task-writing-profile.json
```

The validator checks the effective A6/A7 contract, current registry/catalog/profile
hashes, calibration IDs, writer/reviewer disjointness, external-source disjointness,
coverage state and explicit approval for degraded coverage.

A6's `TASK_WRITING_PROFILE` must contain at least:

```text
DATASET_POLICY_VERSION: 1.2
DATASET_REGISTRY_SHA256:
SEED_CATALOG_SHA256:
DOMAIN_PROFILES_SHA256:
DOMAIN_PROFILE:
CALIBRATION_PAIR_ID:
WRITER_CALIBRATION_ID:
REVIEWER_CALIBRATION_ID:
WRITER_SAMPLE_IDS:
REVIEWER_SAMPLE_IDS:
WRITER_REVIEWER_SAMPLE_OVERLAP: []
WRITER_EXTERNAL_SOURCE_KEYS:
REVIEWER_EXTERNAL_SOURCE_KEYS:
EXTERNAL_DATASET_COVERAGE: FULL | DEGRADED
CACHE_SOURCE_KEYS_USED:
RAW_SOURCE_KEYS_USED_FOR_CONTAMINATION:
HUMAN_INFORMATION_SELECTION_NOTES:
CONSTRAINT_PRESERVATION_NOTES:
ANTI_TEMPLATE_NOTES:
DO_NOT_IMITATE:
```

`DEGRADED` requires a recorded controller approval with `approved=true`,
`approved_by` and `reason`. Silent degraded coverage is invalid.

## Source-text contamination guard

Before final Instruction Reviewer acceptance, run the contamination guard against
retained raw examples used by the task. `learning_cli.py contamination-check
--profile ...` automatically derives the retained source set from
`CACHE_SOURCE_KEYS_USED`; callers do not have to remember every source key.

The guard uses n-gram containment, whole-document similarity, local-window
similarity and longest contiguous token match. This is intentionally able to catch
a copied paragraph embedded inside a much longer source. Findings expose only
source IDs and scores, never copied phrases.

If no raw text was retained/read, record `SKIPPED_NO_RAW_TEXT` rather than pretending
a comparison occurred.

## Blind A/B effectiveness evaluation

Blind A/B is sampled for policy releases, rollout measurement and suspected
regressions; it is not a mandatory second full review on every time-constrained
task.

The writer identity is sealed when the A/B packet is created. Scoring requires an
allowed evaluator role and a different evaluator identity. Self-evaluation is
rejected.

A variant is eligible only when:

- requirement completeness = 5/5;
- technical precision >= 4/5;
- rubric mirroring <= 1/5;
- implementation leakage <= 1/5;
- AI-template signal <= 2/5.

A natural but incomplete/leaky variant cannot win.

## Durable Terminus-native learning

No-text learning is stored in the committable knowledge area:

- `.terminus/learning/knowledge/human-writing-outcomes.jsonl`
- `.terminus/learning/knowledge/human-writing-preferences.jsonl`

Do not store prior instruction wording in these files.

Preference records contain chosen/rejected hashes, label source/reason codes,
calibration pair and holdout eligibility. Before append, the chosen text must hash
to the actual `<task>/instruction.md` at the exact recorded task commit. Holdout
preferences require an independent label source and `requirements_preserved`.

Outcome telemetry is also provenance-bound. It requires exact task commit/domain,
current deterministic calibration IDs, accepted instruction hash matching the task
commit, explicit requirement-regression boolean, contamination status, reviewer
evidence reference and known enabled dataset IDs. Prohibited text fields are
rejected recursively, including nested objects.

## Metrics and dataset weighting

Exposure correlation is descriptive only. A task's overall quality is **not**
credited causally to every dataset it happened to use.

Weight recommendations require:

- the registry minimum number of distinct tasks;
- the configured minimum controlled ablation observations for **every active dataset
  in that role**;
- per-observation `controlled=true`, role and bounded `quality_delta`.

Without sufficient controlled attribution the result is
`INSUFFICIENT_ATTRIBUTION`. Recommendations are bounded, never mutate the registry
automatically and require explicit approval.

Reviewer disagreement is tracked as calibration evidence. It is not permission to
rerun reviewers until one agrees.

## Future adapters

Per-task fine-tuning remains forbidden.

Adapter readiness counts real bound preference-store records and bound holdout
records, not mere inequality between draft/final hashes. Every recorded task must
explicitly show no requirement regression. Blind A/B performance must meet the
policy threshold.

While `adapter_policy.enabled=false`, readiness status is `DISABLED` regardless of
other metrics. Enabling/training/releasing an adapter always requires explicit human
approval and separate writer/reviewer adapters.

## Time budget

Normal A6 calibration target remains **5–8 counted minutes**. Materialization is a
reusable/offline cache-building operation and should not consume every task's A6
budget. Blind A/B and controlled dataset ablations are sampled measurement work.
All task-time work remains subordinate to the controller's 4-hour target / 5-hour
hard limit and explicit time-extension mechanism.

## Non-negotiable invariants

- no material requirement is removed to improve human signal;
- writer/reviewer calibration evidence is disjoint;
- dataset role permissions are mechanically enforced;
- disabled/unaudited corpora cannot contribute evidence;
- source wording is evidence, never a phrase bank;
- raw source corpora/cache are not committed or task-package-visible;
- hidden verifier/oracle evidence is never writing-training input;
- no invented incidents, typos, slang, customers, dates or business impact;
- contamination is resolved before final acceptance when raw evidence exists;
- prior Terminus wording is never projected into new task-time writer prompts;
- learning records are no-text and provenance-bound;
- empirical learning can recommend policy changes but cannot silently apply them;
- missing/stale calibration blocks or explicitly routes a degraded-evidence decision.
