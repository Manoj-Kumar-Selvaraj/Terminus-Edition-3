# Dataset-Backed Human Writing Calibration Policy

Policy version: `1.0`

This policy specializes Terminus instruction writing and instruction review with a reusable, provenance-aware calibration layer. It does **not** authorize per-task model-weight fine-tuning, downloading arbitrary corpora into task packages, copying source prose, or weakening correctness to sound more human.

## Objective

Before the Instruction Writer drafts and before the Instruction Reviewer judges, each role must receive a task-specific calibration pack derived from:

1. real human technical writing signals;
2. explicit constraint-preservation preference pairs;
3. low-weight anti-template contrasts;
4. the existing high-precision Terminus human-engineering corpus.

The writer and reviewer must use **different sample IDs** for the same task so the reviewer is not merely checking whether the writer reproduced its own examples.

## Canonical dataset registry

The machine-readable registry is:

`.terminus/human_writing/dataset_registry.json`

The current enabled sources are:

- `terminus-human-engineering` — local structural summaries derived from the curated public engineering issue corpus;
- `h4-stack-exchange-preferences` — primary external human technical preference source;
- `tulu3-constraint-preferences` — constraint-preservation/chosen-vs-rejected source;
- `human-like-dpo` — low-weight anti-template contrast source only.

`github-human-codereview` is intentionally disabled until its current `license: other` metadata receives a repository-level provenance/license audit.

Dataset weights are calibration weights, not permission to blend source wording. The human voice target comes primarily from genuinely human technical material; synthetic preference corpora teach constraints and anti-patterns.

## Why retrieval calibration instead of per-task fine-tuning

Terminus tasks operate under a 3–5 hour execution budget. Re-training model weights before each task is too expensive, hard to reproduce, and unnecessary for the writing objective.

The mandatory mechanism is therefore:

`versioned corpus -> deterministic task/domain selection -> A6 structural synthesis -> writer/reviewer calibration packs -> role execution`

An external runtime may later train reusable adapters from the same governed corpus, but those adapters must be versioned and evaluated separately. Their existence never replaces the per-task calibration/provenance gate.

## Deterministic planner

Use:

```bash
python .terminus/human_writing/calibration_cli.py --root . validate
python .terminus/human_writing/calibration_cli.py --root . plan \
  --task-id <task> \
  --domain "<technologies and engineering domain>" \
  --output .terminus/research/<task>-dataset-calibration.json
```

The resulting pair contains:

- dataset registry SHA-256;
- compact seed-catalog SHA-256;
- one `WRITER_CALIBRATION_ID`;
- one `REVIEWER_CALIBRATION_ID`;
- disjoint local study sample IDs;
- external dataset sampling targets;
- role-specific directives.

The planner does not download raw external data. External samples are gathered or read from an approved local cache by the Human Writing Researcher and recorded by source/sample ID plus structural observation.

## A6 Human Writing Research requirements

A6 must begin by producing the deterministic calibration pair for the task/domain.

A6 then satisfies the external sampling plan using the enabled datasets when accessible. Record only what is needed for calibration:

- dataset ID;
- source/sample ID or URL;
- domain relevance;
- structural/preference observation;
- whether any wording was copied (`false` must be recorded for task-writing use).

Do not place bulk dataset text in the repository or task package.

If an external dataset is temporarily inaccessible, A6 may use the local high-precision corpus plus fresh public engineering sources, but must record `EXTERNAL_DATASET_COVERAGE: DEGRADED` and the missing source. The writer may proceed only when the controller accepts that degraded evidence under the task time/evidence policy; it must never be silently treated as full dataset coverage.

## Writer calibration

Before drafting, the Instruction Writer must receive only the writer calibration projection:

- `WRITER_CALIBRATION_ID`;
- dataset manifest/catalog hashes;
- writer-only sample IDs and generalized observations;
- task-specific information-selection profile;
- constraint-preservation warnings;
- anti-template warnings;
- solver-visible requirement contract.

The writer must **not** receive reviewer-only sample IDs, reviewer rationale, or a suggested final sentence bank.

Writer priority order:

1. preserve every material solver-visible requirement;
2. preserve technical precision and fairness;
3. select/group information like a real engineer;
4. remove synthetic benchmark cadence and unnecessary explanation.

Naturalness never outranks #1 or #2.

## Reviewer calibration

Before cold review, the Instruction Reviewer must receive only the reviewer calibration projection:

- `REVIEWER_CALIBRATION_ID`;
- same dataset manifest/catalog hashes as the writer's task pair;
- reviewer-only sample IDs and generalized observations;
- extra chosen/rejected constraint comparisons;
- extra anti-template contrasts;
- solver-visible instruction and legitimate referenced contracts;
- requirement/test discoverability summary allowed by the reviewer contract.

The reviewer must not see writer rationale or writer-only study samples before fixing its independent verdict.

The reviewer judges artifact quality, not authorship. It must reject both of these failure modes:

- natural-sounding but incomplete/unsafe instruction;
- technically complete but synthetic hidden-test/rubric prose.

## Dataset-specific interpretation

### H4 Stack Exchange Preferences

Use as the main external human technical source. Learn information selection, problem framing, evidence placement, shared-context assumptions, and preference for useful technical explanation.

Do not copy distinctive wording. When source text is retained outside transient calibration, preserve CC-BY-SA attribution/provenance requirements.

### Tulu-3 constraint preferences

Use to learn that relaxing one constraint can make an otherwise fluent answer invalid. Its purpose is requirement preservation and reviewer discrimination, not human voice imitation.

### Human-Like-DPO

Use only to recognize mechanical assistant patterns and overcorrection. Never imitate emojis, fabricated personal experience, casual persona, or conversational filler in an engineering ticket.

### Terminus human-engineering corpus

Use as the highest-precision local anchor because its structural summaries were selected specifically for engineering incidents/change requests and do not vendor long public issue bodies.

## Required `TASK_WRITING_PROFILE` calibration fields

A6's existing `TASK_WRITING_PROFILE` must include at least:

```text
DATASET_POLICY_VERSION: 1.0
DATASET_REGISTRY_SHA256:
SEED_CATALOG_SHA256:
CALIBRATION_PAIR_ID:
WRITER_CALIBRATION_ID:
REVIEWER_CALIBRATION_ID:
WRITER_SAMPLE_IDS:
REVIEWER_SAMPLE_IDS:
WRITER_REVIEWER_SAMPLE_OVERLAP: []
EXTERNAL_DATASET_COVERAGE: FULL | DEGRADED
EXTERNAL_SOURCES_USED:
HUMAN_INFORMATION_SELECTION_NOTES:
CONSTRAINT_PRESERVATION_NOTES:
ANTI_TEMPLATE_NOTES:
DO_NOT_IMITATE:
```

Missing IDs, mismatched hashes, or non-empty writer/reviewer overlap make the calibration stale/invalid.

## Time-budget behavior

Dataset calibration is intentionally bounded. Normal target for A6 dataset calibration is **5–8 counted minutes**.

Use the local deterministic plan and existing governed corpus first. Fetch more live examples only when:

- the domain is poorly represented;
- the task uses a novel engineering artifact type;
- a prior human/LLMaJ finding identified a specific writing failure;
- source diversity is otherwise insufficient.

Do not spend 20–40-source live-research time automatically on every task when the governed dataset/index already supplies adequate calibration.

## Learning loop

After accepted/rejected Terminus tasks accumulate, add safely generalized labeled pairs to the local calibration/holdout system. Over time, in-domain Terminus preference evidence should carry more weight than generic external style corpora.

Do not promote one reviewer phrase or one task's wording into a universal rule. Preserve hard positives and hard negatives so the reviewer learns context rather than banned-word heuristics.

## Non-negotiable invariants

- no material requirement may be removed to increase human signal;
- writer and reviewer calibration samples must be disjoint;
- disabled/unlicensed corpora cannot contribute samples;
- source wording is evidence, not a phrase bank;
- task packages contain no external training corpus;
- hidden verifier/oracle evidence is never used as writing-training input;
- dataset calibration does not authorize invented incidents, typos, slang, emotions, customers, dates, or impact;
- if calibration evidence is missing/stale, stop or explicitly route a degraded-evidence decision rather than pretending the agent was trained.
