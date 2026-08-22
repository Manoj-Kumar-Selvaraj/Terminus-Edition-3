# Terminus Task Session

Session schema version: `2.4`

## Identity

- Task: `sovereign-l4-load-balancer`
- Controller state: `SUBMISSION_READY`
- Working branch: `local`
- Pull request: `none`
- Current task commit: `uncommitted local assembly`
- Agent-system policy: `2.5`

## Current gates

| Gate | Status | Evidence / version |
| --- | --- | --- |
| Creator Complexity Gate | PASS | `validate_task_complexity.py`: 3015 LOC, 28 F2P cases, 29 defects |
| Environment Complexity Gate | PASS | `validate_environment_complexity.py` |
| Defect Topology Gate | PASS | `validate_defect_topology.py`: 29 defects, 7 RC clusters |
| Runtime Authenticity Gate | PASS | `validate_runtime_authenticity.py` with `sovereign-l4-load-balancer-production.json` |
| Ruff verifier | PASS | `tests/test_outputs.py` passes Ruff in verifier image |
| Oracle = 1 | PASS | Docker oracle run: 32/32 pytest pass after `solution/repair.py` + build |
| NOP = 0 | PASS | Docker starter run: 10 F2P failures / 22 pass (4 P2P) |
| Q1 Spec Gap Repair | PENDING | pre-LLMaJ specialist evidence not yet recorded |
| Q2 Verifier Coverage Repair | PENDING | producer evidence only |
| Q3 Spec Ambiguity Repair | PENDING | producer evidence only |
| Q7 Task Format Enforcer | PASS | Edition 3 flat layout, `task.toml`, `instruction.md`, verifier contract |
| Preflight/static | PASS | local Terminus validators green |
| Q4 Spec-Test Contract Reviewer | PENDING | packet-bound review not yet recorded |
| Q6 Production Logic Auditor | PENDING | packet-bound review not yet recorded |
| Quality Interlock | PENDING | requires current Q4 + Q6 PASS |
| Pre-LLMaJ specialist panel | PENDING | |
| Harbor LLMaJ | PENDING | |
| Difficulty trials | PENDING | GPT-5.5 ×5 plus Claude Opus 4.8 ×5 |
| Combined difficulty ×10 | PENDING | tier not calibrated |
| Final Compliance | PENDING | |
| Final Human Quality | PENDING | |
| Final package | PASS | task ZIP contents assembled locally |

## Latest validation evidence

- Images: `sovereign-l4-lb-env`, `sovereign-l4-lb-verifier`
- Oracle command: `python3 /solution/repair.py /app/sovereign-lb && /app/sovereign-lb/bin/build && /tests/test.sh`
- NOP command: `/tests/test.sh` on starter image
- Production profile: `.terminus/designs/sovereign-l4-load-balancer-production.json`

## Current blocker

Official Harbor LLMaJ, quality-interlock packet reviews, and combined ×10 difficulty trials remain deferred. Deterministic assembly, oracle/NOP, complexity, defect-topology, and runtime-authenticity gates are complete.

## Notes

- `production_authenticity.current_state_evidence_required=false` because `instruction.md` states desired end-state behavior only; no inherited incident narrative is asserted.
- Stateful dataset exemption documents why 10k business rows are inappropriate for an L4 control/dataplane service.
