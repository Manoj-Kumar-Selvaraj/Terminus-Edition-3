# Terminus Task Session

Session schema version: `2.4`

This is the durable operational checkpoint for one task. Keep it evidence-oriented. Current repository/rules/Git/CI/review provenance override stale prose.

## Identity

- Task: `jenkins-home-insights-plugin`
- Controller state: `FROZEN_CANDIDATE`
- Working branch: `main`
- Pull request: none
- Current task commit: `44fca100fb4572b286a4f42e15f35f928674dea5`
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
| Oracle = 1 | PASS | Harbor 0.21 job `jobs/2026-08-22__16-47-57` mean 1.000; 34/34 pytest passed |
| NOP = 0 | PASS | Harbor 0.21 job `jobs/2026-08-22__16-50-05` mean 0.000 |
| Q7 Task Format Enforcer | PASS | `.terminus/reviews/jenkins-home-insights-plugin/q7-format-check.md` |
| Q4 Spec-Test Contract Reviewer | PASS | `.terminus/reviews/jenkins-home-insights-plugin/44fca100/jenkins-home-insights-plugin-44fca100-spec-test-contract-14835af6d2.json` |
| Q6 Production Logic Auditor | PASS | `.terminus/reviews/jenkins-home-insights-plugin/44fca100/jenkins-home-insights-plugin-44fca100-production-logic-fd9810d5e3.json` scope `3df0c9d58d1b` |
| Quality Interlock | PASS | `.terminus/reviews/jenkins-home-insights-plugin/44fca100/quality-interlock.md` |
| Pre-LLMaJ panel | READY | generate specialist packets on `44fca100` |

## Q4 round-2 remediation @ 44fca100

1. **Generate sanitization** — `assert_exports_sanitized()` in `test_f2p_deterministic_10000_home_generation`
2. **Metadata contract** — api-v1.md documents principal, sort, direction ASC/DESC, visible, checkpoint

Prior round-1 probes (torn journal, contains, metadata keys, env paths, HTTP forbidden) remain at `63374113`.

## Next action

1. Generate Pre-LLMaJ specialist packets bound to `44fca100`.
2. Run Pre-LLMaJ panel → Q8 simulations → Harbor LLMaJ and official ×10.

## Decisions that must survive chat changes

- Do not redesign the task or weaken legitimate F2P requirements.
- Starter defects remain in `environment/plugin`; oracle copies `solution/fixed/` only.
- Q6 scope hash `3df0c9d58d1b` binds environment/ at `44fca100`; rerun Q6 if environment/ or task.toml changes.
