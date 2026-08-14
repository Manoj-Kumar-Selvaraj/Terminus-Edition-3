# Terminus Task Session

Session schema version: `2.4`

## Identity

- Task: `cobol-comp3-python-equiv`
- Controller state: `SPEC_ALIGNMENT`
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
| Q1 Spec Gap Repair | IN_PROGRESS | recovered contract plus signed/unsigned sign-class and storage-pad requirements |
| Q2 Verifier Coverage Repair | IN_PROGRESS | 22 F2P / 2 P2P mapped tests; current CI rerun pending after verifier-image packaging repair |
| Q3 Spec Ambiguity Repair | IN_PROGRESS | malformed sign class, storage pad, illegal sign nibble, ODO range, and record-boundary cases |
| Q7 Task Format Enforcer | PENDING | current-head CI evidence pending |
| Creator Complexity Gate | PENDING | task-specific run `31807846984` passed at prior head; rerun pending for current task commit |
| Preflight/static | PENDING | rerun pending for current task commit |
| Ruff verifier | PENDING | rerun pending for current task commit |
| Oracle = 1 | PENDING | prior run `31807847210` exposed verifier image packaging omission; fixed in `bf242838a5a985583d43e9ca919c03e4c3f9459d` |
| NOP = 0 | PENDING | fresh run waits on Oracle |
| Q4 Spec-Test Contract Reviewer | PENDING | generate only after one current exact-commit freeze |
| Q6 Production Logic Auditor | PENDING | generate only after one current exact-commit freeze |
| Quality Interlock | PENDING | bounded final Q4/Q6 interlock only; no recursive cold-review loop |

## Current deterministic evidence

- Reference public tape: PASS — two records, byte lengths `44` and `28`, summary flags true.
- Reference sealed holdout: PASS — two records, byte lengths `60` and `28`, negative/scaled COMP-3 and ODO behavior correct.
- Strict malformed COMP-3 probes: PASS — signed field rejects `F`; unsigned field rejects `C` and `D`; non-zero left storage pad is rejected while the parser preserves the 44-byte record boundary.
- Existing malformed fixtures: PASS — illegal sign and out-of-range ODO become record errors.
- Creator Complexity run `31807846984` evaluated this task as PASS at the immediately preceding head: 10 defects, 4 root causes, 9 causal edges, 24 mapped tests (22 F2P / 2 P2P). Its overall workflow failed later on unrelated `wiki-creation-counter-flap` baseline debt.
- Production Authenticity run `31807847016` failed before task inspection because live control-plane policy documents lack four markers required by `validate_production_policy.py`; this is repository baseline debt, not task evidence.
- Agent System run `31807847069` showed the known `platform-sonar-ingress-token-bind` quality-interlock baseline failure and review-freshness baseline debt. This session's noncanonical identity labels found in that run are corrected by this checkpoint.
- Edition-3 run `31807847210` passed preflight and Ruff but Oracle collected zero verifier tests because `tests/Dockerfile` did not copy the newly added `test_comp3_contract.py`. Commit `bf242838a5a985583d43e9ca919c03e4c3f9459d` changes the verifier image to copy all `test_*.py` files.

## Current blocker

Fresh Edition-3 Oracle/NOP evidence on `bf242838a5a985583d43e9ca919c03e4c3f9459d` or its task-equivalent current commit. Historical Harbor evidence at `32de80a57ddbc38acd33d36cac598c69abe99da8` remains stale and is not acceptance evidence.

## Next action

Use current PR #22 CI to verify the packaging repair. Repair only concrete task-owned deterministic failures. Once current Oracle=1 and NOP=0 are durable, mark Q1/Q2/Q3/Q7 complete, freeze once, and run the single bounded Q4/Q6 interlock required by the live workflow.

## Decisions that must survive chat changes

- Domain is warehouse catalog / SKU tape, not EOD payments.
- Verifier checks behavior and byte boundaries against sealed expected data; the reference implementation performs genuine COMP-3 decoding.
- Signed COMP-3 accepts `C/D`; unsigned COMP-3 accepts `F`; storage pad nibbles must be zero.
- REDEFINES aliases target storage and ODO consumes only the actual bounded count.
- Never reuse the old branch's Q4/Q6 packets or Harbor runs as fresh acceptance evidence.
- Do not self-certify independent Q4/Q6 results.
- Do not broaden this task to repair unrelated control-plane, `platform-sonar`, or `wiki-creation-counter-flap` baseline debt.
