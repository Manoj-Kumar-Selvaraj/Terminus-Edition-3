# Human Writing Calibration and Learning Subsystem

This directory implements deterministic, dataset-backed calibration for Terminus
instruction writing/review plus the measured learning loop that evaluates whether
calibration actually improves artifact quality.

It is intentionally **not** a model-training data dump. External corpora remain
external. Raw source text may exist only in the ignored local cache used for
retrieval and contamination checks.

## Components

- `dataset_registry.json` — governed corpora, licenses, weights, audit state and
  empirical-weight policy.
- `dataset_audits/` — explicit enable/hold decisions for ambiguous sources.
- `seed_catalog.json` — generalized local human/constraint/anti-template and
  hard-positive/hard-negative calibration cases.
- `domain_profiles.json` — task-domain profiles used to bias retrieval without
  turning prose into templates.
- `calibration.py` / `calibration_cli.py` — deterministic disjoint
  writer/reviewer calibration planning.
- `corpus_cache.py` — ignored SQLite cache with metadata filtering and optional
  vector scoring. Task-time packs receive summaries/IDs, not raw text.
- `contamination.py` — lexical similarity guard that reports source IDs/scores
  without echoing copied phrases.
- `evaluation.py` — blind A/B packet generation and completeness-gated scoring.
- `preference_store.py` — Terminus-native chosen/rejected references stored as
  hashes plus provenance, never prior wording in task-time prompts.
- `learning_loop.py` / `learning_cli.py` — outcome metrics, reviewer disagreement,
  bounded dataset-weight recommendations and adapter-readiness gating.
- `adapter_policy.json` — fail-closed requirements for any future reusable
  writer/reviewer adapters.
- `test_calibration.py` / `test_learning_loop.py` — isolated regression suites.

## Normal calibration

```bash
python .terminus/human_writing/calibration_cli.py --root . validate
python .terminus/human_writing/calibration_cli.py --root . plan \
  --task-id example-task \
  --domain 'kubernetes distributed systems recovery' \
  --output .terminus/research/example-task-dataset-calibration.json
```

A6 first uses the local governed catalog/cache, then performs live retrieval only
when the domain/profile or evidence budget requires it.

## Local cache

`.terminus/cache/` is ignored by Git. Ingest only approved records:

```bash
python .terminus/human_writing/learning_cli.py --root . cache-ingest \
  --input /tmp/human-writing-records.jsonl

python .terminus/human_writing/learning_cli.py --root . cache-search \
  --query 'terraform migration recovery' \
  --role-signal writer
```

Source text retained for contamination analysis must carry the applicable
license/provenance fields. Stack Exchange text additionally requires author
attribution metadata.

## Blind A/B evaluation

For a controlled evaluation, prepare a baseline and calibrated variant:

```bash
python .terminus/human_writing/learning_cli.py --root . ab-prepare \
  --task-id example-task \
  --baseline /tmp/baseline.md \
  --calibrated /tmp/calibrated.md \
  --requirement-contract-sha256 <sha256> \
  --output /tmp/ab-public.json \
  --sealed-mapping-output /tmp/ab-mapping.json
```

The evaluator sees only the public packet. Requirement completeness and technical
precision are hard eligibility gates before human-style preference can win.

## Learning and future adapters

Per-task outcome/preference state is stored beneath `.terminus/learning/state/`,
which is already ignored. Durable repository changes should contain only
approved aggregate policy/metrics, never a source-text or prior-instruction phrase
bank.

Dataset-weight changes are recommendations only and require explicit approval.
Per-task fine-tuning is forbidden. Any future reusable adapter remains disabled
until `adapter_policy.json` readiness gates pass and a human explicitly approves
the release.
