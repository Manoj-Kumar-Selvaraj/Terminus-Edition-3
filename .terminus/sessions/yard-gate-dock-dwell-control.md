# Terminus Task Session

Session schema version: `2.4`

## Identity

- Task: `yard-gate-dock-dwell-control`
- Controller state: `ASSEMBLY`
- Working branch: `main`
- Pull request: `none`
- Current task commit: `none`
- Agent-system policy: `2.5`

## CREATION_RULE_CONTEXT

```text
CONTROL_PLANE_COMMIT: 6e3944669a62da5c2a9ae9c6a2528e11b772ca86
CREATION_PROFILE: large_system_strict
NETWORK_MODE: public
KNOWN_POLICY_CONFLICTS: none
REQUESTED_DOMAIN: Operations / Logistics
```

## Current gates

| Gate | Status | Evidence |
| --- | --- | --- |
| System architecture | ARCHITECTURE_READY | architecture.md |
| Defect topology | DESIGN_READY | json |
| Environment build | BUILT | environment/yard |
| Reference solution | IMPLEMENTED | solution/solve.sh |
| Verifier | BUILT | tests/; local oracle 36/36; starter 6/36 |
| A6 writing calibration | CALIBRATION_READY | DEGRADED external; pair hwpair-015955e2ba5fe83e02ff |
| Instruction | DRAFTED | instruction.md (10 bullets) |
| Q1/Q2/Q3 | ALIGNED | SPEC_ALIGNMENT.md |
| Q7 format | PASS | FORMAT_GATE.md |
| Assembly | ASSEMBLED | ASSEMBLY.md |
| Complexity | PASS | loc=5441; f2p_cases=29 |
| Runtime authenticity | PASS | 12600 visits; log+handoff |
| Harbor oracle/NOP | BLOCKED | Docker daemon not running (`dockerDesktopLinuxEngine` missing) |

## Next action

Harbor oracle then NOP once Docker Desktop is up (`JOBS_DIR=/tmp/e3-yard`, helper `.terminus/run-yard-oracle.sh`). Freeze only after both. Harbor LLMaJ / ×10 deferred unless asked.

## Decisions that must survive chat changes

- `artifacts = ["/app/yard"]` so verifier receives repaired CLI + state.
- Verifier mkdir `/app/yard/out` and `/app/yard/var`.
- Local oracle: 36 passed; starter NOP: 30 failed / 6 passed after Q2 additions.
- Config F2P raises grace_early to 90 and gates in at 13:45Z so starter (UTC compare) still fails.
- Harbor LLMaJ / official ×10 deferred unless asked.
- Do not leave oracle modules in `environment/yard/yard/` after local smoke.
