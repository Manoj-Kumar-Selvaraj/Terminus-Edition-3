# Terminus Task Session

Session schema version: `2.4`

## Identity

- Task: `codecommit-iam-merge-fence`
- Controller state: `FROZEN_CANDIDATE` (pending task-tree commit bind)
- Working branch: local rebuild under large_system_strict
- Pull request: none
- Current task commit: none (rebuild in progress; prior tip `1a50746e` superseded)
- Agent-system policy: `2.4`
- Specialist prompt policy: `2.2`
- Specialist protocol policy: `2.2`
- Pre-LLMaJ panel policy: `2.2`
- Comprehensive reviewer policy: `1.0`
- Reviewer checklist snapshot: `2026-08-08-user-supplied`

## CREATION_RULE_CONTEXT

```text
CONTROL_PLANE_COMMIT: 88e17620d0a13530127d61849557ec01ecdb1687
RULE_SOURCES:
  - TERMINUS_3_AI_INSTRUCTIONS.md
  - .terminus/AGENT_SYSTEM.md
  - .terminus/agents/CREATION_PIPELINE.md
  - .terminus/agents/CREATION_CONTROLLER.md
  - .terminus/agents/PRODUCTION_AUTHENTICITY.md
  - .terminus/agents/QUALITY_AGENT_REGISTRY.md
  - .terminus/agents/INSTRUCTION_POLICY.md
  - .terminus/reviewers/REVIEWER_CHECKLIST.md
ACTIVE_VALIDATORS:
  - .terminus/validate_task_complexity.py
  - .terminus/validate_runtime_authenticity.py
  - .terminus/validate_review_freshness.py
  - .terminus/validate_quality_interlock.py
  - ruff on tests/
CREATION_PROFILE: large_system_strict
NETWORK/ENVIRONMENT_CONSTRAINTS:
  network_mode: public
  environment_mode: separate
  artifacts: ["/app/codecommit"]
  workdir: /app/codecommit
  digest-pin canonical python:3.13-slim-bookworm
  tmux+asciinema required in agent image
KNOWN_POLICY_CONFLICTS: none
REBUILD_NOTE: prior non-strict ~633 LOC lab and uncommitted Q4 patches superseded; in-place scrap/rebuild
SUBAGENT_MODEL_POLICY: inherit/auto only — no premium model slugs
```

## Current gates

| Gate | Status | Evidence |
| --- | --- | --- |
| Rule Resolution | PASS | CREATION_RULE_CONTEXT pinned above |
| Work-Package Research | PASS | WP-C full control plane; research note on disk |
| System Architecture | PASS | `.terminus/designs/codecommit-iam-merge-fence.json` |
| Defect Topology | PASS | 28 defects / 7 RC / 30 edges |
| Environment Build | PASS | multi-package `environment/codecommit` |
| Oracle / Verifier / Instruction | PASS local | local oracle 35/35; NOP 27 fail / 8 pass |
| Complexity Gate | PASS | `substantive_loc=3097+`; F2P≈27 |
| Runtime Authenticity | PASS | production companion + 12k authz_events |
| Harbor Oracle/NOP | PASS | Oracle `jobs/2026-08-16__19-59-07` reward 1; NOP `jobs/2026-08-16__20-01-47` reward 0 |
| Quality Interlock | BLOCKED | needs clean task commit before Q4/Q6 packets |

## Current blocker

Task tree is dirty. Cold Q4/Q6 packets require a commit-bound freeze. Approve a git commit of `codecommit-iam-merge-fence/` (and related `.terminus/designs/*` companions) to proceed with auto-only Q4/Q6.
## Decisions that must survive chat changes

- Security / AppSec taxonomy.
- Profile is `large_system_strict` (no non-strict waiver).
- Rebuild in place; outbox is subordinate to CodeCommit deliver, not a reskin of webhook-outbox-delivery-plane.
- Auto/inherit only for all subagents — no premium credits.
