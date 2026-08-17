# Terminus Task Session

Session schema version: `2.4`

This is the durable operational checkpoint for one task. Keep it evidence-oriented. Current repository/rules/Git/CI/review provenance override stale prose.

## Identity

- Task: `event-time-session-window-processor`
- Controller state: `FROZEN_CANDIDATE`
- Working branch: `main`
- Pull request: `none`
- Current task commit: `pending freeze after catalog COUNT(*) assert`
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
| Creator Complexity Gate | PASS | 25 F2P / 15 P2P |
| Runtime authenticity | PASS | 12000 click_event rows |
| Q6 on 4927f2e | PASS | independent LOC 3122; PADDING MEDIUM; TOY LOW; reusable if environment hash unchanged |
| Q4 on 4927f2e | REVISE | Q4-B01 COUNT(*) not bound — patched in tests only |
| Ruff verifier | PASS | tests/test_outputs.py |
| Oracle = 1 | PASS | Harbor `/tmp/e3-ets/2026-08-17__13-59-38` reward 1.0 |
| NOP = 0 | PASS | Harbor `/tmp/e3-ets/2026-08-17__14-00-43` reward 0.0 |
| Quality interlock | PENDING | Q4 re-review after COUNT(*) freeze; Q6 reuse if scope hash matches |
| Harbor LLMaJ | DEFERRED | user-deferred unless asked |
| Difficulty trials | DEFERRED | user-deferred unless asked |

## Current blocker

Q4 REVISE on 4927f2e: ops counts must equal SELECT COUNT(*) FROM click_event. Tests-only patch. Environment unchanged so Q6 PASS may reuse.

## Decisions that must survive chat changes

- Profile `large_system_strict`; Software/Systems; artifacts `["/app/sessions"]`.
- Planted defects unchanged.
- last_run.warehouse.event_count and ops-report.inventory.event_count equal catalog click_event COUNT(*).
- Harbor LLMaJ and official GPT×5/Claude×5 deferred unless asked.
- Leave unrelated dirty work untouched (including jetstream).

## Resume rule

A new controller follows `.terminus/CONTINUE_SESSION.md`, reconciles this checkpoint with Git and live CI/artifact/review provenance, and corrects stale state before changing the task.
