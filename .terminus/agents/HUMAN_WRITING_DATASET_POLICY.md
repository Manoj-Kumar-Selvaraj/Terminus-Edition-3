# Dataset-Backed Human Writing Calibration Policy

Policy version: `1.1`

This policy specializes Terminus instruction writing and instruction review with a
reusable, provenance-aware calibration and measurement layer. It does **not**
authorize per-task model-weight fine-tuning, copying source prose into task
packages, or weakening correctness to sound more human.

## Objective

Before the Instruction Writer drafts and before the Instruction Reviewer judges,
each role receives a task-specific calibration pack derived from:

1. real human technical-writing signals;
2. explicit constraint-preservation preference pairs;
3. low-weight anti-template contrasts;
4. Terminus hard-positive/hard-negative reviewer cases;
5. the existing high-precision Terminus human-engineering corpus.

The writer and reviewer must use different sample IDs for the same task. Quality
is then measured after drafting/review so corpus choices can improve from evidence
rather than opinion.

## Canonical subsystem

Machine-readable policy lives under `.terminus/human_writing/`:

- `dataset_registry.json`
- `seed_catalog.json`
- `domain_profiles.json`
- `adapter_policy.json`
- `dataset_audits/`
- deterministic calibration/retrieval/evaluation/learning code and tests.

Raw external corpora are never committed. `.terminus/cache/` is the approved
machine-local cache boundary and is already ignored by Git.

## Enabled corpus roles

The current registry controls enablement and weights. The intended source roles are:

- `terminus-human-engineering` — high-precision local structural summaries of real
  engineering issues/change requests;
- `h4-stack-exchange-preferences` — primary external human technical-writing and
  preference source;
- `tulu3-constraint-preferences` — chosen/rejected constraint-preservation source;
- `human-like-dpo` — low-weight anti-template contrast only;
- `code-review-bench-human-annotations` — low-weight reviewer-only technical
  judgment source using expert/human annotation fields, not bot prose as a voice;
- `terminus-reviewer-hard-cases` — repository-authored hard positives and hard
  negatives for reviewer discrimination.

`github-human-codereview` remains disabled. Its current public dataset metadata
reports `license: other`; its README says source repositories are permissively
licensed and an older card revision declared MIT, but those signals are not
sufficiently consistent to enable the dataset automatically. The controlling audit
is `.terminus/human_writing/dataset_audits/github-human-codereview.json`.

## Mandatory calibration planning

For each task:

```bash
python .terminus/human_writing/calibration_cli.py --root . validate
python .terminus/human_writing/calibration_cli.py --root . plan \
  --task-id <task> \
  --domain "<technologies and engineering domain>" \
  --output .terminus/research/<task>-dataset-calibration.json
```

The pair binds:

- dataset-registry SHA-256;
- seed-catalog SHA-256;
- domain-profile SHA-256 and selected domain profile;
- one writer calibration ID;
- one reviewer calibration ID;
- disjoint local study sample IDs;
- role-specific external sampling targets and directives.

Missing IDs, mismatched hashes or non-empty writer/reviewer overlap invalidate
calibration.

## Domain-aware retrieval

`domain_profiles.json` provides broad engineering profiles such as SRE/incident,
platform/cloud, data migration, distributed systems, security, compiler/runtime and
application/backend.

Profiles influence which evidence is retrieved and which artifact types are useful.
They are **not** prose templates and may never prescribe sentence wording or
requirement ordering.

The local cache/retrieval layer is:

`.terminus/human_writing/corpus_cache.py`

It supports:

- dataset/license allow-list enforcement;
- domain/artifact/role metadata filters;
- deterministic lexical/domain ranking;
- optional precomputed vector similarity without requiring a vector dependency;
- writer/reviewer source-ID exclusions;
- source attribution checks when raw text is retained.

Task-time calibration packs receive source IDs and generalized observations. Raw
cached text is available only to contamination analysis or an explicitly
authorized offline evaluation/training job.

## Source-text contamination guard

Before final Instruction Reviewer acceptance, compare the proposed solver-visible
instruction against any raw external examples actually retained/read for that task.

Use `.terminus/human_writing/contamination.py` or:

```bash
python .terminus/human_writing/learning_cli.py --root . contamination-check ...
```

The guard reports source IDs and similarity scores only. It must not echo copied
phrases into reviewer output. A material similarity finding routes to rewrite.

Necessary shared technical vocabulary, absolute paths, protocol names and schema
terms are not by themselves evidence of copying; reviewers interpret scores in
context.

## Writer calibration

The writer receives only:

- writer calibration ID;
- manifest/profile hashes;
- writer-only sample/source IDs and generalized observations;
- task-specific information-selection profile;
- constraint-preservation and anti-template warnings;
- the approved solver-visible requirement contract.

Priority order is fixed:

1. preserve every material solver-visible requirement;
2. preserve technical precision, fairness and output/schema/path contracts;
3. select/group information like a real engineer in the applicable domain;
4. remove synthetic benchmark cadence and unnecessary explanation.

Naturalness never outranks #1 or #2.

## Reviewer calibration

The reviewer receives only:

- reviewer calibration ID;
- the same manifest/profile hashes;
- reviewer-only source/sample IDs and generalized observations;
- additional constraint-preference contrasts;
- hard-positive and hard-negative reviewer cases;
- solver-visible instruction/contracts plus only the discoverability summary
  authorized by the reviewer contract.

The reviewer must not see writer rationale or writer-only study examples before
fixing an independent verdict.

Hard positives prevent false positives such as rejecting a required exact schema,
required absolute paths, a legitimate 15–20-bullet work package, or precise formal
security language merely because it looks structured.

Hard negatives prevent false passes such as accepting concise natural prose that
silently drops restart, safety, authorization, output-path or schema requirements.

## Blind A/B effectiveness evaluation

The subsystem includes `.terminus/human_writing/evaluation.py`.

For calibration releases and sampled production tasks, compare:

- baseline/previous-policy instruction;
- dataset-calibrated instruction.

Variant identity is hidden from the blind evaluator until scores are fixed.

Required scoring dimensions include requirement completeness, technical precision,
human information selection, natural grouping, implementation distance, verbosity
fit, AI-template signal, synthetic completeness, rubric mirroring and
implementation leakage.

**Requirement completeness = 5/5 and technical precision >=4/5 are eligibility
gates.** A more natural but incomplete variant cannot win.

Do not turn blind A/B into a mandatory second full review on every task when the
task time budget is tight. Sample it during rollout, calibration-policy changes,
suspected regressions and enough normal tasks to estimate performance.

## Terminus-native preference evidence

`.terminus/human_writing/preference_store.py` records chosen/rejected evidence as:

- task and exact commit;
- chosen/rejected SHA-256;
- label source;
- reason codes;
- calibration pair ID;
- holdout eligibility.

The store intentionally does not place prior wording in the task-time calibration
surface. Exact historical content may be resolved only by an authorized offline
training/evaluation job from the recorded task/commit.

This prevents the Terminus-native corpus from becoming a phrase-copying or
originality-contamination bank.

## Effectiveness metrics and disagreement tracking

`.terminus/human_writing/learning_loop.py` records no-text per-task outcome data and
computes:

- initial/final instruction pass rate;
- average revision count;
- human-signal outcomes;
- LLMaJ writing-finding rate;
- blind A/B calibrated win rate;
- per-dataset task exposure and quality;
- Instruction Reviewer vs Human Quality Reviewer disagreement rate/classes.

Repeated disagreement is evidence to inspect calibration policy, not permission to
rerun reviewers until one agrees.

Dataset-weight changes are generated only as bounded recommendations after the
registry's minimum task count. Recommendations never mutate
`dataset_registry.json` automatically and require explicit approval.

## Controller telemetry hook

The Creation Controller records a no-text writing outcome when the instruction
artifact reaches a stable review point and refreshes/finalizes it after final human
quality / LLMaJ writing evidence is available.

At minimum record:

- exact task/commit and calibration IDs;
- draft/final content hashes, never prompt text in the telemetry record;
- material requirement count and completeness status;
- revision count;
- dataset/cache source counts by dataset;
- Instruction Reviewer and Human Quality Reviewer verdicts;
- human-signal assessment;
- contamination status;
- blind A/B result when sampled;
- LLMaJ writing finding when available;
- calibration time and writing/review time when available.

Use `learning_cli.py record-outcome`. If a revision clearly establishes a
chosen/rejected preference, also use `preference-add` so the Terminus-native
preference store grows without exposing historical wording to future task writers.

Telemetry collection is non-blocking for task correctness when the learning store
is unavailable, but the controller must not fabricate records or silently claim
metrics it did not capture.

## Future reusable adapter training

Per-task weight fine-tuning remains forbidden.

`adapter_policy.json` is fail-closed. A future writer/reviewer adapter can only
become a candidate after sufficient distinct tasks, preference pairs, holdouts,
blind A/B evidence and zero requirement-completeness regressions. Writer and
reviewer adapters remain separate.

Even when readiness is achieved, training/release requires explicit human approval
and a holdout evaluation. Adapters never replace per-task provenance/calibration.

## Required `TASK_WRITING_PROFILE` fields

A6's existing profile must include at least:

```text
DATASET_POLICY_VERSION: 1.1
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
EXTERNAL_DATASET_COVERAGE: FULL | DEGRADED
EXTERNAL_SOURCES_USED:
CACHE_SOURCES_USED:
HUMAN_INFORMATION_SELECTION_NOTES:
CONSTRAINT_PRESERVATION_NOTES:
ANTI_TEMPLATE_NOTES:
DO_NOT_IMITATE:
```

If raw source text was used, also record the source IDs needed for contamination
checking. Do not embed the raw source text in the profile.

## Time-budget behavior

Normal A6 calibration target remains **5–8 counted minutes**.

Use, in order:

1. deterministic local plan;
2. approved local cache/index;
3. bounded live retrieval only for missing domain diversity, novel artifact type,
   a specific prior failure mode, or insufficient evidence.

Do not automatically browse 20–40 fresh sources when the governed corpus/cache
already provides sufficient calibration.

Blind A/B, extended live research and weight analysis are optional/sampled
measurement work unless a policy release, regression or evidence gap makes them
necessary. They must respect the controller's 4-hour target / 5-hour hard limit.

## Non-negotiable invariants

- no material requirement is removed to improve human signal;
- writer and reviewer calibration samples are disjoint;
- disabled/unaudited corpora cannot contribute samples;
- source wording is evidence, never a phrase bank;
- raw source corpora and local cache are not committed/package-visible;
- hidden verifier/oracle evidence is never writing-training input;
- no invented incidents, typos, slang, customers, dates or business impact;
- contamination findings are handled before final instruction acceptance;
- prior Terminus wording is not projected into new writer prompts;
- empirical learning may recommend policy changes but cannot silently mutate them;
- if calibration evidence is missing/stale, stop or explicitly route a degraded
  evidence decision rather than pretending the agent was trained.
