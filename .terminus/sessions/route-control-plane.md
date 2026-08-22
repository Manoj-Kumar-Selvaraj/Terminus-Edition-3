# Terminus Task Session

Session schema version: `2.4`

This is the durable operational checkpoint for route-control-plane. Current task-tree, controller, deterministic, and review provenance overrides stale chat prose or unrelated repository HEAD movement.

## Identity

- Task: `route-control-plane`
- Controller state: `QUALITY_INTERLOCK`
- Working branch: `task/route-control-plane-q4q6-remediation`
- Pull request: `#92`
- Current task commit: `01dba48d44515a69d0a2e4305a75294c41389a67`
- Agent-system policy: `2.5`
- Specialist prompt policy: `2.2`
- Specialist protocol policy: `2.2`
- Pre-LLMaJ panel policy: `2.2`
- Comprehensive reviewer policy: `1.0`
- Effective creation control-plane commit: `df7ef7569e2947b9f0bf7cf89ed4dec6c2a5a1fe`
- Creation profile: `large_system_strict`

## Current gates

| Gate | Status | Evidence / version |
| --- | --- | --- |
| Rule Resolution | PASS | current route ledger sequence 10 under control-plane `df7ef7569e2947b9f0bf7cf89ed4dec6c2a5a1fe` |
| Work Package Research | PASS | ledger sequence 11; `FLEET_ROUTE_DESIRED_STATE_RECONCILIATION` |
| System Architecture | PASS | ledger sequence 12 |
| Defect Topology | PASS | ledger sequence 13; 24 approved defects across 8 coupled clusters |
| Environment Build | PASS | ledger sequence 14 |
| Reference Solution | PASS | ledger sequence 15 |
| Verifier Build | PASS | ledger sequence 16 |
| Human Writing Research | PASS | ledger sequence 17 |
| Instruction Draft | PASS | ledger sequence 18 |
| Spec Alignment / Q1-Q3 | PASS | ledger sequence 19 |
| Documentation Draft | PASS | ledger sequence 20 |
| Q7 Format Gate | PASS | latest route FORMAT_GATE records through sequence 30 |
| Assembly | PASS | ledger sequence 31 |
| Creator Complexity Gate | PASS on remediation candidate | PR #92 run `32561799801`: substantive_loc=3338, 24 defects, 8 root causes, 25 F2P + 8 P2P; rerun required after reference handoff fix |
| Runtime Authenticity | PASS on remediation candidate | PR #92 run `32561799801`; rerun required after reference handoff fix |
| Deterministic Validation | REPAIRING | PR #92 run `32561799801`: 32/33 Oracle tests passed; delegated Ansible reference repair targeted old tasks/main.yml path. Task commit `01dba48d44515a69d0a2e4305a75294c41389a67` fixes only that Oracle handoff; rerun pending |
| Q4 Spec-Test Contract Reviewer | REVISE | run `32559452472`, attempt 1/3; four blockers on behavioral coverage / discoverability |
| Q6 Production Logic Auditor | REVISE | run `32559452472`, attempt 1/2; substantive LOC below strict floor and repetitive fleet padding risk |
| Quality Interlock | REVISE | remediation task commit `01dba48d44515a69d0a2e4305a75294c41389a67`; do not spend Q6 attempt 2 before deterministic rerun passes |
| Pre-LLMaJ | NOT_REACHED | waits for Quality Interlock |
| Submission ready | NO | Q4/Q6 rerun and downstream gates remain open |

## Quality review evidence

- Reviewed frozen candidate: `98940c2836fbfbdeb49c82c05f09b58c251b161f`.
- Q4 result: `.terminus/reviews/route-control-plane/98940c28/route-control-plane-98940c28-spec-test-contract-3eff6ac841.json` = `REVISE`, HIGH confidence, SUFFICIENT evidence.
- Q6 result: `.terminus/reviews/route-control-plane/98940c28/route-control-plane-98940c28-production-logic-0022b2b05d.json` = `REVISE`, HIGH confidence, SUFFICIENT evidence.
- Model execution / interlock run: `32559452472`.
- Q4 remaining budget after remediation: attempts 2-3 available.
- Q6 remaining budget after remediation: attempt 2 only.
- The first interlock collector additionally exposed a missing-session freshness failure; this checkpoint repairs that task-local provenance prerequisite. The separate validator circular-import issue remains control-plane infrastructure evidence to re-check before the second interlock.

## Bounded Q4/Q6 remediation

- Production-depth and verifier remediation base: `5690627358738f94f9d0960edab6b399a9e13f55`.
- Current task commit including Oracle delegated-projection handoff repair: `01dba48d44515a69d0a2e4305a75294c41389a67`.
- Q4 contract repair: instruction explicitly defines protected management reachability, isolated host-network behavior, Ansible second-run convergence, and strictly increasing `GET /v1/audit` Sequence values.
- Q4 verifier repair: behavioral P2P coverage for management reachability, host route-table isolation, actual two-run Ansible projection convergence, and public audit monotonicity.
- Private test map: 25 F2P cases retained; preservation set expanded from 4 to 8 P2P cases.
- Q6 production-depth repair: reachable FIB tracing, topology/dependency analysis, management safety, policy evaluation, transaction recovery, fleet health, rollout preview, impact analysis, inventory, diagnostics, state diff, route shadow/ECMP analysis, consistency sweeps, and failure-domain change-window planning.
- Q6 complexity evidence from first PR validation: `substantive_loc=3338`, 10 components, 11 cross-cluster pairs, 33 total behavioral tests.
- Q6 padding repair: replaced ~1,600 lines of near-identical fleet-node fixtures with compact, behaviorally diverse multi-site IPv4/IPv6, ECMP, offline, staging, and DR configurations.
- Existing intentional F2P defects remain starter-visible; in particular host-specific protected-route precedence is not repaired in the starter.
- Oracle run `32561799801` showed all new Q4 behavioral P2P tests passing; the only failure was the old reference repairer path after the Ansible task refactor. `01dba48d...` adds an Oracle-only delegated projection fixer and leaves starter semantics unchanged.

## Required resume sequence

1. Rerun PR #92 validation at current task commit and require Oracle=1 plus NOP=0.
2. Merge PR #92 to `main` after checks are green.
3. Replay the controller-defined affected stages and mandatory Q1/Q2/Q3/Q7 gates as required by current machine routing.
4. Rerun Creator Complexity Gate and Runtime Authenticity on the remediated task snapshot.
5. Rerun hosted deterministic validation; require Oracle=1, NOP=0, all 25 F2P transitions correct, and all 8 P2P cases preserved.
6. Freeze the resulting exact task commit.
7. Re-check quality collector freshness/import health.
8. Only then execute Q4/Q6 quality attempt 2 and poll through terminal status.
