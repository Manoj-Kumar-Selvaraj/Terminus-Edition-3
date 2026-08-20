# Q4 Closure and Human Risk-Acceptance Policy

Policy version: `1.3`

This policy governs exceptional Q4 satisfaction after ordinary Q4 repair iteration can no longer proceed. It does not weaken ordinary cold Q4, rewrite a frozen Q4 verdict, or permit the Orchestrator to waive a semantic finding.

## Adjudicated-closure activation prerequisites

The adjudicated-closure path is available only when all of the following are true:

1. an exhaustive Q4/review-repair sequence has tripped the Protocol circuit breaker and the durable controller state is `BLOCKED`;
2. a frozen Adjudicator result established the controlling semantic repair boundary, including upheld/narrowed and rejected scope;
3. the Adjudicator authorized one final bounded closure repair or otherwise fixed the closure boundary;
4. that final repair, if any, is committed and its exact task diff is available;
5. one final exact-commit exhaustive cold Q4 has completed after the boundary/repair;
6. the final Q4 is not patched again before closure reconciliation.

If these prerequisites are absent, use the normal Protocol Q4 path. A closure result can never legitimize an ordinary first-pass `REVISE`.

## Independent closure decision

The `Q4 Closure Adjudicator` is a read-only semantic reviewer. It receives the frozen boundary Adjudicator result, the final frozen Q4 result, the exact boundary-to-final task diff, current authoritative rules and no desired outcome. It must reconcile every final-Q4 finding exactly once.

Allowed dispositions are:

- `CLOSED_BOUND_FINDING` — a previously upheld/narrowed semantic blocker is closed by the final repair;
- `SURVIVING_BOUND_BLOCKER` — a previously upheld/narrowed blocker still survives; blocking;
- `REPAIR_REGRESSION` — the final bounded repair introduced the finding; blocking;
- `NEW_EVIDENCE` — evidence not reviewable at the frozen boundary materially creates a new finding; blocking;
- `AUTHORITATIVE_RULE_CONFLICT` — a direct current higher-precedence rule conflict remains unresolved; blocking and requires strategy/policy resolution rather than blind patching;
- `REJECTED_SCOPE_REOPEN` — the final Q4 reopens scope the frozen boundary explicitly rejected/narrowed away without genuinely new evidence; non-blocking for this closure;
- `LATENT_AFTER_BOUNDARY` — the evidence was already fully reviewable before the frozen closure boundary but the completeness reviewer did not raise it until after the final boundary; non-blocking for this task closure and retained as learning/policy debt.

`LATENT_AFTER_BOUNDARY` is not a declaration that the observation is unimportant. It means the no-drip/circuit-breaker authority has moved responsibility from another task patch loop to institutional learning or a future policy/task-generation improvement. A direct authoritative-rule conflict must use `AUTHORITATIVE_RULE_CONFLICT`, not be hidden as latent.

## Finding identity

The closure packet records a deterministic `q4-finding-v1` SHA-256 fingerprint for every final-Q4 finding from its criterion, evidence-reference family and why-it-matters text. Finding IDs remain visible, but changing an ID alone cannot evade exact reconciliation.

## Closure PASS

`CLOSURE_OUTCOME: PASS` requires:

- a current packet-bound `Q4 Closure Adjudicator` result with `PASS`, confidence `HIGH` or `MEDIUM`, and `SUFFICIENT` evidence;
- exact current task-commit binding;
- exact frozen boundary-Adjudicator and final-Q4 packet/result binding;
- exact repair-base/final task commits and final task diff binding;
- every final-Q4 finding reconciled exactly once with the packet-recorded fingerprint;
- no `SURVIVING_BOUND_BLOCKER`, `REPAIR_REGRESSION`, `NEW_EVIDENCE`, or `AUTHORITATIVE_RULE_CONFLICT` disposition.

A closure PASS does **not** change the final Q4 result from `REVISE` to `PASS`. The durable session retains the frozen Q4 verdict and adds a distinct `Q4 Adjudicated Closure` PASS row.

## Authenticated external human risk acceptance

`AUTHENTICATED_HUMAN_RISK_ACCEPTANCE` remains the hardened signed-authority route for a frozen Q4 `REVISE`. It requires the canonical append-only feedback event to be `HUMAN_AUTHENTICATED`, a valid `HUMAN_FEEDBACK` receipt, explicit frozen-Q4 and accepted-current-commit binding, Git ancestry from the frozen Q4 commit to the accepted commit, exact blocking-finding acceptance, and non-empty residual backlog. Task mutation after the accepted commit makes the authority stale. The CI Orchestrator may consume this authority but may not manufacture it.

## Same-chat human decision authority

`CHAT_HUMAN_RISK_ACCEPTANCE` is the normal low-friction route for a live task owner who explicitly accepts a bounded residual Q4 risk in the active Terminus task chat. It is not cryptographically equivalent to `HUMAN_AUTHENTICATED` and must never be relabeled as such.

This route requires a first-class outstanding human decision created through `.terminus/human_decision_cli.py request` with:

- exact `task_id` and current exact `task_commit`;
- stage `QUALITY_INTERLOCK`;
- decision type `ACCEPT_RESIDUAL_Q4_RISK`;
- at least `ACCEPT_RISK` and `REJECT` as allowed decisions;
- machine-defined reason and consequences;
- structured context containing the frozen Q4 `review_id`, frozen Q4 `task_commit`, `q4_verdict: REVISE`, the exact complete `accepted_finding_ids`, and non-empty `residual_backlog`.

The decision request receives deterministic `decision_id = hd_<sha256>` and is recorded in the append-only hash-chained `.terminus/human-decisions/<task>/ledger.jsonl` ledger. The Orchestrator must present that exact outstanding request to the human. It must not infer approval from old chat prose, a generic preference, or an earlier risk decision.

Only after an explicit response in the active task chat may the Orchestrator call `.terminus/human_decision_cli.py resolve` for that exact pending decision. The resolution records `authority.type = CHAT_HUMAN_APPROVAL`, source `ACTIVE_TASK_CHAT`, and a SHA-256 fingerprint of the explicit response without storing the response prose itself.

The acceptance is valid only when:

- the decision remains the exact resolved request for this task and stage;
- the decision task commit equals the repository's current task commit;
- the decision is `ACCEPT_RISK` or a policy-allowed equivalent such as `OVERRIDE_WITH_BACKLOG`;
- the Q4 result remains `REVISE` with sufficient evidence and MEDIUM/HIGH confidence;
- the decision context binds the exact frozen Q4 review ID and frozen Q4 task commit;
- the context accepts exactly every blocking Q4 finding and preserves non-empty residual backlog;
- any task-commit change makes the approval stale and requires a new decision request.

The canonical lifecycle representation is:

```text
Q4 verdict: REVISE
Q4 satisfaction: CHAT_HUMAN_RISK_ACCEPTANCE
Q4 Human Risk Acceptance: PASS
Human authority: CHAT_HUMAN_APPROVAL
```

The `Q4_CLOSURE_RESULT` compatibility envelope for this route contains only:

```json
{
  "type": "CHAT_HUMAN_RISK_ACCEPTANCE",
  "decision_id": "hd_<sha256>"
}
```

The envelope has no authority by itself. `.terminus/q4_chat_human_risk.py` revalidates the human-decision ledger, current task snapshot and Q4 binding whenever the route is consumed.

## Human decision recovery rule

An unresolved decision is a real `HUMAN_DECISION_REQUIRED` stop condition, not a reason to invent or guess approval. A new task chat must recover the outstanding decision from `.terminus/human-decisions/<task>/ledger.jsonl`, present it again, and wait for an explicit response. Resolved decisions are reusable only for the exact commit-bound request they authorized.

External signed authority remains available for policies that explicitly require higher assurance. Routine Terminus risk acceptance should prefer the chat-human route when current policy permits it.

## Quality Interlock semantics

The Q4 side of Quality Interlock is satisfied by exactly one of four routes:

1. `DIRECT_PASS` — a current ordinary Q4 `PASS` under normal Protocol rules;
2. `ADJUDICATED_CLOSURE_PASS` — a final cold Q4 `REVISE` plus a current closure result that passes `.terminus/q4_closure.py` and `.terminus/validate_quality_interlock.py`;
3. `AUTHENTICATED_HUMAN_RISK_ACCEPTANCE` — a frozen Q4 `REVISE` plus exact externally authenticated human acceptance that passes `.terminus/q4_human_risk.py`; or
4. `CHAT_HUMAN_RISK_ACCEPTANCE` — a frozen Q4 `REVISE` plus an exact current same-chat decision that passes `.terminus/q4_chat_human_risk.py`.

The exceptional routes preserve the original Q4 verdict. Q6 and every other mandatory gate remain independently required and unchanged.

## Termination

A closure result containing any blocking disposition leaves the task `BLOCKED`. It does not authorize another normal Q4 patch cycle. Re-entry then requires a genuinely different strategy, new authority, or higher-precedence policy change. A valid human-risk decision is such a new authority only for the exact bound task/Q4 snapshot and accepted residual findings.
