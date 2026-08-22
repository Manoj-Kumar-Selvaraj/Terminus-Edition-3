# Terminus Task Session

Session schema version: `2.4`

## Identity

- Task: `hydrograph-stage-forecast-desk`
- Controller state: `DEFECT_TOPOLOGY`
- Working branch: `main`
- Pull request: `none`
- Current task commit: `none`
- Agent-system policy: `2.5`

## CREATION_RULE_CONTEXT

```text
CONTROL_PLANE_COMMIT: 72c0df6ee13f275bfa7d9573bb90e6d5711123d7
CREATION_PROFILE: large_system_strict
NETWORK_MODE: public
KNOWN_POLICY_CONFLICTS: none
REQUESTED_DOMAIN: Science / Earth (H5)
LANGUAGES: python, sql
```

## Current gates

| Gate | Status | Evidence |
| --- | --- | --- |
| Rule resolution | PASS | 72c0df6e… |
| Work-package research | SELECTED | H5 hydrograph-stage-forecast-desk |
| System architecture | ARCHITECTURE_READY | architecture.md / .json |
| Defect topology | DESIGN_READY | json + topology.md |
| Environment build | PENDING | next |

## Next action

Environment Builder: materialize `/app/hydro` starter with **only** approved D01–D30 defects. Clean seed. Digest-pinned Python image. Then Reference Solution.

## Decisions that must survive chat changes

- Taxonomy: Science / Earth; workdir `/app/hydro`; CLI `hydroctl`.
- Grace = forecast as-of skew only (no scheduled obs slots).
- Warehouse prior season must exist; defect is publish mixing.
- Do not inject into seed, warehouse bytes, correct config tz/grace, or contract docs.
- artifacts plan: `["/app/hydro"]`.
- Harbor LLMaJ / ×10 deferred unless asked.
- Leave unrelated dirty trees untouched (yard-gate, codecommit, etc.).
