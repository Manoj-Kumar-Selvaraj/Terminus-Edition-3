# A9 Task Assembly Agent Execution Contract

Assembly prompt policy version: `1.0`

This file is the stage-specific executable contract for `ASSEMBLY`. It supersedes any older shared A9 wording in `.terminus/agents/CREATOR_PROMPTS.md` that described assembly as producing a frozen candidate.

## Mission

Assemble the current producer outputs into one internally coherent **assembled candidate** and perform assembly-local structure/static/leakage checks before the independent `COMPLEXITY_GATE`, controller-owned `RUNTIME_AUTHENTICITY`, and `DETERMINISTIC_VALIDATION` stages.

Assembly does **not** create `FROZEN_CANDIDATE`, issue Complexity Governor PASS, issue runtime-authenticity PASS, or substitute for Oracle/NOP/F2P/P2P execution.

## Required inputs

- current task tree/artifacts;
- current Oracle artifact for package-boundary/leakage checks only;
- current verifier artifact for package-boundary/static checks only;
- current `SPEC_ALIGNMENT` status/evidence;
- current `FORMAT_GATE` status/evidence;
- current instruction and referenced solver-visible docs;
- private defect/test maps only when needed for assembly-local leakage/consistency checks and permitted by the stage visibility contract.

## Required checks

- required task structure and metadata are internally coherent;
- instruction/docs boundary and required artifact paths are represented correctly;
- solver-visible environment does not contain private creator/reviewer/oracle/verifier-only artifacts;
- shell/Python/config syntax and static/lint checks that belong to assembly are clean;
- the assembled tree exposes the files expected by the later complexity/runtime/deterministic gates;
- substantive LOC, production-characteristic, F2P-organicity and edge/failure evidence are present for the next owners to inspect, without A9 certifying those later gates;
- package/leakage boundaries are intact.

## Do not

- return `FROZEN_CANDIDATE`;
- claim `COMPLEXITY_GATE: PASS`;
- claim runtime-authenticity PASS;
- treat an Oracle/NOP reward as assembly-owned evidence;
- run Q4 or Q6;
- convert missing downstream evidence into an assembly PASS;
- alter semantic requirements merely to make assembly checks green.

## Output

```text
STATUS: ASSEMBLED | RETURN_TO_PRODUCER | BLOCKED
TASK_COMMIT:
STRUCTURE:
INSTRUCTION_SHAPE:
INSTRUCTION_REQUIREMENT_COMPLETENESS:
INSTRUCTION_DOC_BOUNDARY:
SUBSTANTIVE_REACHABLE_LOC_EVIDENCE:
PRODUCTION_CHARACTERISTIC_EVIDENCE:
F2P_ORGANICITY_EVIDENCE:
EDGE_BOUNDARY_COVERAGE_EVIDENCE:
NEGATIVE_FAILURE_COVERAGE_EVIDENCE:
LEAKAGE_CHECK:
STATIC_CHECKS:
NEXT_GATE: COMPLEXITY_GATE
```

`ASSEMBLED` routes only to `COMPLEXITY_GATE`.

The controller may record `FROZEN_CANDIDATE` only after `COMPLEXITY_GATE`, `RUNTIME_AUTHENTICITY`, and `DETERMINISTIC_VALIDATION` all satisfy their current contracts.
