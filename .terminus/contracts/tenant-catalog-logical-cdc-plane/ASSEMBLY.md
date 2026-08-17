# ASSEMBLY — tenant-catalog-logical-cdc-plane

```text
STATUS: ASSEMBLED
TASK_COMMIT: pending-freeze
STRUCTURE: PASS — flat Edition 3 tree with Go agent runtime and Python verifier
INSTRUCTION_SHAPE: PASS — one short paragraph + six bullets (<=20)
INSTRUCTION_REQUIREMENT_COMPLETENESS: PASS — work package + preservation + CLI/safety; schemas via binding contract
INSTRUCTION_DOC_BOUNDARY: CLEAN — contract/oncall/bounce are technical/evidence docs, not a second prompt
SUBSTANTIVE_REACHABLE_LOC_EVIDENCE: PASS — validate_task_complexity substantive_loc>=3000 (seed.sql counted by validator; Go packages are the reachable runtime)
PRODUCTION_CHARACTERISTIC_EVIDENCE: PASS — differentiated packages, sqlite persistence, CLI, recover/apply/CDC, 12k row_version seed
F2P_ORGANICITY_EVIDENCE: PASS — 25 F2P / 9 P2P mapped in private test map from CLI/visibility/constraints/CDC/apply/recover/index surfaces
EDGE_BOUNDARY_COVERAGE_EVIDENCE: PASS — parent/child same-txn, hold aggregate, update before image, LSN monotonicity
NEGATIVE_FAILURE_COVERAGE_EVIDENCE: PASS — unknown flags/commands, missing --input, frozen tenant, stale epoch, unique/FK/hold rejects
LEAKAGE_CHECK: PASS — solution/tests excluded from agent image; no agent *.py; no .terminus in task package
STATIC_CHECKS: PASS — ruff on tests; shell LF; complexity PASS; authenticity PASS
NEXT_GATE: COMPLEXITY_GATE
```

Harbor deterministic evidence already recorded for this assembled tree: oracle reward 1.0, NOP reward 0.0 (25 F2P fail / 9 P2P pass). Controllers may freeze only after commit SHA is bound and those gates remain current.
