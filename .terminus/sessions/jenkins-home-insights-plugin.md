# Terminus Task Session

Session schema version: `2.4`

This is the durable operational checkpoint for one task. Keep it evidence-oriented. Current repository/rules/Git/CI/review provenance override stale prose.

## Identity

- Task: `jenkins-home-insights-plugin`
- Controller state: `FROZEN_CANDIDATE`
- Working branch: `main`
- Pull request: none
- Current task commit: `0766c0a2cb6b666c72f111ef49f3a8724d46ba42`
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
| Defect topology | PASS | validate_defect_topology — 29 defects, 7 RC, 34 edges |
| Environment complexity | PASS | substantive_loc=3245 |
| Creator complexity | PASS | 30 F2P / 4 P2P |
| Runtime authenticity | PASS | validate_runtime_authenticity.py |
| Ruff verifier | PASS | `uvx ruff==0.8.4 check tests/test_outputs.py` run 1 — All checks passed |
| Oracle = 1 | PASS | Harbor 0.21 job `jobs/2026-08-22__13-17-32` mean 1.000; 34/34 pytest passed |
| NOP = 0 | PASS | Harbor 0.21 job `jobs/2026-08-22__13-20-18` mean 0.000; 20 failed / 14 passed |
| Q7 Task Format Enforcer | PASS | `.terminus/reviews/jenkins-home-insights-plugin/q7-format-check.md` FORMAT_PASS |
| Q4 Spec-Test Contract Reviewer | REVISE | `.terminus/reviews/jenkins-home-insights-plugin/0766c0a2/jenkins-home-insights-plugin-0766c0a2-spec-test-contract-7aafeea56c.json` HIGH SUFFICIENT; blocking Q4-B01..Q4-B05 |
| Q6 Production Logic Auditor | PASS | `.terminus/reviews/jenkins-home-insights-plugin/0766c0a2/jenkins-home-insights-plugin-0766c0a2-production-logic-63d408fd36.json` HIGH SUFFICIENT; scope `6a41990f5457` |
| Quality Interlock | FAIL | `.terminus/reviews/jenkins-home-insights-plugin/0766c0a2/quality-interlock.md` — Q4 REVISE blocks |
| Pre-LLMaJ panel | BLOCKED | until Q4 PASS + quality interlock PASS |

## Q4 blocking findings (remediation queue)

1. **Q4-B01** — torn journal final record / valid prefix preservation (storage.md + instruction)
2. **Q4-B02** — `contains` query filter untested (api-v1.md)
3. **Q4-B03** — required query `metadata` field untested (api-v1.md)
4. **Q4-B04** — `JENKINS_HOME` / `INSIGHTS_STATE` env path overrides untested (operations.md)
5. **Q4-B05** — HTTP standalone unauthorized rejection untested (instruction + api-v1)

## Next action

1. Add F2P probes in `tests/test_outputs.py` for Q4-B01..B05 (Verifier Author / Q2 route).
2. Rerun Harbor oracle=1 and NOP=0 on new task commit.
3. Regenerate Q4 packet and rerun cold Q4 review; advance to PRE_LLMAJ when interlock PASS.

## Decisions that must survive chat changes

- Do not redesign the task or weaken legitimate F2P requirements.
- Starter defects remain in `environment/plugin`; oracle copies `solution/fixed/` only.
- Q6 PASS at `0766c0a2` is scope-preserved until `task.toml` or `environment/` changes.
