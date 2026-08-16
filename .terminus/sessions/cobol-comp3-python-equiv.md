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
| Q1 Spec Gap Repair | PASS | fresh independent direct Q1 execution at task commit `bb2e042c45873da3f3d78836d915ddb6446debf2`: `STATUS=NO_GAP`, requirement completeness `SUFFICIENT`, instruction shape `PASS`, instruction/docs boundary `CLEAN`, handoff `PASS`, reverse-outline risk `LOW`; live task SHA reverified unchanged after execution |
| Q2 Verifier Coverage Repair | REPAIR_PROPOSED | frozen direct diagnostic `.terminus/reviews/cobol-comp3-python-equiv/bb2e042c/cobol-comp3-python-equiv-bb2e042c-q2-verifier-coverage-direct-20260816.md`; task files unchanged; adjudication pending under packet `.terminus/reviews/cobol-comp3-python-equiv/bb2e042c/cobol-comp3-python-equiv-bb2e042c-adjudication-1cb69323e3.packet.json` |
| Q3 Spec Ambiguity Repair | PENDING | held until Q2-vs-closure conflict is adjudicated |
| Q7 Task Format Enforcer | PENDING | held until Q2-vs-closure conflict is adjudicated |
| Deterministic closure Oracle | PASS | run `31943332388`, job `95155548440`: `40 passed in 6.09s` |
| Deterministic closure NOP | PASS | run `31943332388`, job `95155548440`: `30 failed, 10 passed in 3.05s` |
| Q4 Spec-Test Contract Reviewer | REVISE | frozen final Q4: `.terminus/reviews/cobol-comp3-python-equiv/bb2e042c/cobol-comp3-python-equiv-bb2e042c-spec-test-contract-852fc1b28a.json` |
| Q4 Adjudicated Closure | PASS | `.terminus/reviews/cobol-comp3-python-equiv/bb2e042c/cobol-comp3-python-equiv-bb2e042c-q4-closure-adjudication-c00658ae75.json`; deterministic closure-chain validation PASS in run `31953426334`, job `95180306897` |
| Q6 Production Logic Auditor | PASS | `.terminus/reviews/cobol-comp3-python-equiv/02a558ab/cobol-comp3-python-equiv-02a558ab-production-logic-80ad7c5258.json`; Protocol-2.2 scope reuse accepted by the repository validator from task commit `02a558ab...` to `bb2e042c...` because the validated production `review_scope_hash` is unchanged |
| Quality Interlock | BLOCKED | Q4 is satisfied through `ADJUDICATED_CLOSURE_PASS`, Q6 is current by scope reuse and Q1 is complete; Q2 returned `REPAIR_PROPOSED` and is now routed to independent packet-bound Adjudication before any task edit or later producer gate |

## Current blocker

The Protocol-2.2 Q4 circuit-breaker closure is resolved. The frozen final Q4 remains `REVISE`, while the independent Q4 Closure Adjudicator result is `PASS/HIGH/SUFFICIENT` and explicitly says not to reopen `REJECTED_SCOPE_REOPEN` or `LATENT_AFTER_BOUNDARY` as another ordinary task patch loop.

Q1 is complete on the unchanged final task candidate. Fresh Q2 then returned `REPAIR_PROPOSED` without modifying task files. Its frozen diagnostic is `.terminus/reviews/cobol-comp3-python-equiv/bb2e042c/cobol-comp3-python-equiv-bb2e042c-q2-verifier-coverage-direct-20260816.md`. Its proposed verifier additions include several semantic families already addressed by the frozen boundary/closure, plus other possible distinct coverage concerns that require independent scope classification rather than an Orchestrator waiver.

Protocol 2.2 requires Adjudication when a proposed fix trades one gate against another, when reviewer/quality conclusions materially conflict, or when a latent/unchanged-scope finding appears after the no-drip boundary. The Orchestrator therefore cannot mark Q2 PASS, cannot implement Q2-S01..Q2-S12, and cannot continue to Q3 yet.

A repository-generated schema-v3 Adjudicator packet is now frozen at `.terminus/reviews/cobol-comp3-python-equiv/bb2e042c/cobol-comp3-python-equiv-bb2e042c-adjudication-1cb69323e3.packet.json`. Its canonical output path `.terminus/reviews/cobol-comp3-python-equiv/bb2e042c/cobol-comp3-python-equiv-bb2e042c-adjudication-1cb69323e3.json` was live-verified absent after packet freeze. Packet generation run `31957254650`, job `95189648642` passed all guards; task SHA remained exactly `bb2e042c45873da3f3d78836d915ddb6446debf2`.

## Required strategy change

Keep the task frozen and execute the packet-bound independent Adjudicator. The Adjudicator must reconcile the Q2 diagnostic against the frozen `59dcf214` Adjudicator boundary, final frozen Q4, Q4 Closure PASS/policy, current authoritative rules and current verifier/task evidence. It must determine which Q2 proposed scenario/requirement clusters are legitimately controlling current blockers versus rejected-scope reopenings/latent-after-boundary learning debt, whether any genuinely distinct Q2 blocker remains that authorizes bounded verifier repair, and what exact controller disposition is valid for the mandatory Q2 producer gate.

If a genuinely controlling Q2 blocker survives, strategy/policy re-entry is required before task repair because ordinary post-closure patching is not automatically authorized. If none survives, the controller still needs an authoritative representation for satisfying the mandatory Q2 producer gate; the current Quality Interlock validator accepts only literal producer-gate `PASS` and has no adjudicated-Q2 exception.

## Next action

Open a fresh independent Adjudicator chat using `.terminus/reviews/cobol-comp3-python-equiv/bb2e042c/cobol-comp3-python-equiv-bb2e042c-adjudication-1cb69323e3.packet.json`. Before semantic adjudication, verify the current Git-derived task SHA is still `bb2e042c45873da3f3d78836d915ddb6446debf2`, the packet exists with `control_plane_commit=ecdce8dde4ce08a6e3cf5357e9085cbc76bd116b` and `role_contract_hash=ae7523f7674adecdb0ca242024e8ee1cc0483105b249621469ec288184485cca`, and the packet-specified result path does not already exist. Do not modify task files and do not advance Q3/Q7 until that result returns to the Orchestrator.

## Decisions that must survive chat changes

- Q4 circuit-breaker closure is complete and deterministically valid; do not start another Q4 patch loop.
- Preserve the frozen final Q4 as `REVISE`; Q4 satisfaction is the separate `ADJUDICATED_CLOSURE_PASS` route.
- Preserve the frozen Adjudicator's rejected/narrowed scopes and the closure's `REJECTED_SCOPE_REOPEN` / `LATENT_AFTER_BOUNDARY` dispositions.
- Q6 remains reusable only while its exact production-scope hash and Q6 role contract remain current; the repository validator accepted reuse for the current candidate.
- Q1 is complete: fresh direct execution returned `NO_GAP` on unchanged task commit `bb2e042c45873da3f3d78836d915ddb6446debf2`.
- Q2 is not PASS: frozen direct execution returned `REPAIR_PROPOSED`; no task files were modified.
- Q2 conflict packet: `.terminus/reviews/cobol-comp3-python-equiv/bb2e042c/cobol-comp3-python-equiv-bb2e042c-adjudication-1cb69323e3.packet.json`.
- Do not implement Q2 repairs or advance Q3/Q7 until the Q2-vs-closure semantic conflict is independently adjudicated.
- Quality Interlock remains BLOCKED.
