# Terminus Task Session

Session schema version: `2.4`

## Identity

- Task: `cobol-comp3-python-equiv`
- Controller state: `FROZEN_CANDIDATE`
- Working branch: `task/cobol-comp3-python-equiv-completion`
- Pull request: `#22`
- Current task commit: `bf242838a5a985583d43e9ca919c03e4c3f9459d`
- Agent-system policy: `2.4`
- Specialist prompt policy: `2.2`
- Specialist protocol policy: `2.2`
- Pre-LLMaJ panel policy: `2.2`
- Comprehensive reviewer policy: `1.0`
- Creation Controller policy: `1.0`

## Current task profile

Software/Languages warehouse SKU tape unpacker for signed/unsigned COMP-3, REDEFINES, and OCCURS DEPENDING ON. Solver-visible runtime remains intentionally compact and uses the non-strict `large_system` authoring profile; do not pad LOC to satisfy scale diagnostics. Holdouts and malformed-record cases are verifier-only. No model API or GnuCOBOL runtime is required.

The abandoned branch `task/cobol-comp3-python-equiv@51723cbca1013fea7b1f7ca3cf0583af7182c785` was 483 commits behind current main. Useful task-only hardening was recovered onto the current branch; its old Q4/Q6 packets were not carried forward because they are commit-bound and stale.

## Current gates

| Gate | Status | Evidence / version |
| --- | --- | --- |
| Q1 Spec Gap Repair | PASS | task commit `bf242838a5a985583d43e9ca919c03e4c3f9459d`: contract reconciled for signed/unsigned sign class, zero storage pad, deterministic malformed-record byte boundaries, REDEFINES, and ODO |
| Q2 Verifier Coverage Repair | PASS | task commit `bf242838a5a985583d43e9ca919c03e4c3f9459d`: 24 mapped tests, 22 F2P / 2 P2P across six requirements; Oracle run `31808250840` job `94792334675` |
| Q3 Spec Ambiguity Repair | PASS | task commit `bf242838a5a985583d43e9ca919c03e4c3f9459d`: malformed sign class, storage pad, illegal sign nibble, ODO range, and record-boundary behavior made explicit and tested |
| Q7 Task Format Enforcer | PASS | Edition-3 run `31808250840` job `94792334675`: task format/preflight path accepted current task package |
| Creator Complexity Gate | PASS | run `31808250839` job `94792306458`: this task PASS with 10 defects, 4 root causes, 9 causal edges, 24 mapped tests; overall workflow later fails unrelated `wiki-creation-counter-flap` |
| Preflight/static | PASS | Edition-3 run `31808250840` job `94792334675` |
| Ruff verifier | PASS | Edition-3 run `31808250840` job `94792334675` |
| Oracle = 1 | PASS | Edition-3 run `31808250840` job `94792334675`, artifact `9222093520`: 24/24 tests pass, reward 1 |
| NOP = 0 | PASS | Edition-3 run `31808250840` job `94792334675`, artifact `9222093520`: 22 F2P fail / 2 P2P retention checks pass, reward 0 |
| Q4 Spec-Test Contract Reviewer | PENDING | one fresh packet/result required for exact task commit `bf242838a5a985583d43e9ca919c03e4c3f9459d` |
| Q6 Production Logic Auditor | PENDING | one fresh packet/result required for exact task commit `bf242838a5a985583d43e9ca919c03e4c3f9459d` |
| Quality Interlock | PENDING | one bounded Q4/Q6 interlock only; no recursive cold-review loop |

## Current deterministic evidence

- Reference public tape: PASS — two records, byte lengths `44` and `28`, summary flags true.
- Reference sealed holdout: PASS — two records, byte lengths `60` and `28`, negative/scaled COMP-3 and ODO behavior correct.
- Strict malformed COMP-3 probes: PASS — signed field rejects `F`; unsigned field rejects `C` and `D`; non-zero left storage pad is rejected while the parser preserves the 44-byte record boundary.
- Existing malformed fixtures: PASS — illegal sign and out-of-range ODO become record errors.
- Edition-3 run `31808250840` is exact current-head deterministic evidence: preflight PASS, Ruff PASS, Oracle PASS, NOP PASS. It turns red only at Harbor credential preparation because no Harbor API key/provider credential is configured.
- Creator Complexity run `31808250839` explicitly evaluates `cobol-comp3-python-equiv` as PASS: 10 defects, 4 root-cause clusters, 9 causal edges, 24 mapped tests (22 F2P / 2 P2P). Its overall workflow fails later on unrelated `wiki-creation-counter-flap` baseline debt.
- Agent System run `31808250834` has no freshness error for this task after the schema repair. Its regression failure is the existing `platform-sonar-ingress-token-bind` Q1/Q2/Q3/Q7 state; its review-freshness errors are other stale sessions/tasks.
- Production Authenticity remains repository baseline debt: the workflow fails before task inspection because current control-plane policy documents lack markers required by `validate_production_policy.py`.
- Historical Harbor evidence at `32de80a57ddbc38acd33d36cac598c69abe99da8` remains stale and is not used for this freeze.

## Current blocker

The frozen candidate needs exactly one current, packet-bound Q4 Spec-Test Contract review and one current, packet-bound Q6 Production Logic audit. Model-based Harbor validation is separately blocked by missing CI credentials and is not being misrepresented as complete.

## Next action

Generate fresh Q4 and Q6 packets for exact task commit `bf242838a5a985583d43e9ca919c03e4c3f9459d`, then obtain the single independent results required by the bounded quality interlock. Do not modify the task tree after freeze unless a concrete blocking defect is proven; any such change invalidates this freeze and its review binding.

## Decisions that must survive chat changes

- Domain is warehouse catalog / SKU tape, not EOD payments.
- Verifier checks behavior and byte boundaries against sealed expected data; the reference implementation performs genuine COMP-3 decoding.
- Signed COMP-3 accepts `C/D`; unsigned COMP-3 accepts `F`; storage pad nibbles must be zero.
- REDEFINES aliases target storage and ODO consumes only the actual bounded count.
- Never reuse the old branch's Q4/Q6 packets or Harbor runs as fresh acceptance evidence.
- Do not self-certify independent Q4/Q6 results.
- Do not broaden this task to repair unrelated control-plane, `platform-sonar`, `wiki-creation-counter-flap`, Production Authenticity policy-marker, or global review-freshness baseline debt.
- This task gets one bounded Q4/Q6 interlock, not an open-ended cold-review/remediation loop.
