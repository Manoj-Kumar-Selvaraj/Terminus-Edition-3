# Terminus Task Session

Session schema version: `2.4`

This is the durable operational checkpoint for one task. Keep it evidence-oriented. Current repository/rules/Git/CI/review provenance override stale prose.

## Identity

- Task: `jenkins-home-insights-plugin`
- Controller state: `FROZEN_CANDIDATE`
- Working branch: `main`
- Pull request: none
- Current task commit: `6337411350befd83359a8fef4c2bbddbc17ca366`
- Agent-system policy: `2.5`
- Specialist prompt policy: `2.2`
- Specialist protocol policy: `2.2`
- Pre-LLMaJ panel policy: `2.2`
- Comprehensive reviewer policy: `1.0`
- Creation profile: `large_system_strict`

## CREATION_RULE_CONTEXT

```text
CREATION_PROFILE: large_system_strict
NETWORK/ENVIRONMENT_CONSTRAINTS: environment_mode=separate; network_mode=public; agent timeout 7200
KNOWN_POLICY_CONFLICTS: none
```

## Current gates

| Gate | Status | Evidence / version |
| --- | --- | --- |
| Defect topology | PASS | 29 defects, 7 RC, 34 edges |
| Environment complexity | PASS | substantive_loc=3245 |
| Creator complexity | PASS | 30 F2P / 4 P2P |
| Runtime authenticity | PASS | validate_runtime_authenticity.py |
| Ruff verifier | PASS | ruff 0.8.4 clean |
| Oracle = 1 | PASS | Harbor 0.21 job `jobs/2026-08-22__16-30-30` mean 1.000; 34/34 pytest passed |
| NOP = 0 | PASS | Harbor 0.21 job `jobs/2026-08-22__16-32-25` mean 0.000 |
| Q7 Task Format Enforcer | PASS | `.terminus/reviews/jenkins-home-insights-plugin/q7-format-check.md` |
| Q4 Spec-Test Contract Reviewer | PENDING RERUN | prior REVISE at `0766c0a2` addressed by probe expansion @ `63374113` |
| Q6 Production Logic Auditor | PASS | `.terminus/reviews/jenkins-home-insights-plugin/0766c0a2/...production-logic-63d408fd36.json` scope `6a41990f5457` (reuse until environment/ changes) |
| Quality Interlock | PENDING RERUN | needs fresh cold Q4 on `63374113` |
| Pre-LLMaJ panel | BLOCKED | until quality interlock PASS |

## Q4 probe remediation @ 63374113

Expanded existing F2P tests (still 30 total):

1. **Q4-B01 torn journal** — `test_f2p_checkpoint_restart_replays_unpublished_tail_once` torn-tail sub-scenario
2. **Q4-B02 contains** — `test_f2p_stable_sorting_cursors_and_filter_errors`
3. **Q4-B03 metadata** — same test asserts `metadata` keys
4. **Q4-B04 env paths** — `test_f2p_readiness_and_supported_empty_home` via `JENKINS_HOME`/`INSIGHTS_STATE`
5. **Q4-B05 HTTP forbidden** — `test_f2p_cli_and_http_use_equivalent_shared_query_semantics`

Oracle fixes: isolate torn journal tail without aborting recovery; readiness when torn tail isolated and lag=0.

## Next action

1. Regenerate Q4 packet on `63374113` and rerun cold Q4 review.
2. Record quality interlock PASS → advance to Pre-LLMaJ panel.

## Decisions that must survive chat changes

- Do not redesign the task or weaken legitimate F2P requirements.
- Starter defects remain in `environment/plugin`; oracle copies `solution/fixed/` only.
- Q6 PASS at `0766c0a2` remains scope-valid until `task.toml` or `environment/` changes.
