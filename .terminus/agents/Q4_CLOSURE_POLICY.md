# Q4 Closure and Human Risk-Acceptance Policy

Policy version: `1.1`

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

## Authenticated human risk acceptance

`AUTHENTICATED_HUMAN_RISK_ACCEPTANCE` is a separate satisfaction authority for an exact frozen Q4 `REVISE`. It is not a Q4 PASS, reviewer override, or Orchestrator waiver.

It is valid only when all of the following are true:

- the authority artifact is a canonical feedback event in the append-only feedback registry;
- the event source is `HUMAN_REVIEW` and provenance is `HUMAN_AUTHENTICATED`;
- the authority receipt validates for action `HUMAN_FEEDBACK` and the exact human principal;
- the feedback category is exactly `HUMAN_RISK_ACCEPTANCE` and `stage_hint` is `QUALITY_INTERLOCK`;
- the event binds the exact task ID and exact task commit of the frozen Q4 result;
- the signed decision is `ACCEPTED`, while `q4_verdict` remains exactly `REVISE`;
- the event binds the exact frozen Q4 `review_id`;
- `accepted_finding_ids` exactly equals the frozen Q4 blocking-finding set;
- `residual_backlog` is non-empty and remains durable as accepted unresolved risk;
- the human producer is not any registered Terminus machine/agent role;
- the referenced feedback event is revalidated every time the satisfaction route is consumed.

A task-commit change makes the acceptance stale. A receipt or feedback event for another task, commit, Q4 review, category, finding set, or decision cannot be reused. The CI Orchestrator may consume and validate this authority, but may not manufacture it.

The canonical lifecycle representation remains:

```text
Q4 verdict: REVISE
Q4 satisfaction: AUTHENTICATED_HUMAN_RISK_ACCEPTANCE
Q4 Human Risk Acceptance: PASS
```

The `Q4_CLOSURE_RESULT` optional stage-output field is also the compatibility envelope for exceptional Q4-satisfaction evidence. For this human route it contains only the authority locator:

```json
{
  "type": "AUTHENTICATED_HUMAN_RISK_ACCEPTANCE",
  "feedback_id": "feedback_<sha256>"
}
```

The envelope itself has no authority. `.terminus/q4_human_risk.py` resolves and revalidates the signed feedback event before advancement.

## Quality Interlock semantics

The Q4 side of Quality Interlock is satisfied by exactly one of three routes:

1. `DIRECT_PASS` — a current ordinary Q4 `PASS` under normal Protocol rules;
2. `ADJUDICATED_CLOSURE_PASS` — a final cold Q4 `REVISE` plus a current closure result that passes `.terminus/q4_closure.py` and `.terminus/validate_quality_interlock.py`; or
3. `AUTHENTICATED_HUMAN_RISK_ACCEPTANCE` — a frozen Q4 `REVISE` plus exact authenticated human acceptance that passes `.terminus/q4_human_risk.py` and `.terminus/validate_quality_interlock.py`.

The two exceptional routes preserve the original Q4 verdict. Q6 and every other mandatory gate remain independently required and unchanged.

## Termination

A closure result containing any blocking disposition leaves the task `BLOCKED`. It does not authorize another normal Q4 patch cycle. Re-entry then requires a genuinely different strategy, new authority, or higher-precedence policy change. A valid authenticated human-risk decision is such a new authority only for the exact signed task/Q4 snapshot and accepted residual findings.
