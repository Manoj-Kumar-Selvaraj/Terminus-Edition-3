# Unified Feedback, Remediation & Agent Learning

Feedback-learning contract version: `1.0`

The Terminus feedback plane treats task-quality signals from humans, reviewers, CI systems, Portal checks, LLMaJ, model diagnostics/trials, difficulty analysis, final review, submission results and runtime failures as first-class `FeedbackEvent` records. This is not model-weight retraining. It is durable institutional learning: current-task remediation plus generalized lessons delivered through bounded StageInvocation context.

## Trust root

Repository consistency is not identity. A source label, role string, Git path, reachable commit, hash-chained registry row, mutually consistent packet/result pair or locally constructible StageInvocation/ExecutionRecord is not by itself semantic authority.

Semantic authority is represented by detached OpenSSH-signed receipts verified by `.terminus/authority/receipts.py`. The verifier reads public keys only from the operator-controlled `TERMINUS_AUTHORITY_ALLOWED_SIGNERS` file, and that file must resolve outside the repository tree. Private signing keys are never repository data.

Receipts bind an exact canonical JSON claim, claim hash, action and semantic principal. Supported authority actions are:

- `HUMAN_FEEDBACK` — principal `human:<producer>`;
- `AUTOMATED_SOURCE` — principal `automation:<source_type>:<producer>`;
- `REVIEW_RESULT` — principal `reviewer:<canonical reviewer role>`;
- `EXECUTION_RESULT` — principal `executor:<canonical stage role>`;
- `LESSON_ACTIVATION` — principal `learning-curator`.

A receipt for one claim, action or principal cannot be reused for another. Repository-controlled signer configuration is rejected.

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

Every event binds to an exact task commit and enters an append-only hash chain. Event identity, content hash and source provenance are replayed before the event can become canonical finding authority.

## Source provenance

Human feedback without a valid authority receipt is retained as `HUMAN_ASSERTED` but is informational only. A signed human event becomes `HUMAN_AUTHENTICATED` and may contribute canonical finding authority where the relevant semantic action permits human authority.

Automated/reviewer sources require immutable `source_binding` evidence. Repository-resolved automated sources additionally require an `AUTOMATED_SOURCE` authority receipt over the exact source, task, observation, capture time and source binding. Their source-specific execution record must consume the exact immutable binding and must itself carry valid `EXECUTION_RESULT` authority.

Trust statuses are:

- `HUMAN_AUTHENTICATED` — valid external human authority receipt;
- `HUMAN_ASSERTED` — captured human assertion without authenticated semantic authority;
- `REPOSITORY_RESOLVED` — repository-resolved evidence plus the source/reviewer authority required by its source contract;
- `EXTERNAL_POINTER_ONLY` — content-addressed external pointer retained as evidence but not independently authenticated for closure or promotion.

Repository source attestations live under the controlled `.terminus/feedback/source_evidence/` namespace. Structured JSON and Git reachability remain evidence bindings, not their own root of trust.

## Canonical finding genesis

`FindingNormalizer` accepts only schema-valid feedback whose content hash, feedback identity and provenance replay successfully. At least one event must be authenticated authority before a canonical finding can be emitted.

Persisted findings are re-derived from their stored signal IDs at terminal/learning consumption. A raw appended OPEN, REPAIRED, VERIFIED, CLOSED or WONT_FIX row therefore cannot become semantic authority merely because it is schema-valid or hash-chained.

## Review-result authority

Non-human closure requires a repository-resolved canonical `RESULT` under `.terminus/reviews/<task>/`. The exact bound result must:

- validate against the canonical review-result schema;
- bind the configured verification owner to the embedded canonical reviewer role;
- bind the exact task and repaired task commit;
- carry a passing top-level verdict, `SUFFICIENT` evidence and at least `MEDIUM` confidence;
- carry current Protocol, prompt and reviewer-role policy versions and role-contract hash;
- bind the exact generated packet, review ID, result output path and control-plane commit;
- carry a valid `REVIEW_RESULT` authority receipt for that exact result;
- be consumed as immutable evidence by the mapped canonical controller execution;
- have that controller execution itself carry valid `EXECUTION_RESULT` authority.

Reachable hand-written packet/result files plus a locally constructed controller record are therefore insufficient.

### Finding-specific verification

A generic task PASS is not finding closure authority. Verification binds:

- `finding_id`;
- `remediation_id`;
- exact `repaired_task_commit`;
- original signal IDs;
- a hash of the exact closure conditions.

A non-human review RESULT must carry that exact `FINDING_VERIFICATION` binding. Human verification is allowed only when the finding names `HUMAN_REVIEWER`, the event is `HUMAN_AUTHENTICATED`, its category is `FINDING_VERIFICATION`, and its value carries the same exact verification binding plus `verification=PASS`.

## Current-task remediation loop

```text
feedback -> authenticated canonical finding -> remediation packet
         -> signed owning repair execution(s) -> REPAIRED
         -> finding-bound independent verification -> CLOSED
```

An unresolved finding interlocks the controller before normal lifecycle progression. Remediation packets are deterministically re-derived from the finding and bind the execution-ledger sequence that existed when repair was planned.

`mark-repaired` requires the exact `remediation_id`. The progress validator replays only post-floor execution records, enforces every planned stage and repair role in order, requires `ADVANCE`, exact StageInvocation remediation context, valid task lineage and the computed terminal output commit. Every remediation-counting execution must also pass `EXECUTION_RESULT` authority verification.

Task-producing/fixing records may mutate only the task directory and explicitly task-scoped `.terminus/designs/<task>...` / `.terminus/contracts/<task>/...` paths. A task-mutating producer/fixer commit must contain an actual authorized task-scope diff; an empty descendant commit is not a repair.

A repair owner cannot verify its own finding. Verification binds the exact repaired commit rather than a generic descendant.

## Conflict handling

When ordinary feedback sources disagree on classification, the normalizer emits `FEEDBACK_CONFLICT`. Conflicts are not majority-voted and cannot enter ordinary remediation.

Conflict resolution evidence is bound to the exact finding, original signal IDs and signal claims. Authenticated human resolution must be explicitly classified as `CONFLICT_RESOLUTION`. Automated semantic resolution is restricted to the canonical Adjudicator and must carry the exact repository-resolved, signed review result. CI Orchestrator is not a semantic conflict resolver.

`POLICY_CONFLICT` is stricter. It may originate only from a signed canonical Adjudicator review. The proof must bind:

- a registered affected lifecycle gate;
- one normalized `decision_key`;
- an explicit conflict statement;
- at least two distinct exact authoritative rule identities;
- exact reachable source revisions, rule text and rule hashes;
- the same `decision_key` on every rule;
- at least two mutually exclusive scalar `required_value` values;
- the exact proof in the Adjudicator RESULT's `POLICY_CONFLICT_PROOF` output.

Merely naming policy files, choosing two unrelated excerpts or inventing caller-controlled outcome labels is not policy-conflict authority.

## Learning boundary

Raw feedback, task-specific findings and remediation state live under `.terminus/learning/state/` and are intentionally gitignored. They may contain exact task locations, reviewer conclusions, Portal messages or solver trajectories and must not leak into future cold reviews.

Generalized knowledge lives under `.terminus/learning/knowledge/` and is tracked. Future StageInvocations receive only ACTIVE generalized lessons relevant to their stage/role/domain plus current-task remediation instructions owned by the invoked repair stage. The projection explicitly carries:

```text
raw_feedback_exposed = false
raw_historical_findings_exposed = false
```

Domain-targeted lessons fail closed without an explicit matching invocation domain. A cold reviewer may receive a generalized anti-pattern but never the prior task's raw finding, file/line answer or historical verdict.

## Lesson and pattern integrity

Learning creation defaults to `CANDIDATE`, not `ACTIVE`. A candidate may contain a proposed `future_rule`, but it cannot influence future agents.

ACTIVE lessons require a `LESSON_ACTIVATION` receipt from `learning-curator` over the exact lesson ID, category, generalized failure pattern, root-cause class, future rule, targets, source findings and promotion state. Changing the future rule, targets, sources or promotion after approval invalidates the receipt.

Every lesson source must be independently learning-eligible and must semantically match the lesson category, generalized failure pattern and root-cause class. Patterns similarly recompute their finding/task counts and require every source finding to match the pattern category and root-cause class. Unrelated closed findings therefore cannot be combined into a fabricated recurrence or policy candidate.

```text
RAW_FEEDBACK -> AUTHENTICATED FINDING -> SIGNED/LEDGER-PROVEN REPAIRED
             -> FINDING-BOUND VERIFIED/CLOSED
             -> CANDIDATE LESSON -> CURATOR-SIGNED ACTIVE LESSON
             -> SEMANTICALLY REPLAYED PATTERN -> POLICY_CANDIDATE
```

Recurrence across at least three distinct verified tasks may mark a pattern/lesson as a policy candidate, but this subsystem never edits canonical policy automatically.

## Invocation provenance

Each StageInvocation binds its learning projection to exact append-only registry heads and a `context_hash`. ExecutionRecord replay validates those exact heads and rejects modified lessons, widened remediation context or invented learning projections even if a caller recomputes an invocation hash.

Portable `lessons.jsonl` and `patterns.jsonl` are part of the StageInvocation control-plane snapshot. Newly learned portable knowledge must therefore be reviewed/committed before it can influence another executable invocation; dirty or uncommitted portable knowledge fails snapshot validation.

Later private feedback may append without invalidating an already-issued invocation because the invocation records the exact registry heads it consumed.

## CLI authority inputs

The CLI consumes receipts; it does not mint them. Signing is an external/operator responsibility.

Human or automated capture may provide:

```text
--authority-receipt-json '<signed receipt object>'
--source-binding-json '<immutable source binding object>'
```

Unsigned human capture is retained but cannot create a canonical finding by itself.

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

After the signed planned repair execution chain is complete:

```bash
python .terminus/feedback/feedback_cli.py mark-repaired \
  --finding-id <finding_id> \
  --remediation-id <remediation_id> \
  --task-commit <terminal_repair_commit>
```

Generalized learning is created as a candidate by default:

```bash
python .terminus/feedback/feedback_cli.py learn \
  --finding-id <finding_id> \
  --future-rule "When behavior crosses an external boundary, verify that boundary rather than trusting an internal proxy."
```

Activation additionally requires `--activate --authority-receipt-json '<learning-curator receipt>'`.

Because portable learning is control-plane-commit bound, commit/review resulting knowledge changes before issuing later StageInvocations.
