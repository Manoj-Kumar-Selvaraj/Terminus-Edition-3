# Terminus Task Session

Session schema version: `2.4`

This is the durable operational checkpoint for one task. Keep it evidence-oriented. Current repository/rules/Git/CI/review provenance override stale prose.

## Identity

- Task: `event-time-session-window-processor`
- Controller state: `FROZEN_CANDIDATE`
- Working branch: `main`
- Pull request: `none`
- Current task commit: `pending freeze after Q4-B01/B02 patch`
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
| Q6 on dafc1da | PASS | independent LOC 3263; PADDING MEDIUM; TOY LOW |
| Q4 on dafc1da | REVISE | Q4-B01 detail tokens; Q4-B02 nested ops schema — patched on working tree |
| Ruff verifier | PASS | tests/test_outputs.py |
| Oracle = 1 | PASS | Harbor `/tmp/e3-ets/2026-08-17__13-49-36` reward 1.0 (post-patch) |
| NOP = 0 | PASS | Harbor `/tmp/e3-ets/2026-08-17__13-50-53` reward 0.0 (post-patch) |
| Quality interlock | PENDING | needs independent Q4+Q6 PASS on the same freeze |
| Harbor LLMaJ | DEFERRED | user-deferred unless asked |
| Difficulty trials | DEFERRED | user-deferred unless asked |

## Current blocker

Q4 REVISE on dafc1da is patched (reject event_id classes; last_run/ops-report schema in session-contract.md; drop unused free-plan overlay). Environment change invalidates Q6 reuse. Re-freeze and re-issue Q4+Q6.

## Decisions that must survive chat changes

- Profile `large_system_strict`; Software/Systems; artifacts `["/app/sessions"]`.
- Planted defects unchanged: session_key, watermark last-write, record-before-classify, arrival gap, journal overwrite, CLI mutate-before-parse.
- Oracle copies: session_key, journal, pipeline, cli, watermark_track.
- Catalog enterprise overlay 45000; no free-plan overlay.
- last_run.warehouse.event_count and ops-report catalog.available + inventory.event_count are public contract fields.
- Harbor LLMaJ and official GPT×5/Claude×5 deferred unless asked.
- Leave unrelated dirty work untouched (including jetstream).

## Resume rule

A new controller follows `.terminus/CONTINUE_SESSION.md`, reconciles this checkpoint with Git and live CI/artifact/review provenance, and corrects stale state before changing the task.
