# Terminus Task Session

Session schema version: `2.4`

## Identity

- Task: `jenkins-home-insights-plugin`
- Controller state: `FROZEN_CANDIDATE`
- Working branch: `main`
- Pull request: none
- Current task commit: untracked (not yet committed)
- Agent-system policy: `2.5`
- Creation profile: `large_system_strict`

## CREATION_RULE_CONTEXT

```text
CREATION_PROFILE: large_system_strict
NETWORK/ENVIRONMENT_CONSTRAINTS: environment_mode=separate; network_mode=public; agent timeout 7200
KNOWN_POLICY_CONFLICTS: none
```

## Current gates

| Gate | Status | Evidence |
| --- | --- | --- |
| Defect topology | PASS | 29 defects, 7 RC, 34 edges |
| Environment complexity | PASS | substantive_loc=3245 |
| Creator complexity | PASS | 30 F2P / 4 P2P |
| Runtime authenticity | PASS | validate_runtime_authenticity.py |
| Ruff verifier | PASS | ruff 0.8.4 clean |
| Docker agent build | PASS | LF scripts; sleep infinity CMD |
| Oracle = 1 | PASS | `jobs/2026-08-22__13-17-32` — 34/34, reward 1.0 |
| NOP = 0 | PASS | `jobs/2026-08-22__13-20-18` — 20 fail / 14 pass; all P2P pass |
| Q7 format | PASS | `.terminus/reviews/jenkins-home-insights-plugin/q7-format-check.md` |
| Q4/Q6 quality interlock | PENDING | requires independent chats (not self-certified) |
| Pre-LLMaJ panel | PENDING | after Q4/Q6 |

## Harbor runtime notes (Windows)

- Use **stb-bundled Harbor 0.21** for `environment_mode=separate`.
- `./terminus3.sh oracle|nop jenkins-home-insights-plugin` when bash/WSL available.

## Latest validation (empirical)

- Oracle: **34 passed** in 81.76s
- NOP: **20 failed, 14 passed**; all `test_p2p_*` pass on starter

## Next action

1. Run **Q4** and **Q6** quality interlock in **separate, fresh chats** (platform policy — do not self-certify).
2. Generate Pre-LLMaJ specialist packets after interlock passes.
3. Commit task tree when user requests.

## Decisions that must survive chat changes

- Do not redesign the task or weaken legitimate F2P requirements.
- Starter defects remain in `environment/plugin`; oracle copies `solution/fixed/` only.
- Jenkins-owned home stays read-only; `/app/plugin` artifact path unchanged.
