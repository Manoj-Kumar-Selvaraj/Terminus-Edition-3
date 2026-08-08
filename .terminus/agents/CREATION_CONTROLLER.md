# Terminus Edition 3 Creation Controller

Policy version: `1.0`

This controller is mandatory for new/rebuilt tasks. Current Edition 3 rules override local policy on conflict. Every creation run also applies `.terminus/agents/PRODUCTION_AUTHENTICITY.md`.

## States

`IDEA -> RESEARCHING -> ARCHITECTING -> DEFECT_DESIGN -> ENVIRONMENT_BUILD -> ORACLE_BUILD -> VERIFIER_BUILD -> HUMAN_WRITING_RESEARCH -> INSTRUCTION_DRAFT -> DOCUMENTATION_DRAFT -> ASSEMBLY -> COMPLEXITY_GATE -> RUNTIME_AUTHENTICITY -> DETERMINISTIC_VALIDATION -> FROZEN_CANDIDATE`

`BLOCKED` may overlay any state.

## Strict large-system constraints

For `large_system_strict`:
- >= **3,000** substantive solver-visible runtime/configuration LOC;
- infrastructure: **30–50** meaningful resources;
- **20–30** observable defect manifestations;
- >=15 manifestations in the causal graph with multiple cross-cluster relationships;
- **25–30** F2P cases, plus P2P according to regression risk.

If these cannot be satisfied through meaningful behavior, return `SCENARIO_TOO_SMALL`. Never pad or silently downgrade.

## Mandatory production-authenticity checks

For an operational/stateful strict task, before Instruction Writer or review:
1. Build a solver-visible **production evidence surface**: incident logs plus an independent handoff/state/operator artifact.
2. Ensure incident prose is grounded in those artifacts. Do not invent a “real-time” story after the environment is built.
3. For data-backed strict tasks, normally materialize **10,000–20,000** deterministic, varied primary business records.
4. Reject thin business logic. Major COBOL/business programs cannot be one constant output or one comparison surrounded by declarations; “one IF = one program” is a blocking authenticity smell.
5. Run `.terminus/validate_runtime_authenticity.py <task>` and treat failure as blocking.

## Role ownership

1. **Scenario Researcher** — incident candidates, evidence surface, persona, normal workflow, originality and scale fit.
2. **System Architect / Environment Builder** — runtime topology, representative state, logs/operator evidence, starter implementation.
3. **Defect Topology Designer** — private causal graph and partial-fix traps.
4. **Reference Solution Author** — general deterministic repair.
5. **Verifier Author** — behavioral F2P/P2P verifier from solver-visible contract.
6. **Human Writing Researcher** — public human-engineering calibration and task-specific writing profile.
7. **Instruction Writer** — evidence-backed handoff, not compressed rubric.
8. **Documentation Writer** — reviewer-facing explanations without benchmark framing.
9. **Task Assembly Agent** — deterministic authoring checks.
10. **Complexity Governor** — scale + authenticity adversarial review.
11. **Authoring Failure Diagnostician** — route Oracle/NOP failures to the smallest responsible producer.

## Freeze conditions

`FROZEN_CANDIDATE` requires:
- structure/static/lint PASS;
- complexity gate PASS;
- runtime-authenticity PASS;
- production evidence surface PASS when applicable;
- representative state-volume PASS when applicable;
- Oracle reward 1;
- NOP reward 0;
- every planned F2P Oracle-pass/starter-fail;
- intended P2P preserved;
- no solution/test leakage.

A creator cannot convert its own evidence into independent review approval.
