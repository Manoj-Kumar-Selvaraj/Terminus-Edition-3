# Unified Feedback, Remediation & Agent Learning

Feedback-learning contract version: `1.0`

The Terminus feedback plane treats task-quality signals from humans, reviewers, CI systems, Portal checks, LLMaJ, model diagnostics/trials, difficulty analysis, final review, submission results and runtime failures as first-class `FeedbackEvent` records. This is not model-weight retraining. It is durable institutional learning: current-task remediation plus generalized lessons delivered through bounded StageInvocation context.

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

Every event binds to an exact task commit and enters an append-only hash chain. A source label alone is never proof of origin.

## Source provenance

`HUMAN_REVIEW` may be captured as `HUMAN_ASSERTED`. All automated/reviewer sources require an immutable `source_binding` evidence reference whose identity matches the claimed producer or run ID.

Automated source trust has two levels:

- `REPOSITORY_RESOLVED`: `git:` or `commit:` evidence resolves to immutable repository bytes/identity.
- `EXTERNAL_POINTER_ONLY`: a content-addressed `run:` or `external:` pointer records provenance but is not independently repository-resolved.

External pointers may contribute feedback signals, but they cannot alone close a finding or promote knowledge. Non-human closure requires `REPOSITORY_RESOLVED` evidence bound to the configured verification owner. Human closure is allowed only when the finding explicitly names `HUMAN_REVIEWER` as its verification owner and the closing feedback is `HUMAN_REVIEW`/`HUMAN_ASSERTED`.

## Current-task remediation loop

```text
feedback -> canonical finding -> remediation packet -> owning repair stage(s)
         -> descendant task commit -> trusted independent verification -> close
```

An unresolved finding interlocks the controller before normal lifecycle progression. Repair packets are ordered by canonical stage order and bind to the execution-ledger sequence that existed when repair was planned, so historical executions cannot satisfy a new remediation. The current task commit must remain on the finding's Git lineage; otherwise the controller returns `REMEDIATION_LINEAGE_CONFLICT`. A repair owner cannot verify its own finding.

When multiple sources disagree on classification, the normalizer emits `FEEDBACK_CONFLICT`. Conflicts are not majority-voted and cannot enter ordinary remediation. They must be explicitly adjudicated through trusted human feedback or repository-resolved `ADJUDICATOR`/`CI_ORCHESTRATOR` feedback. The conflict finding is then retired as `WONT_FIX`; any substantive resolved problem is normalized as a replacement finding with its own identity and repair path. Existing `POLICY_CONFLICT` behavior remains fail-closed.

## Learning boundary

Raw feedback, task-specific findings and remediation state live under `.terminus/learning/state/` and are intentionally gitignored. They may contain exact task locations, reviewer conclusions, Portal messages or solver trajectories and must not leak into future cold reviews.

Generalized knowledge lives under `.terminus/learning/knowledge/` and is tracked. Future StageInvocations receive only active generalized lessons relevant to their stage/role/domain plus current-task remediation instructions owned by the invoked repair stage. The executor-facing projection explicitly carries:

```text
raw_feedback_exposed = false
raw_historical_findings_exposed = false
```

A cold reviewer may receive a generalized anti-pattern, but never the prior task's raw finding, file/line answer or historical verdict.

## Promotion model

```text
RAW_FEEDBACK -> FINDING -> TRUSTED VERIFIED/CLOSED FINDING
             -> LESSON -> PATTERN -> POLICY_CANDIDATE
```

A finding is learning-eligible only if its stored closure feedback can be replayed and independently validated. Repeated lessons accumulate stable finding identities. Recurrence across at least three distinct tasks may mark a pattern/lesson as a policy candidate, but this subsystem never edits canonical policy automatically.

## Invocation provenance

Each StageInvocation binds its learning projection to exact append-only registry heads and a `context_hash`. The recorder replays those exact heads and rejects modified lessons, widened remediation context or invented learning projections even if a caller recomputes the invocation hash.

Portable `lessons.jsonl` and `patterns.jsonl` are part of the StageInvocation control-plane snapshot. Therefore newly learned portable knowledge must be reviewed/committed before it can influence another executable invocation; dirty or uncommitted portable knowledge causes control-plane snapshot validation to fail.

Later private feedback may append without invalidating an already-issued invocation because the invocation records the exact registry heads it consumed.

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

Automated sources additionally supply `--source-binding-json` with an immutable evidence reference.

Normalize and plan repair:

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

Resolve a feedback/policy conflict only with trusted resolution feedback:

```bash
python .terminus/feedback/feedback_cli.py resolve-conflict \
  --finding-id <finding_id> \
  --feedback-id <trusted_resolution_feedback_id>
```

After repair, trusted independent verification closes the finding. Generalized learning can then be created:

```bash
python .terminus/feedback/feedback_cli.py learn \
  --finding-id <finding_id> \
  --future-rule "When behavior crosses an external boundary, independently verify that boundary rather than trusting only an internal proxy."
```

Because portable learning is control-plane-commit bound, commit/review the resulting knowledge change before issuing later StageInvocations.
