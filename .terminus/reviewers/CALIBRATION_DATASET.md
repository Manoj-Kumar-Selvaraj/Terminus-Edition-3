# Reviewer Calibration Dataset Protocol

Dataset policy version: `1.0`

Purpose: grow reviewer accuracy from accumulated evidence without overfitting to one Harbor judge, one task domain, or superficial wording patterns.

This is an evaluation/calibration corpus, not model fine-tuning. The current chat/Custom GPT roles consume the examples as reviewer knowledge; an external agent runtime may later turn the same labeled cases into automated eval fixtures.

## Why this exists

A long list of “AI phrase -> human phrase” examples can make a reviewer brittle. It may learn that certain words are always bad, that shorter is always better, or that a familiar domain is automatically templated. Accuracy requires balanced examples where the same surface feature can be good or bad depending on context.

## Dataset units

Each calibration item has:

```text
CASE_ID:
DIMENSION: instruction | documentation | originality | verifier | difficulty | compliance | trajectory | adjudication
SOURCE: synthetic | public_reference | prior_local_task | Harbor | portal | human_review | difficulty_trajectory
PROVENANCE: <source/task/run/reference>
ARTIFACT_TYPE:
INPUT:
LABEL: PASS | REVISE | REJECT | INSUFFICIENT_EVIDENCE | <dimension-specific label>
SEVERITY: BLOCKER | HIGH | MEDIUM | LOW | NONE
RATIONALE:
CONTROLLING_EVIDENCE:
CONFUSABLE_WITH: <case ids with similar surface form but different label>
POLICY_VERSION:
```

Do not store secrets, hidden benchmark answers, or leaked private test content.

## Required data balance

For each semantic reviewer, maintain all four categories:

1. **positive examples** — genuine clean cases that should PASS;
2. **negative examples** — clear material defects;
3. **hard negatives** — text/tasks that look superficially clean but contain a real defect;
4. **hard positives** — cases that contain a suspicious surface signal but are legitimate in context.

Examples of hard positives:

- an instruction lists an exact schema because no other solver-visible interface defines it;
- a verifier inspects a generated artifact because absence of a secret literal is the actual requirement;
- two tasks share a payment domain and retry semantics but have genuinely different failure/verifier topology;
- documentation uses headings because the submission form explicitly requests Difficulty/Solution/Verification sections.

Without hard positives, reviewers become over-strict.

## Minimum corpus targets

These are growth targets, not submission gates.

### Initial useful corpus
- 20+ labeled instruction cases;
- 15+ documentation cases;
- 15+ originality cases;
- 20+ verifier cases;
- 10+ difficulty/trajectory cases;
- 10+ compliance/adjudication cases.

### Mature corpus
Aim for 40–60 cases per high-use semantic dimension, diversified across languages/domains/toolchains. Do not grow by duplicating the same pattern with noun swaps.

## Train/calibration vs holdout

Split cases conceptually:

- **calibration set**: reviewer prompt/example bank may reference generalized lessons from these cases;
- **regression holdout**: exact cases are not quoted in the reviewer prompt and are used to test whether the lesson generalizes.

When a new Harbor/portal miss occurs:

1. add the real miss or a safely generalized equivalent to the holdout/regression bank first;
2. change reviewer guidance using the generalized lesson;
3. evaluate on both the new case and unrelated old holdouts;
4. only then promote the new guidance.

This prevents “teaching to the test.”

## Provenance classes

### A. Authoritative/user rule evidence
Used for compliance/contract decisions. Highest local calibration priority.

### B. Harbor/portal/human review feedback
High-value evidence about actual acceptance judgments. Preserve the exact applicable task/version and whether the feedback was later overturned.

### C. Difficulty trajectories
High-value evidence for ambiguity, shortcuts and genuine reasoning walls. Include successful trajectories too; failures alone bias reviewers toward hardening.

### D. Public/golden tasks
Useful for diversity, realism and writing calibration. Never treat acceptance/public availability as proof that every detail matches current Edition 3 rules.

### E. Synthetic contrast cases
Useful for edge conditions and adversarial/hard-positive construction. Lower evidentiary weight than real acceptance/rejection history.

## Human-writing corpus rules

For Instruction/Documentation reviewers, do not label text “human” merely because it is informal or imperfect.

Label positive cases for:
- selective information;
- credible work context;
- concrete failure/request;
- natural grouping of related constraints;
- evidence-backed technical specificity;
- no rubric mirroring;
- no unnecessary implementation walkthrough.

Label negative cases for:
- synthetic completeness;
- one-sentence-per-test cadence;
- generic professional filler;
- copied benchmark/task structure;
- excessive justification;
- over-prescription;
- schema/interface dumping when already discoverable;
- unsupported claims.

Include human-written-but-bad examples and AI-written-but-technically-good examples where possible. The reviewer’s job is artifact quality, not authorship detection.

## Originality corpus rules

Compare on multiple axes rather than wording alone:

- phrase similarity;
- requirement ordering;
- failure topology;
- verifier scenario topology;
- solution architecture;
- domain/provenance.

Include hard positives with high lexical overlap but distinct topology, and hard negatives with low lexical overlap but structurally cloned topology.

## Reviewer calibration record

For each reviewer-policy release record:

```text
REVIEWER:
POLICY_VERSION:
CALIBRATION_CASE_COUNT:
HOLDOUT_CASE_COUNT:
DOMAINS represented:
KNOWN_FALSE_POSITIVES:
KNOWN_FALSE_NEGATIVES:
REGRESSION_EVAL_RESULT:
APPROVAL:
```

## Data hygiene

- Remove/abstract secret values and private identifiers.
- Do not copy hidden solution/test content into solver-visible writing packs.
- Do not add a public task example merely because it supports the desired conclusion; sample diverse outcomes.
- Record superseded/overturned feedback rather than silently deleting it.
- Version generalized lessons so a future reviewer can understand why a rule exists.

## Current sources

The initial corpus is distributed across:

- `HUMAN_WRITING_CALIBRATION.md`
- `WRITING_EXAMPLE_BANK.md`
- `REVIEWER_EVALS.md`
- `LLMAJ_LEARNING_LOG.md`
- `.terminus/GOLDEN_TASKS.md`

Future growth should prefer labeled cases following this protocol over adding unstructured prose to prompts.
