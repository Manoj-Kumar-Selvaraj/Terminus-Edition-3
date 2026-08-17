# Terminus Task Session

Session schema version: `2.4`

This is the durable operational checkpoint for one task. Keep it evidence-oriented. Current repository/rules/Git/CI/review provenance override stale prose.

## Identity

- Task: `event-time-session-window-processor`
- Controller state: `FROZEN_CANDIDATE`
- Working branch: `main`
- Pull request: `none`
- Current task commit: `pending freeze commit`
- Agent-system policy: `2.4`
- Specialist prompt policy: `2.2`
- Specialist protocol policy: `2.2`
- Pre-LLMaJ panel policy: `2.2`
- Comprehensive reviewer policy: `1.0`
- Reviewer checklist snapshot: `2026-08-08-user-supplied`

## CREATION_RULE_CONTEXT

```text
CONTROL_PLANE_COMMIT: live HEAD
CREATION_PROFILE: large_system_strict
NETWORK_MODE: public
KNOWN_POLICY_CONFLICTS: none
```

## Current gates

| Gate | Status | Evidence / version |
| --- | --- | --- |
| Creator Complexity Gate | PASS | 25 F2P / 11 P2P; 25 defects; 6 root causes; loc includes generated seed.sql |
| Runtime authenticity | PASS | 12000 click_event rows; notes+log evidence |
| Q1 Spec Gap Repair | REPAIR_PROPOSED | `.terminus/reviews/event-time-session-window-processor/q1-spec-gap.md` |
| Q2 Verifier Coverage Repair | COVERED | `.terminus/reviews/event-time-session-window-processor/q2-coverage.md` |
| Q3 Spec Ambiguity Repair | REPAIR_PROPOSED | `.terminus/reviews/event-time-session-window-processor/q3-ambiguity.md` |
| Q7 Task Format Enforcer | FORMAT_PASS | `.terminus/reviews/event-time-session-window-processor/q7-format-check.md` |
| Ruff verifier | PASS | `python -m ruff check event-time-session-window-processor/tests/test_outputs.py` |
| Oracle = 1 | PASS | Harbor `/tmp/e3-ets/2026-08-17__12-13-37` reward 1.0 |
| NOP = 0 | PASS | Harbor `/tmp/e3-ets/2026-08-17__12-14-37` reward 0.0 |
| Q4 Spec-Test Contract | PENDING | packet after freeze |
| Q6 Production Logic | PENDING | packet after freeze |
| Quality interlock | PENDING | needs independent Q4+Q6 PASS |
| Pre-LLMaJ | PENDING | after QUALITY_INTERLOCK_PASS |
| Q8 GPT/Claude sim | PENDING | after PRE_LLMAJ |
| Harbor LLMaJ | DEFERRED | user-deferred unless asked |
| Difficulty trials | DEFERRED | user-deferred unless asked |

## Current blocker

Independent Q4/Q6 after freeze. Q6 is expected to scrutinize seed.sql LOC padding.

## Decisions that must survive chat changes

- Profile `large_system_strict`; Software/Systems; artifacts `["/app/sessions"]`.
- Domain: event-time session windows with allowed lateness, tenant isolation, journal restart.
- Planted defects: session_key drops tenant; watermark last-write-wins + classify after record; arrival-index gap; journal overwrite seq=1; CLI mutates before parse and reset clears journal.
- Oracle copies: session_key, journal, pipeline, cli, watermark_track.
- Q5: CRLF shebangs on solve.sh/test.sh/run-sessions caused Harbor 127; LF + `.gitattributes`.
- Harbor LLMaJ and official GPT×5/Claude×5 deferred unless the user asks.
- Leave unrelated dirty work untouched.

## Resume rule

A new controller follows `.terminus/CONTINUE_SESSION.md`, reconciles this checkpoint with Git and live CI/artifact/review provenance, and corrects stale state before changing the task.
