# Terminus Task Session

Session schema version: `2.4`

## Identity

- Task: `cobol-comp3-python-equiv`
- Controller state: `BLOCKED`
- Working branch: `task/cobol-comp3-python-equiv-strict-rebuild`
- Pull request: `#23`
- Current task commit: `bb2e042c45873da3f3d78836d915ddb6446debf2`
- Agent-system policy: `2.5`
- Specialist prompt policy: `2.2`
- Specialist protocol policy: `2.2`
- Pre-LLMaJ panel policy: `2.2`
- Comprehensive reviewer policy: `1.0`
- Reviewer checklist snapshot: `2026-08-08-user-supplied`

## Current task profile

Large-system-strict warehouse inventory cutover task: legacy COBOL packed-decimal movement feed to restartable Python equivalence runtime with public CLI, durable SQLite state, replay/recovery, reconciliation/publication and operator preflight/audit/archive workflows.

## Current gates

| Gate | Status | Evidence / version |
| --- | --- | --- |
| Deterministic closure Oracle | PASS | run `31943332388`, job `95155548440`: `40 passed in 6.09s` |
| Deterministic closure NOP | PASS | run `31943332388`, job `95155548440`: `30 failed, 10 passed in 3.05s` |
| Q4 Spec-Test Contract Reviewer | REVISE | `.terminus/reviews/cobol-comp3-python-equiv/bb2e042c/cobol-comp3-python-equiv-bb2e042c-spec-test-contract-852fc1b28a.json` |
| Q4 Adjudicated Closure | PENDING | generate a current `Q4 Closure Adjudicator` packet under Q4_CLOSURE_POLICY.md |
| Q6 Production Logic Auditor | PASS / scope-reusable | existing Q6 production scope unchanged because `task.toml` and `environment/**` did not change |
| Quality Interlock | BLOCKED | decisive post-circuit-breaker Q4 remains `REVISE` |

## Current blocker

Protocol-2.2 circuit breaker is active. The frozen Adjudicator result `.terminus/reviews/cobol-comp3-python-equiv/59dcf214/cobol-comp3-python-equiv-59dcf214-adjudication-516e0ca6b1.json` authorized one final non-blind closure repair followed by one fresh exhaustive Q4 and states that survival of any same adjudicated semantic blocker triggers `BLOCKED/strategy redesign` rather than another normal repair cycle.

The decisive Q4 at task commit `bb2e042c45873da3f3d78836d915ddb6446debf2` returned `REVISE/HIGH/SUFFICIENT` with Q4-001..Q4-005. Several demands materially overlap scopes previously rejected or narrowed by the frozen Adjudicator, including blanket private `src.*` API prohibition, per-safety-subclass publication expansion, and corrupt archive-input testing. No further task repair or ordinary Q4 rerun is authorized under the current strategy.

## Required strategy change

Use the committed Q4 adjudicated-closure strategy. Ordinary Q4 remains frozen at `REVISE`; re-entry is through a dedicated `Q4 Closure Adjudicator` packet that binds the frozen boundary adjudication, final Q4, exact final repair diff and deterministic finding fingerprints. Rejected-scope reopen and latent-after-boundary findings cannot silently restart task repair, while surviving bound blockers, repair regressions, genuinely new evidence and authoritative-rule conflicts remain blocking.

## Next action

Do not modify `cobol-comp3-python-equiv/**`. After deterministic control-plane validation, generate the exact current Q4 closure packet and route it to a fresh independent `Q4 Closure Adjudicator`. Do not rerun Q4 or repair the five decisive Q4 findings before that closure decision.

## Decisions that must survive chat changes

- Do not start another blind Q4 patch loop.
- Do not repair the decisive Q4 findings directly under the current Protocol-2.2 strategy.
- Preserve the frozen Adjudicator's rejected/narrowed scopes.
- Q6 remains reusable only while its exact production-scope hash remains unchanged.
- Learning-system improvements remain desirable, but the immediate blocker is Q4 closure/termination semantics.
