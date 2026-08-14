# Unified Feedback, Remediation & Agent Learning

Feedback-learning contract version: `1.0`

The Terminus feedback plane treats task-quality signals from humans, reviewers, CI systems, Portal checks, LLMaJ, model diagnostics/trials, difficulty analysis, final review, submission results and runtime failures as first-class `FeedbackEvent` records. Feedback is not a vote and it is not model-weight retraining. It is durable institutional learning: task-local remediation plus generalized lessons that future agents receive through bounded StageInvocation context.

## Supported feedback sources

- `HUMAN_REVIEW`
- `INDEPENDENT_REVIEW`
- `REVIEWER_REVIEW`
- `PORTAL_CI`
- `REPOSITORY_CI`
- `LLMAJ`
- `MODEL_DIAGNOSTIC`
- `MODEL_TRIAL`
- `DIFFICULTY`
- `FINAL_REVIEW`
- `SUBMISSION_RESULT`
- `RUNTIME`

Every feedback event binds to an exact task commit and enters an append-only hash chain. Human feedback is equal in standing to machine feedback: it is never reduced to an unstructured chat note.

## Current-task remediation loop

```text
feedback -> canonical finding -> remediation packet -> owning repair stage(s)
         -> descendant task commit -> independent verification -> close
```

An unresolved finding interlocks the controller before normal lifecycle progression. Repair packets are ordered by canonical stage order, bind to the execution-ledger sequence that existed when the repair was planned, and therefore cannot be satisfied by old historical executions. A repair owner cannot verify its own finding. A finding remains blocking after repair until its configured independent verification owner closes it with new feedback evidence.

When multiple sources disagree on classification, the normalizer emits `FEEDBACK_CONFLICT`. Conflicts are not majority-voted and cannot be planned for remediation until resolved. Existing `POLICY_CONFLICT` behavior remains fail-closed.

## Learning boundary

Raw feedback, task-specific findings and remediation state live under `.terminus/learning/state/` and are intentionally gitignored. They may contain exact task locations, prior reviewer conclusions, Portal messages or solver trajectories and must not leak into future cold reviews.

Generalized, approved knowledge lives under `.terminus/learning/knowledge/` and may be committed. Future StageInvocations receive only:

- active generalized lessons relevant to their stage/role/domain; and
- current-task remediation instructions owned by the stage being invoked.

The executor-facing projection explicitly carries:

```text
raw_feedback_exposed = false
raw_historical_findings_exposed = false
```

A cold reviewer may learn a generalized anti-pattern such as "independently inspect external-effect assertions for internal-proxy verification", but must not receive the prior task's raw finding, file/line answer or historical verdict.

## Promotion model

```text
RAW_FEEDBACK -> FINDING -> VERIFIED/CLOSED FINDING -> LESSON -> PATTERN -> POLICY_CANDIDATE
```

Only independently `VERIFIED` or `CLOSED` findings may create lessons. Repeated lessons accumulate stable source identities. Recurrence across at least three distinct tasks may mark a pattern/lesson as a policy candidate, but no code here automatically edits canonical policy. Policy promotion remains an explicit governed action.

## Invocation provenance

Each StageInvocation binds its learning projection to exact append-only registry chain heads and a `context_hash`. The execution recorder replays those exact heads and rejects a modified lesson, widened remediation context or invented learning projection even if the caller recomputes the public invocation hash. Later feedback can append to the registries without invalidating an already-issued invocation.

## CLI examples

Capture human feedback:

```bash
python .terminus/feedback/feedback_cli.py add \
  --source HUMAN_REVIEW \
  --producer Manoj \
  --task-id my-task \
  --task-commit <sha> \
  --severity HIGH \
  --category WEAK_EXTERNAL_BOUNDARY \
  --stage-hint VERIFIER_BUILD \
  --message "The verifier trusts an internal counter instead of the external effect."
```

Normalize one or more signals into a finding and plan repair:

```bash
python .terminus/feedback/feedback_cli.py normalize \
  --feedback-id <feedback_id> \
  --generalized "External effects must be verified at the observable boundary." \
  --root-cause INTERNAL_PROXY_FOR_EXTERNAL_EFFECT \
  --repair-stage VERIFIER_BUILD \
  --caught-by SPEC_ALIGNMENT \
  --verification-owner Q4_SPEC_TEST_CONTRACT_REVIEWER

python .terminus/feedback/feedback_cli.py plan --finding-id <finding_id>
```

The normal controller then returns `REMEDIATE_STAGE` ahead of normal progression. After the repair execution is recorded, it waits at `AWAIT_REMEDIATION_VERIFICATION` until independent verification feedback closes the finding.

Create generalized learning after closure:

```bash
python .terminus/feedback/feedback_cli.py learn \
  --finding-id <finding_id> \
  --future-rule "When behavior crosses an external boundary, independently verify that boundary rather than trusting only an internal proxy."
```

Inspect learning state or the exact projection an agent would receive:

```bash
python .terminus/feedback/feedback_cli.py status
python .terminus/feedback/feedback_cli.py project \
  --stage-id VERIFIER_BUILD \
  --role-id A5_VERIFIER_AUTHOR \
  --task-id my-task \
  --task-commit <sha>
```
