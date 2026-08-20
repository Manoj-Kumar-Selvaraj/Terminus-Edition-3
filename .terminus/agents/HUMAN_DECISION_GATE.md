# Terminus Human Decision Gate

Policy version: `1.0`

`HUMAN_DECISION_REQUIRED` is a first-class foreground stop condition for bounded human judgment. It exists so a task owner can make an explicit commit-bound decision in the active Terminus task chat without constructing JSON by hand or using a cryptographic signer for routine approvals.

## Authority classes

Terminus distinguishes:

- `MACHINE_EVIDENCE` — controller, CI and reviewer evidence;
- `CHAT_HUMAN_APPROVAL` — explicit decision by the human in the active task chat against one outstanding deterministic decision;
- `EXTERNAL_SIGNED_AUTHORITY` — optional higher-assurance cryptographic authority when policy explicitly requires it.

`CHAT_HUMAN_APPROVAL` must never be relabeled `HUMAN_AUTHENTICATED` or treated as cryptographically equivalent to external signed authority.

## Decision request

The machine-defined request must contain:

```text
decision_id
task_id
task_commit
stage
decision_type
allowed_decisions
reason
consequences
expires_if_task_commit_changes=true
context
```

`decision_id` is deterministic over the complete request identity and has form `hd_<sha256>`.

Requests and resolutions are append-only events in:

`.terminus/human-decisions/<task>/ledger.jsonl`

The ledger is hash chained. A resolved decision never edits the request event in place.

## Same-chat rule

A chat approval is valid only when:

1. an unresolved deterministic decision already exists for the exact task and task commit;
2. the Orchestrator presents that bounded decision to the human in the active task chat;
3. the human replies explicitly after the request is outstanding;
4. the Orchestrator maps the reply to one of the request's `allowed_decisions` and records that exact resolution;
5. downstream validators revalidate the decision ledger before using the approval.

The Orchestrator must not infer approval from old prose, remembered preferences, PR comments, prior decisions or generic statements such as "accept these kinds of risks".

The user need not repeat the decision ID. The Orchestrator resolves a short response such as `Approve`, `Reject`, or `Accept the risk and continue` only against the single currently outstanding decision it just presented.

## Staleness

If `expires_if_task_commit_changes=true`, any task commit change after the request makes that request inapplicable to the new snapshot. The controller must create a new request and ask again. A decision for another task, stage, decision type, commit or request ID cannot be reused.

## Recovery

On bootstrap or chat loss, run:

`python3 .terminus/human_decision_cli.py status --task-id <task> --task-commit <current-task-commit>`

If the result is `HUMAN_DECISION_REQUIRED`, present the outstanding request again. Do not guess a decision. If there is no outstanding decision, continue normal controller recovery.

## Request and resolution interfaces

Create a bounded request with:

`python3 .terminus/human_decision_cli.py request ...`

Resolve it only after an explicit human reply with:

`python3 .terminus/human_decision_cli.py resolve --decision-id <id> --decision <allowed-choice> --response-text <exact-current-reply>`

The response text is not persisted; only its SHA-256 fingerprint is recorded.

## Interaction with RUN_TO_BLOCKER

`HUMAN_DECISION_REQUIRED` is a genuine allowed stop condition under `RUN_TO_BLOCKER`. Before it is reached, the Orchestrator continues automatically. After the human replies, the Orchestrator records the decision and immediately resumes the normal validate -> record -> replay/materialize -> controller continue loop.

## Q4 residual-risk specialization

For Q4 residual risk, the decision type is `ACCEPT_RESIDUAL_Q4_RISK`. The request context must bind the exact frozen Q4 review ID, frozen Q4 task commit, `q4_verdict=REVISE`, every blocking finding ID and non-empty residual backlog. A successful resolution may satisfy Q4 only through `CHAT_HUMAN_RISK_ACCEPTANCE`; Q4 itself remains `REVISE`, and Q6 remains independently mandatory.
