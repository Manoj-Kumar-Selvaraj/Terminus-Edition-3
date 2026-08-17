# Human Writing Calibration and Learning Subsystem

This directory implements deterministic, dataset-backed calibration for Terminus
instruction writing/review plus a provenance-bound learning loop.

It is intentionally **not** a model-training data dump. External corpora remain
external. Raw source text may exist only in the ignored local cache used for
retrieval and contamination checks.

## Core components

- `dataset_registry.json` — enabled datasets, licenses, role permissions, weights,
  provenance requirements, retrieval floor and attribution policy.
- `dataset_audits/` — explicit enable/hold decisions for external sources.
- `seed_catalog.json` — generalized human/constraint/anti-template/hard-case signals.
- `domain_profiles.json` — deterministic primary/secondary domain retrieval profiles.
- `calibration.py` / `calibration_cli.py` — disjoint writer/reviewer planning.
- `validate_calibration.py` — fail-closed effective-stage and task calibration check.
- `corpus_cache.py` — ignored SQLite/FTS cache with bounded policy-aware retrieval.
- `materialize.py` / `materialize_cli.py` — revision-bound reproducible cache builds.
- `contamination.py` — partial/whole source-copy detection without phrase echoing.
- `evaluation.py` — blind independent A/B evaluation with hard eligibility gates.
- `preference_store.py` — bound chosen/rejected hash references.
- `learning_loop.py` / `learning_cli.py` — durable no-text outcome metrics,
  disagreement tracking, controlled-ablation weight recommendations and adapter
  readiness.
- `adapter_policy.json` — disabled/fail-closed future adapter policy.
- `test_calibration.py` / `test_learning_loop.py` — regression suites.

The canonical A6/A7 specialization is
`.terminus/agents/human_writing_stage_overlay.json`; the real `RetrievalPolicy`
loader applies it before stage invocations are built.

## Plan and validate calibration

```bash
python .terminus/human_writing/calibration_cli.py --root . validate
python .terminus/human_writing/validate_calibration.py --root .
python .terminus/human_writing/calibration_cli.py --root . plan \
  --task-id example-task \
  --domain 'kubernetes distributed systems recovery' \
  --output .terminus/research/example-task-dataset-calibration.json
```

After A6 creates the task profile:

```bash
python .terminus/human_writing/validate_calibration.py --root . \
  --pair .terminus/research/example-task-dataset-calibration.json \
  --profile .terminus/research/example-task-task-writing-profile.json
```

A7 must receive `VALIDATED_HUMAN_WRITING_CALIBRATION`; it must not proceed from a
merely documented/unvalidated profile.

## Materialize approved external data

Build the ignored local cache from a normalized snapshot with an exact revision:

```bash
python .terminus/human_writing/materialize_cli.py --root . \
  --dataset-id tulu3-constraint-preferences \
  --input /path/to/normalized.jsonl \
  --source-revision <exact-revision> \
  --role-signal writer
```

The manifest binds dataset, role, source revision, normalized input SHA-256 and
source-ID digest. Dataset role/provenance/retained-text requirements are enforced by
the cache; reviewer-only data cannot be promoted into writer evidence.

## Retrieve evidence

```bash
python .terminus/human_writing/learning_cli.py --root . cache-search \
  --query 'terraform migration recovery' \
  --role-signal writer
```

Retrieval uses a relevance floor and bounded FTS/SQL candidate set. Sparse caches
return no evidence rather than unrelated zero-score rows. Search results never
contain retained source text.

## Contamination guard

Use the validated task profile rather than manually remembering source keys:

```bash
python .terminus/human_writing/learning_cli.py --root . contamination-check \
  --draft <task>/instruction.md \
  --profile .terminus/research/<task>-task-writing-profile.json
```

The guard automatically checks retained cache sources used by the profile. It can
detect copied subsections inside long source documents and reports only source IDs
and similarity measures. With no retained raw text it returns
`SKIPPED_NO_RAW_TEXT`.

## Blind A/B evaluation

```bash
python .terminus/human_writing/learning_cli.py --root . ab-prepare \
  --task-id example-task \
  --baseline /tmp/baseline.md \
  --calibrated /tmp/calibrated.md \
  --writer-actor-id writer-run-123 \
  --requirement-contract-sha256 <sha256> \
  --output /tmp/ab-public.json \
  --sealed-mapping-output /tmp/ab-mapping.json
```

Scoring requires a different evaluator identity and an approved evaluator role.
Completeness/precision are hard gates; material rubric mirroring, implementation
leakage or excessive AI-template signal also makes a variant ineligible.

## Durable learning

No-text learning is intentionally committed under:

- `.terminus/learning/knowledge/human-writing-outcomes.jsonl`
- `.terminus/learning/knowledge/human-writing-preferences.jsonl`

Outcome records bind the exact task commit, accepted instruction hash, deterministic
calibration IDs and reviewer evidence. Preference records bind the chosen hash to
the actual `instruction.md` at the exact task commit. Historical wording is not
stored in these JSONL files and is never projected into a new task-time writer pack.

Dataset exposure metrics are descriptive only. Dataset weight recommendations
require sufficient controlled per-dataset ablation observations and explicit human
approval; recommendations never change `dataset_registry.json` automatically.

## Future adapters

Per-task fine-tuning is forbidden. `adapter_policy.json` remains disabled. Adapter
readiness counts real bound preferences/holdouts and explicit zero-regression task
outcomes. A disabled policy always reports `DISABLED`; any future training/release
requires a separate human approval and separate writer/reviewer adapters.
