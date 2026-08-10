# Cursor Operating Law

Operating policy version: `1.1`

Cursor is a local execution surface for the Terminus control plane, not an authority that can replace repository evidence. Chat history is working context; Git commits, packets, review JSON, session checkpoints and CI/Harbor artifacts are durable evidence.

## One role per chat

One Cursor chat performs exactly one logical role:

- Orchestrator/routing;
- one producer/fixer;
- one semantic reviewer.

Do not combine creator and reviewer authority in one context. Writers/builders never approve their own revision. A reviewer chat that has already seen excluded evidence is not cold for that role.

## Project CI Orchestrator agent

Use `.cursor/agents/terminus-ci-orchestrator.md` to start or resume the controller for one task. Its authoritative portable contract is `.terminus/agents/CI_ORCHESTRATOR.md`. The controller reconciles repository and CI evidence, identifies the first non-current gate and creates a one-role handoff; it does not perform the routed producer, fixer or reviewer role in the same chat.

## Packet required

Every new semantic review starts from `.terminus/new_review_packet.py`. The generated packet binds the role to `TASK_COMMIT`, protocol/prompt/role policy, `ROLE_CONTRACT_HASH`, and a unique review output path.

New protocol-2.1 reviews without their packet are not acceptance evidence.

## Isolation is explicit

Current Cursor reviews use `ISOLATION_MODE: PROCEDURAL`: the packet says what not to open, but the repository remains technically accessible. Do not claim filesystem-level isolation. If a future runner materializes only allowed evidence, it may use `MATERIALIZED`.

## Commit binding

`TASK_COMMIT` must be Git-derived. If the task tree moves after review, the result is `STALE`. If the governing role contract hash changes, that role's result is also `STALE` even when task files did not move.

`STALE` is not PASS. `INSUFFICIENT_EVIDENCE` is not PASS. LOW confidence is not enough for a mandatory ready gate.

## Slice discipline

For control-plane hardening, implement one coherent slice, run its deterministic checks, then move to the next slice. Do not rewrite unrelated policies merely for stylistic consistency.

## After a material change

1. Run the matching local validator/tests.
2. Update the task session only from live evidence.
3. Mark affected semantic gates `STALE`; never preserve an old PASS by prose.
4. Regenerate the relevant packet after the change is committed.
5. Open a fresh chat for a cold reviewer role.

## Submission-ready rule

A session table cannot create evidence. Semantic ready rows cite exact packet-bound reviews; deterministic ready rows cite runs/jobs/artifacts. `SUBMISSION_READY` requires every mandatory gate, not merely every row that happens to remain in the table.
