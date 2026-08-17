# Human Writing Calibration Subsystem

This directory implements deterministic pre-task calibration for Terminus instruction writing and instruction review.

It is intentionally **not** a model-training data dump. External corpora remain external; Terminus stores the dataset registry, compact structural/preference summaries, deterministic selection logic and per-task calibration IDs.

## Files

- `dataset_registry.json` — enabled/disabled corpora, license metadata, role weights and sampling constraints.
- `seed_catalog.json` — compact generalized structural/preference cases; no long external source bodies.
- `calibration.py` — validates the corpus configuration and builds disjoint writer/reviewer study packs.
- `calibration_cli.py` — repository CLI used by A6/controller.
- `test_calibration.py` — isolated regression suite.

## Normal use

```bash
python .terminus/human_writing/calibration_cli.py --root . validate
python .terminus/human_writing/calibration_cli.py --root . plan \
  --task-id example-task \
  --domain 'kubernetes distributed systems recovery' \
  --output .terminus/research/example-task-dataset-calibration.json
```

A6 then satisfies the generated external sampling plan and writes generalized observations into its existing `TASK_WRITING_PROFILE`.

## Role split

The planner selects different local sample IDs for writer and reviewer. A6 must preserve disjointness for any external samples too.

Writer emphasis:

- real human technical information selection;
- natural grouping around engineering responsibilities;
- strict preservation of the approved requirement contract.

Reviewer emphasis:

- more chosen/rejected constraint comparisons;
- more anti-template contrasts;
- independent completeness-first judgment.

## External data

Do not commit raw external corpora here or inside task packages.

If a local runtime caches external samples, keep that cache outside Git or under an ignored machine-local path. Preserve source IDs and required attribution/license metadata. Source wording is calibration evidence, not a phrase bank.

The GitHub code-review corpus remains disabled until its current `license: other` metadata is resolved by an explicit provenance/license audit.
