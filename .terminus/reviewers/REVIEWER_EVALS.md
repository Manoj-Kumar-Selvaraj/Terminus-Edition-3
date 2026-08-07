# Reviewer Regression Evaluation Suite

Purpose: evaluate the Terminus reviewers themselves. Reviewer prompts are production logic; they need regression tests just like task verifiers.

Policy version: `1.0`

## Principles

- Keep a small set of labeled micro-cases plus real historical misses.
- Test both **misses** and **false positives**. A reviewer that flags everything is not accurate.
- Evaluate narrow dimensions separately; do not ask one evaluator to score every reviewer property at once.
- Record the reviewer-policy version and model/config used for each evaluation.
- Prefer repeated trials for semantic reviewers because one sample is not a reliable estimate.
- A reviewer prompt/calibration change must run this suite before being treated as the new default policy.

## Metrics

Track per reviewer:

- `blocking_recall`: proportion of known BLOCKER/HIGH cases correctly caught;
- `blocking_precision`: proportion of BLOCKER/HIGH findings that are actually blocking in the labeled set;
- `pass_precision`: proportion of reviewer PASS verdicts that are correct;
- `insufficient_evidence_accuracy`: whether ambiguous cases use INSUFFICIENT_EVIDENCE instead of guessing;
- `evidence_grounding_rate`: findings with valid evidence references;
- `scope_discipline`: findings that stay inside the reviewer’s owned dimension;
- `stability`: verdict consistency across repeated runs when inputs are unchanged.

Do not collapse all metrics into one number for go/no-go decisions.

## Minimum acceptance for a reviewer-policy change

Before adopting a materially changed reviewer prompt:

- no known BLOCKER case in the regression bank is missed in all repeated trials;
- no known clean PASS case is consistently converted into BLOCKER/HIGH;
- evidence grounding remains mandatory;
- ambiguous cases demonstrate the INSUFFICIENT_EVIDENCE path;
- output parses against the role schema.

## Seed cases

These are conceptual cases. When implemented as automated evals, store exact fixtures under a non-task `.terminus/reviewer_evals/` location so they never enter task ZIPs.

### IR-01 — concise genuine incident

OWNER: Instruction Reviewer
LABEL: PASS

```text
The API deploy is healthy on a clean start, but after a certificate rotation the first restart can come up with the old trust bundle. Fix the startup path so a fresh container always uses the current bundle. Do not change the public TLS endpoint or the health-check contract.
```

Expected: high human signal, low template signal, no forced rewrite.

### IR-02 — synthetic completeness

OWNER: Instruction Reviewer
LABEL: REVISE

```text
In this task, you are required to update the system so that it validates the certificate, refreshes the trust store, verifies the endpoint, maintains backward compatibility, preserves availability, handles errors gracefully, logs all relevant events, and ensures robust and reliable operation across various edge cases.
```

Expected: synthetic completeness, generic filler, weak observable contract.

### IR-03 — legitimate exact schema

OWNER: Instruction Reviewer
LABEL: PASS

Scenario: a task whose entire contract is a new JSON protocol and no referenced interface file exists. The instruction lists the required five JSON fields and their types.

Expected: do **not** flag schema listing merely because fields are explicit. Concision is contextual.

### IR-04 — missing evidence

OWNER: Instruction Reviewer
LABEL: INSUFFICIENT_EVIDENCE

Scenario: instruction says “preserve the output schema defined in the contract,” but the reviewer is not given the contract.

Expected: request the contract; do not PASS or claim ambiguity without seeing it.

### VR-01 — source-grep verifier

OWNER: Verifier Engineer
LABEL: REVISE

Scenario: requirement is “service rejects unauthenticated requests”; verifier only greps config for `auth_required=true`.

Expected: HIGH functional-verification finding.

### VR-02 — necessary source inspection

OWNER: Verifier Engineer
LABEL: PASS

Scenario: requirement explicitly mandates that a secret literal must not appear in a generated configuration artifact and runtime behavior cannot establish the absence reliably.

Expected: source/artifact inspection can be valid when it directly measures the stated outcome. Do not apply “no grep” mechanically.

### VR-03 — phantom requirement

OWNER: Verifier Engineer
LABEL: REVISE

Scenario: tests require gzip compression but no solver-visible instruction/interface requires it.

Expected: HIGH phantom-spec finding.

### OR-01 — same domain, different topology

OWNER: Originality & Authenticity Reviewer
LABEL: PASS

Scenario: two payment tasks share words such as payment/retry/idempotency but one is worker notification startup and the other is COBOL EOD reservation/clearing reconciliation.

Expected: low duplicate risk; thematic overlap is insufficient.

### OR-02 — renamed clone

OWNER: Originality & Authenticity Reviewer
LABEL: REJECT

Scenario: requirement ordering, failure sequence, verifier cases and solution structure are identical to a reference task with only service/entity names changed.

Expected: HIGH duplicate risk.

### OR-03 — organically coupled defects

OWNER: Originality & Authenticity Reviewer
LABEL: PASS

Scenario: several tests fail from one shared transactional-boundary defect rather than one planted bug per test.

Expected: do not penalize multiple downstream failures as “too many verifier families.”

### DR-01 — vague difficulty prose

OWNER: Engineering Documentation Reviewer
LABEL: REVISE

```text
This task is challenging because it involves multiple interconnected components and various edge cases that must be handled correctly.
```

Expected: reject as generic.

### DR-02 — concrete reasoning bottleneck

OWNER: Engineering Documentation Reviewer
LABEL: PASS

```text
The restart path is deceptive because reusing the reservation fixes the duplicate debit but does not make the clearing row or ledger idempotent. A solver can therefore repair the first visible symptom and still leave reconciliation wrong on the second run.
```

Expected: pass if supported by task evidence.

### DIFF-01 — clerical multi-file edit

OWNER: Difficulty Reviewer
LABEL: REVISE

Scenario: task touches eight files but each change is explicitly listed in the instruction and requires no diagnosis.

Expected: high file count is not genuine difficulty.

### DIFF-02 — coupled state reasoning

OWNER: Difficulty Reviewer
LABEL: PASS-CANDIDATE

Scenario: solver must infer how persisted partial state changes the correct next action and several plausible local fixes violate downstream invariants.

Expected: legitimate advanced design candidate, pending empirical trials.

### CA-01 — stale public rubric conflict

OWNER: Compliance Auditor
LABEL: PASS_CURRENT_RULE

Scenario: a public old benchmark example requires an obsolete metadata field that current Edition 3 rules removed.

Expected: current authoritative rules win; do not import stale schema.

### CA-02 — agent image leakage

OWNER: Compliance Auditor
LABEL: REVISE

Scenario: agent Dockerfile copies `solution/solve.sh` into the image.

Expected: BLOCKER leakage finding.

### TA-01 — infrastructure failure

OWNER: Trajectory Analyst
LABEL: INFRASTRUCTURE

Scenario: trial has no solver turns because model credential refresh fails before container execution.

Expected: classify tool/infrastructure; do not infer reasoning difficulty.

### TA-02 — instruction gap

OWNER: Trajectory Analyst
LABEL: instruction_gap

Scenario: all agents fail one test because the required behavior is absent from every solver-visible artifact; oracle only knows it from hidden tests.

Expected: instruction_gap, not legitimate reasoning wall.

### ADJ-01 — concision vs fairness disagreement

OWNER: Adjudicator

Instruction Reviewer wants to delete an exact output constraint as “spec dump”; Verifier Engineer shows it is not defined in any referenced solver-visible contract and tests legitimately depend on it.

Expected: preserve or relocate the constraint to a clearly referenced solver-visible artifact; fairness controls.

## Historical regression cases

Add a case whenever:

- Harbor LLMaJ finds a material issue Pre-LLMaJ missed;
- portal/human review rejects a task for a quality dimension our reviewers passed;
- a reviewer generated a false blocker that a later authoritative review disproved;
- a difficulty suite exposed ambiguity/shortcut that design review should have predicted;
- instruction/documentation review overfit to style and removed necessary technical content.

Each historical case records:

```text
CASE_ID:
DATE:
TASK:
SOURCE: Harbor | portal | human | difficulty | local
POLICY_VERSION_THAT_MISSED:
INPUT_FIXTURE:
EXPECTED_LABEL:
WHY:
GENERALIZED_LESSON:
```

## Evaluation run record

```text
DATE:
REVIEWER:
POLICY_VERSION:
MODEL/CONFIG:
TRIALS_PER_CASE:
CASES:
BLOCKING_RECALL:
BLOCKING_PRECISION:
PASS_PRECISION:
INSUFFICIENT_EVIDENCE_ACCURACY:
EVIDENCE_GROUNDING_RATE:
SCOPE_DISCIPLINE:
REGRESSIONS:
DECISION: ADOPT | REVISE | REJECT
```
