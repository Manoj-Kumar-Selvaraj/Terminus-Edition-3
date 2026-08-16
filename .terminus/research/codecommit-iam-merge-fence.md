# codecommit-iam-merge-fence — work-package research (strict rebuild)

STATUS: CANDIDATES_READY
SELECTED: WP-C

## Candidates

### WP-A — Thin IAM evaluator only
SCALE_FIT: FAIL (prior lab ~633 LOC). SCENARIO_TOO_SMALL for strict.

### WP-B — IAM + merge fence only (no API/audit/outbox)
SCALE_FIT: borderline; likely needs padding. Reject.

### WP-C — CodeCommit platform control plane (SELECTED)
PERSONA: Platform AppSec / source-control owner
ENGINEERING_OBJECTIVE: Bring the local CodeCommit control plane in line with the shipped IAM, PR quorum, fast-forward merge, pipeline deliver, audit, and webhook-outbox contracts after authz and merge fencing drifted from prod.
REQUIRED_END_STATE: Operator CLI + HTTP API authorize every mutating path; Deny/MFA/IP/References evaluate correctly; merges are FF-only after pool quorum; deliver is exactly-once with contracted event_id; authz decisions are queryable; pipeline deliver enqueues durable webhook outbox with retry semantics; multi-repo catalog and policy attachments persist under `/app/codecommit`.
REQUIREMENT_FAMILIES: IAM evaluation; repo/ref git ops; PR approval quorum; FF merge fence; pipeline bindings + journal; audit log; webhook outbox; HTTP API parity with CLI; seed/restart durability.
INHERITED_SYSTEM_STATE: Multi-repo bare git under var/repos, JSON policy attachments, approval rules, pipeline bindings, partial audit/outbox state, shift note + authz dump.
REASONING_CHAIN: IAM conditions × resource ARN × merge quorum × FF topology × deliver idempotency × outbox/audit side effects.
PARTIAL_FIX_TRAPS: Fixing only MFA; fixing merge without quorum; journaling without outbox; CLI-only while API bypasses IAM.
PRESERVATION: Existing repo objects, PR ids, audit append-only semantics, outbox attempt history.
SCALE_FIT: Natural multi-module Python control plane targeting ≥3000 substantive LOC with 25–30 organic F2P.
EDGE_FAILURE: unknown principal, unbound deliver, NOT_FF, insufficient quorum, webhook retry exhaustion, concurrent approve dedupe.
INSTRUCTION_FIT: Incident + binding contract path + end-state bullets (≤20).
NOVELTY: Distinct from ansible-ci (no runner queue), stackyard (not Terraform), webhook-outbox-delivery-plane (outbox subordinate to CodeCommit deliver).

### WP-D — Full AWS CodeCommit cloud mock with Cognito
Rejected: cloud-account / network ground-truth risk; out of scope for local stand-in.

### WP-E — Sonar/Artifactory bind hybrid
Rejected: overlaps platform-sonar-ingress-token-bind.
