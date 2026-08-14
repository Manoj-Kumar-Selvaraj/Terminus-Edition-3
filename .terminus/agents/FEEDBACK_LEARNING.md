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

Every event binds to an exact task commit and enters an append-only hash chain. A source label, caller-selected Git fragment or producer name appearing somewhere in immutable bytes is never proof of origin.

## Source provenance

`HUMAN_REVIEW` may be captured as `HUMAN_ASSERTED`. All automated/reviewer sources require immutable `source_binding` evidence.

Automated source trust has two levels:

- `REPOSITORY_RESOLVED`: the `git:` source artifact is on the authorized repository lineage and contains a structured source-event attestation matching the exact source type, producer, task ID, task commit and run ID when applicable.
- `EXTERNAL_POINTER_ONLY`: a content-addressed `run:` or `external:` pointer records provenance but is not independently repository-authenticated.

Repository source attestations live under the controlled `.terminus/feedback/source_evidence/` namespace. The identity fragment is only a consistency hint after structured event matching; it is not the authentication mechanism.

External pointers may contribute feedback signals, but they cannot alone close a finding or promote knowledge.

## Review-result authority

Non-human closure requires a repository-resolved `RESULT` under `.terminus/reviews/<task>/`. The exact bound result must:

- validate against the canonical review-result schema for reviewer results;
- bind the configured verification owner to the canonical embedded reviewer role;
- bind the exact task and verification task commit;
- carry a successful top-level verdict (`PASS`, `APPROVE` or `APPROVE_WITH_NOTE`);
- carry `SUFFICIENT` evidence and at least `MEDIUM` confidence;
- carry current Protocol, prompt and reviewer-role policy versions;
- carry the current reviewer role-contract hash;
- bind a control-plane commit on the authorized repository lineage;
- bind the exact packet in the same controlled review directory;
- match that packet's review ID, task, task commit, control-plane commit, policy versions, role contract, role, canonical output schema and exact result output path.

The evidence commit itself must be reachable from the current repository lineage; an available orphan/side Git object is not review authority. This converts the review namespace from a path-only convention into a packet-bound canonical result boundary.

A noncanonical pseudo-PASS, old PASS for another task snapshot, current `REVISE`/`REJECT`, insufficient review or stale reviewer contract cannot close a finding or train future agents. Human closure remains allowed only when the finding explicitly names `HUMAN_REVIEWER` as its verification owner and the closing feedback is `HUMAN_REVIEW`/`HUMAN_ASSERTED`.

## Current-task remediation loop

```text
feedback -> canonical finding -> remediation packet -> owning repair stage(s)
         -> post-floor ADVANCE execution chain -> REPAIRED
         -> trusted independent verification -> CLOSED
```

An unresolved finding interlocks the controller before normal lifecycle progression. Repair packets are ordered by canonical stage order and bind to the execution-ledger sequence that existed when repair was planned.

`REPAIRED` is itself a ledger-proven state. `mark-repaired` requires the exact `remediation_id`; the canonical progress validator replays only execution records after the packet's ledger floor, enforces each declared stage and repair role in order, requires `ADVANCE`, checks input/output task lineage, and requires the supplied repaired task commit to equal the computed terminal output commit. The original finding commit cannot be relabeled as repaired. Verification and learning eligibility replay the same remediation proof again.

The current task commit must remain on the finding's Git lineage; otherwise the controller returns `REMEDIATION_LINEAGE_CONFLICT`. A repair owner cannot verify its own finding.

Task-producing/fixing execution records are path-scoped. They may change the task directory and explicitly task-scoped `.terminus/designs/<task>...` / `.terminus/contracts/<task>/...` artifacts, but they cannot declare reviewer evidence, learning knowledge, agent policy, CI workflow, another task or other protected repository paths as their task output.

## Conflict handling

When ordinary feedback sources disagree on classification, the normalizer emits `FEEDBACK_CONFLICT`. Conflicts are not majority-voted and cannot enter ordinary remediation.

Human conflict resolution must be explicitly classified as `CONFLICT_RESOLUTION`. Automated conflict resolution is restricted to the configured adjudication/controller authority and must supply repository-resolved semantic result evidence; the result is validated before the conflict can be retired as `WONT_FIX`. A malformed, stale, negative or unrelated result cannot unblock the controller.

`POLICY_CONFLICT` is a first-class canonical finding state rather than an out-of-band label. Normalization emits it only when trusted feedback supplies structured conflict semantics containing at least two distinct existing authoritative repository rule sources and a registered affected lifecycle stage. An arbitrary caller string `category=POLICY_CONFLICT` without that structured authority evidence fails closed. The controller then returns `RESOLVE_POLICY_CONFLICT`; ordinary remediation cannot proceed until the authority conflict is resolved.

## Learning boundary

Raw feedback, task-specific findings and remediation state live under `.terminus/learning/state/` and are intentionally gitignored. They may contain exact task locations, reviewer conclusions, Portal messages or solver trajectories and must not leak into future cold reviews.

Generalized knowledge lives under `.terminus/learning/knowledge/` and is tracked. Future StageInvocations receive only active generalized lessons relevant to their stage/role/domain plus current-task remediation instructions owned by the invoked repair stage. The executor-facing projection explicitly carries:

```text
raw_feedback_exposed = false
raw_historical_findings_exposed = false
```

Domain-targeted lessons fail closed: without an explicit matching invocation domain they are not projected. A cold reviewer may receive a generalized anti-pattern, but never the prior task's raw finding, file/line answer or historical verdict.

## Promotion model

```text
RAW_FEEDBACK -> FINDING -> LEDGER-PROVEN REPAIRED
             -> TRUSTED VERIFIED/CLOSED FINDING
             -> LESSON -> PATTERN -> POLICY_CANDIDATE
```

A finding is learning-eligible only if its stored remediation proof and closure feedback can both be replayed and independently validated. Repeated lessons accumulate stable finding identities. Recurrence across at least three distinct tasks may mark a pattern/lesson as a policy candidate, but this subsystem never edits canonical policy automatically.

## Invocation provenance

Each StageInvocation binds its learning projection to exact append-only registry heads and a `context_hash`. The recorder replays those exact heads and rejects modified lessons, widened remediation context or invented learning projections even if a caller recomputes the invocation hash.

Portable `lessons.jsonl` and `patterns.jsonl` are part of the StageInvocation control-plane snapshot. Newly learned portable knowledge must therefore be reviewed/committed before it can influence another executable invocation; dirty or uncommitted portable knowledge causes control-plane snapshot validation to fail.

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

Automated sources additionally supply `--source-binding-json` pointing at their structured immutable source-event evidence.

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

After the planned execution chain is complete, bind the exact remediation proof:

```bash
python .terminus/feedback/feedback_cli.py mark-repaired \
  --finding-id <finding_id> \
  --remediation-id <remediation_id> \
  --task-commit <terminal_repair_commit>
```

Resolve a feedback/policy conflict only with trusted resolution feedback:

```bash
python .terminus/feedback/feedback_cli.py resolve-conflict \
  --finding-id <finding_id> \
  --feedback-id <trusted_resolution_feedback_id>
```

After trusted independent verification closes the finding, generalized learning can be created:

```bash
python .terminus/feedback/feedback_cli.py learn \
  --finding-id <finding_id> \
  --future-rule "When behavior crosses an external boundary, independently verify that boundary rather than trusting only an internal proxy."
```

Because portable learning is control-plane-commit bound, commit/review the resulting knowledge change before issuing later StageInvocations.
