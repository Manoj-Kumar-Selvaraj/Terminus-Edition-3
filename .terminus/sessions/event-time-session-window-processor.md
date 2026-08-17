# Terminus Task Session

Session schema version: `2.4`

This is the durable operational checkpoint for one task. Keep it evidence-oriented. Current repository/rules/Git/CI/review provenance override stale prose.

## Identity

- Task: `event-time-session-window-processor`
- Controller state: `FROZEN_CANDIDATE`
- Working branch: `main`
- Pull request: `none`
- Current task commit: `069b0f2e56b11eb0fda344a82c8b50e0461d6755`
- Agent-system policy: `2.5`
- Specialist prompt policy: `2.2`
- Specialist protocol policy: `2.2`
- Pre-LLMaJ panel policy: `2.2`
- Comprehensive reviewer policy: `1.0`
- Reviewer checklist snapshot: `2026-08-08-user-supplied`

## CREATION_RULE_CONTEXT

```text
CONTROL_PLANE_COMMIT: 8ade8b91d26bee3dfcd6dc56e1bca8543f26378f
CREATION_PROFILE: large_system_strict
NETWORK_MODE: public
KNOWN_POLICY_CONFLICTS: none
```

## Current gates

| Gate | Status | Evidence / version |
| --- | --- | --- |
| Q1 Spec Gap Repair | PASS | `.terminus/reviews/event-time-session-window-processor/q1-spec-gap.md` |
| Q2 Verifier Coverage Repair | REPAIR_PROPOSED | VE-01..VE-03 and CR-01/CR-02 applied; recheck after freeze |
| Q3 Spec Ambiguity Repair | PASS | `.terminus/reviews/event-time-session-window-processor/q3-ambiguity.md` |
| Q7 Task Format Enforcer | PASS | layout/Docker unchanged; oracle CLI + tests only |
| Creator Complexity Gate | PASS | local validator; 27 F2P / 15 P2P |
| Runtime authenticity | PASS | 12000 click_event rows |
| Ruff verifier | PASS | `tests/test_outputs.py` and `solution/fixed/cli.py` clean |
| Oracle = 1 | STALE | last Harbor `/tmp/e3-ets/2026-08-17__15-46-13`; rerun after freeze |
| NOP = 0 | STALE | last Harbor `/tmp/e3-ets/2026-08-17__15-47-24`; rerun after freeze |
| Freeze | PASS | `069b0f2e56b11eb0fda344a82c8b50e0461d6755` |
| Q4 Spec-Test Contract Reviewer | STALE | tests/oracle changed; `3fec54c` Q4 historical |
| Q6 Production Logic Auditor | PASS | environment/task.toml unchanged; scope reuse still eligible |
| Quality Interlock | STALE | Q4 stale after producer repair |
| Instruction Reviewer | PASS | `3fec54c` `...-instruction-21c452f480.json`; instruction.md not edited this cycle |
| Documentation Reviewer | PASS | `3fec54c` `...-documentation-e12cdcdf16.json`; README not edited this cycle |
| Verifier Engineer | REVISE | Adjudicator `b229a618a5` controls VE-01..VE-03; same-path later PASS overwrite is not a new packet |
| Comprehensive Reviewer | REQUEST_CHANGES | Adjudicator controls CR-01 CR-02; same-path later APPROVE overwrite is not a new packet |
| Adjudicator | REQUEST_CHANGES | `.terminus/reviews/event-time-session-window-processor/3fec54c6/event-time-session-window-processor-3fec54c6-adjudication-b229a618a5.json` HIGH |
| Pre-LLMaJ aggregate | REVISE | controlling findings still open until refreeze + cold re-review |
| Q8 GPT/Claude | STALE | diagnostics were bound to `3fec54c`; task tree moving |
| Harbor LLMaJ | DEFERRED | user-deferred unless asked |
| Difficulty trials | DEFERRED | user-deferred unless asked |

## Current blocker

Frozen at `069b0f2e56b11eb0fda344a82c8b50e0461d6755`. Harbor oracle/NOP on this commit are pending, then cold Q4, Verifier, Comprehensive.

## Root-cause classification

- Owner: Q2 / Oracle Author
- Classification: verifier_gap, oracle_contract
- Evidence: Adjudicator `b229a618a5` REQUEST_CHANGES

## Next action

Harbor oracle 1 / NOP 0 on `069b0f2` with `JOBS_DIR=/tmp/e3-ets`. Then new Q4 packet (Q6 reuse if production scope hash still `c52a4631…`) and cold Verifier + Comprehensive. Do not edit instruction.md.

## Decisions that must survive chat changes

- Profile `large_system_strict`; Software/Systems; artifacts `["/app/sessions"]`.
- Planted starter defects unchanged (oracle copies five files only).
- last_run.warehouse.event_count and ops-report.inventory.event_count equal catalog click_event COUNT(*).
- Harbor LLMaJ and official GPT×5/Claude×5 deferred unless asked.
- Leave unrelated dirty work untouched (including jetstream and cobol-comp3).
- Do not count `sql/seed.sql` or `warehouse/click_ledger.jsonl` toward Q6 LOC.
- Do not add `task.toml` explanation fields.
- Do not majority-vote a later same-path PASS/APPROVE overwrite over Adjudicator `b229a618a5`. Controlling IDs: VE-01, VE-02, VE-03, CR-01, CR-02. VE-04..VE-07 advisory only.

## Resume rule

A new controller follows `.terminus/CONTINUE_SESSION.md`, reconciles this checkpoint with Git and live review provenance, and treats Adjudicator `b229a618a5` as controlling over any same-path later overwrite of Verifier/Comprehensive JSON.
