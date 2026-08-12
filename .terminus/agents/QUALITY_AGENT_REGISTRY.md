# Terminus Edition 3 Quality Agent Registry

Quality-agent registry version: `1.1`

This registry adds eight narrow agents around the existing creator/reviewer system. It does not replace the CI Orchestrator, Verifier Engineer, Instruction Reviewer, Complexity Governor, Compliance Auditor, Difficulty Reviewer, or Comprehensive Reviewer. The purpose is to catch expensive authoring failures earlier and route them to a specialist with one decision right.

All quality agents read current authoritative Edition 3 rules first, then `.terminus/AGENT_SYSTEM.md`, `.terminus/agents/PROTOCOL.md`, this registry, and `.terminus/agents/QUALITY_AGENT_PROMPTS.md`.

## Independence model

- Repair agents may change only their owned artifact class after Orchestrator routing. They never issue acceptance PASS for their own revision.
- Review agents are read-only and packet-bound under the normal v3 review provenance rules.
- A read-only quality reviewer that finds a defect routes it to the responsible repair agent; it does not silently patch the task.
- A task change stales any quality review whose evidence surface changed. Exact task-commit binding remains the default; Q6 is the only scope-reusable quality role and may remain current across a tests/spec-only task commit when its recorded production-scope hash is unchanged and all other provenance remains current.
- Hidden verifier details may be used only by roles explicitly allowed to compare verifier behavior against the solver-visible contract. They must not copy test names, fixture values, assertion ordering, or hidden expected values into solver-facing prose.

## Q1 — Spec Gap Repairer

**Purpose:** find legitimate verifier-required behavior that is not discoverable from the solver-visible work request plus explicitly referenced technical contracts, then repair the specification without losing complete material functional requirements or leaking hidden test topology.

**Owns:** solver-visible specification coverage gaps and the instruction-vs-doc natural location of a missing requirement.

**May read:** instruction, referenced contracts/runbooks, verifier requirement/assertion summary, and—when necessary—the verifier body for evidence. Hidden test details are treated as confidential evidence, never as wording source.

**May change:** `instruction.md` and existing solver-visible contract/runbook files only when the missing requirement naturally belongs there.

**Must not:** dump test cases into the instruction, create one sentence per test, copy hidden values/test names, prescribe implementation, diagnose which module/function is buggy without legitimate solver-visible basis, move material task goals into docs to evade the instruction limit, or invent a current-state/incident fact to justify a requirement.

**Repair rule:** keep the complete engineering objective and all material functional/operational/preservation/safety requirements discoverable in the work request under the Edition 3 `<=2` short paragraphs or `<=20` concise bullets shape. Technical architecture/layout/state/schema/protocol/API/CLI/runbook detail may live in referenced docs. Group related cases around meaningful responsibilities/invariants without erasing distinct material requirements. After editing, apply Jira/Slack handoff, requirement-completeness, reverse-outline and spec-file-loophole tests.

**Output:** gap IDs, affected solver-visible requirement, evidence showing the requirement is graded, chosen natural location, concise repair, instruction-shape/completeness status, instruction/docs boundary status, and a private coverage note.

## Q2 — Verifier Coverage Repairer

**Purpose:** find material solver-visible requirements that are not actually graded and add legitimate behavioral coverage.

**Owns:** specification -> verifier coverage gaps.

**May read:** complete solver-visible specification, verifier, test map, relevant runtime contracts, and Oracle/NOP evidence.

**May change:** verifier/tests and private test map. It may not weaken or remove a legitimate solver-visible requirement merely because it is inconvenient to test.

**Must not:** enforce a preferred implementation when behavior is observable, duplicate cases by fixture renaming, or derive the complete expected solution from Oracle source.

**Output:** stable requirement IDs, existing coverage, missing behavior, new/changed behavioral scenario, F2P/P2P classification, and required empirical starter/Oracle evidence.

## Q3 — Spec Ambiguity Repairer

**Purpose:** eliminate solver-visible ambiguity without converting the task into a grader specification.

**Owns:** ambiguous, contradictory, undefined, or multi-interpretation solver-visible contract language.

**Checks:** scope, actor, object, state transition, ordering, units, paths, identities, failure semantics, restart/idempotency behavior, authority/source-of-truth, allowed alternatives, and words such as "correct", "proper", "reliable", "recent", "matching", "safe", or "consistent" when their interpretation changes grading.

**May change:** instruction and referenced solver-visible contracts. It does not add new behavior merely to make wording more detailed.

**Must preserve:** the complete material engineering work request, natural Jira/change-request style, information selectivity, implementation freedom, the Edition 3 instruction shape, and the boundary between task goals in `instruction.md` and technical detail in referenced docs.

**Output:** ambiguity IDs, competing interpretations, grading consequence, minimal clarification, and why the clarification belongs in the chosen artifact.

## Q4 — Spec-Test Contract Reviewer

**Type:** independent read-only semantic reviewer.

**Decision right:** is the complete grading contract bidirectionally aligned and unambiguous after an exhaustive walk of the entire allowed scope, with a complete material work request in `instruction.md` and no prompt-extension/repair-map misuse of solver-visible docs?

It independently rebuilds the requirement/test matrix rather than trusting Q1–Q3 or Verifier Author notes. Q4 is not allowed to stop after the first blocking defect merely because the verdict is already known.

Mandatory exhaustive checks:
1. Inventory every material engineering objective, functional/operational requirement, preservation/compatibility/safety requirement and stable output/interface obligation.
2. Inventory every substantive verifier behavior.
3. Complete requirement -> verifier coverage for the full inventory.
4. Complete verifier behavior -> discoverable requirement for the full inventory.
5. Check `instruction.md` against the Edition 3 `<=2` short paragraphs or `<=20` concise bullets shape and verify that material task goals remain in the work request rather than being displaced into docs merely to evade the limit.
6. Walk every delegated solver-visible contract and stable graded output interface; distinguish legitimate architecture/layout/state/schema/protocol/API/CLI/runbook documentation from a second prompt or repair map.
7. Check for unnecessary implementation diagnosis that tells the solver which module/function is incomplete/buggy merely because the author knows the hidden topology.
8. Walk all F2P/P2P behavioral boundaries, including external integrations, preservation intent, circular oracles and bypass risk.
9. Walk all grading-relevant ambiguity and authority boundaries.
10. Check hidden-test/compressed-rubric leakage; up to 20 concise functional bullets are allowed, and the defect is one-to-one test topology or implementation recipe—not the mere presence of many legitimate requirements.
11. Perform a second adversarial omission sweep after the first matrix is frozen.
12. Report all blocking findings from the complete review in the same result.

A reviewer that cannot complete the exhaustive walk because evidence is unavailable returns `INSUFFICIENT_EVIDENCE`, not a partial `REVISE`.

Materiality is explicit: `BLOCKER/HIGH` always block; `MEDIUM` blocks only when it can change solver pass/fail, observable correctness, safety/durability or a documented stable public interface; `LOW` is advisory unless an authoritative rule makes it mandatory. `PASS` requires no blocking findings and a complete exhaustiveness block.

A single material phantom test, material untested requirement, grading-relevant ambiguity, material work-request omission, spec-file loophole/prompt-extension defect, or material repair-plan leakage is still `REVISE`; exhaustiveness makes the review more complete, not easier.

## Q5 — Oracle & Runtime Repair Specialist

**Type:** producer/fixer.

**Purpose:** troubleshoot and repair Oracle, reference solution, application/runtime code, environment, Docker/build, dependency, harness, state/bootstrap, and integration failures.

**Trigger:** Oracle != 1, Oracle exception, build/runtime failure, or an empirically proven implementation defect routed by the Orchestrator.

**Method:** classify the first failing boundary before editing: `ENVIRONMENT | BUILD | DEPENDENCY | STARTUP | STATE | APPLICATION | ORACLE | VERIFIER_HARNESS | INFRASTRUCTURE | CONTRACT`.

**May change:** only the smallest coherent responsible layer. If the verifier requirement is legitimate, it must not weaken the test to obtain green. If evidence proves a verifier or contract defect, route that finding to Q2/Q3/Verifier Author instead of silently changing it.

**Output:** failure boundary, first meaningful error, root cause, files changed, preserved invariants, rerun evidence needed, and regression risks.

## Q6 — Production Logic Auditor

**Type:** independent read-only semantic reviewer.

**Decision right:** is the solver-visible core genuinely complex, reachable, coupled, non-toy, and credible as production software/configuration rather than benchmark padding?

It evaluates more than raw LOC. For `large_system_strict`, >=3,000 substantive solver-visible runtime/config LOC is necessary but not sufficient.

Mandatory checks:
- major modules are reachable from real entrypoints/operator workflows;
- business/runtime modules contain material branching, state handling, error handling, persistence/integration behavior, not wrappers or constant-output shells;
- subsystem responsibilities differ materially rather than cloning one thick template;
- data/state volume is meaningful to domain behavior rather than opaque filler;
- interactions cross module/component boundaries and create real partial-fix traps;
- removing a large fraction of code would materially reduce system behavior;
- complexity comes from domain invariants and state transitions, not chores, file count, comments, generated code, vendored code, or duplicate resources.

Verdict is independent of Complexity Governor and production-authenticity validator output.

Q6 uses a conservative production evidence-scope hash over task `task.toml` plus the full solver-visible `environment/` tree. Once a Q6 PASS is produced under the current scoped-freshness contract, a later task commit may retain it only when that scope hash is unchanged and packet/result/role-contract provenance remains current. Any production-scope change makes Q6 stale.

## Q7 — Task Format Enforcer

**Type:** producer/fixer with deterministic-first behavior.

**Purpose:** enforce the exact current Edition 3 package and file-format contract before expensive runtime/reviewer gates.

It checks current authoritative rules and active CI/preflight scripts for, at minimum:
- top-level task directory and required files;
- `task.toml` version/sections/field placement/types/current metadata contract;
- `instruction.md`/README required presence and path rules;
- environment Dockerfile/base digest/dependency pins/build context/runtime tooling;
- `.dockerignore`;
- test image, test launcher, Python test discovery and timeout/artifact boundaries;
- solution directory and `solve.sh` deterministic executable contract;
- environment/solution/tests isolation and leakage;
- package-excluded private `.terminus` design/review artifacts;
- required tmux/asciinema/runtime conventions where current rules require them;
- forbidden backup/temp/AI-framework files and unsafe privilege/mount patterns.

It must derive exact requirements from current rule/enforcement files, not from stale golden tasks.

**Output:** exact rule, path, observed mismatch, deterministic vs semantic classification, minimal format fix, and revalidation command/gate.

## Q8 — Model Perspective Difficulty Simulator

**Type:** diagnostic read-only/solve-simulation agent with two mandatory isolated modes.

**Purpose:** predict how mature tasks may behave under the two official model families before spending official difficulty trials.

Required isolated executions:
- `GPT_PERSPECTIVE` — a cold solver strategy calibrated to the likely strengths/failure patterns of the GPT/Codex family.
- `CLAUDE_PERSPECTIVE` — a separate cold solver strategy calibrated to the likely strengths/failure patterns of the Claude/Claude Code family.

These are **simulations, not claims that the underlying runtime actually is GPT-5.5 or Claude Opus 4.8**. Never label simulated results as official model evidence.

Default evidence boundary before solving: solver-visible instruction, environment and normal tools only; no solution, hidden tests, private defect graph, prior solver trajectory, desired tier, or other perspective result.

Where the execution surface supports a disposable task clone, each perspective should attempt a full solve and preserve trajectory/diff/test outcome. If execution is unavailable, return `SIMULATION_NOT_EXECUTED` rather than invent a pass/fail.

After both perspectives freeze, the Orchestrator may compare them for:
- likely shortcuts;
- first divergence points;
- different diagnosis strategies;
- likely over/under-difficulty;
- environment/tool friction masquerading as reasoning difficulty;
- verifier cases both perspectives systematically miss.

Q8 is diagnostic only. It cannot set the official tier or satisfy the official GPT x5 / Claude x5 evidence requirement.

## Workflow integration

Authoring/repair loop:

`Verifier built -> instruction drafted -> Q1 spec-gap + instruction-boundary repair -> Q2 verifier-coverage repair -> Q3 ambiguity repair -> Q7 format enforcement -> Assembly/Complexity/Authenticity -> Oracle/NOP`

On Oracle/runtime failure:

`deterministic evidence -> Q5 diagnosis/repair -> affected deterministic reruns`

Before independent Pre-LLMaJ:

`FROZEN_CANDIDATE -> Q4 Spec-Test/Instruction-Contract Reviewer -> Q6 Production Logic Auditor -> QUALITY_INTERLOCK_PASS`

Only after Q4 passes on the current exact task commit and Q6 independently passes with sufficient evidence—either on that exact task commit or under the Protocol-defined unchanged Q6 production-scope hash—may normal Pre-LLMaJ begin.

After `PRE_LLMAJ: PASS` and before expensive model-backed evaluation, run Q8 in both isolated perspectives. A simulation finding may route the task back for repair, but simulation output never substitutes for Harbor LLMaJ or the official 10 difficulty trials.

## Quality interlock PASS

`QUALITY_INTERLOCK_PASS` requires:
- Q4 `PASS`, confidence >= MEDIUM, evidence `SUFFICIENT` on the exact current task commit;
- Q6 `PASS`, confidence >= MEDIUM, evidence `SUFFICIENT`, either on the exact task commit or retained by the Protocol-defined unchanged Q6 production-scope hash;
- no unresolved Q1/Q2/Q3 finding;
- Q7 exact-format checks current for the task commit;
- Oracle/NOP deterministic evidence current;
- no creator/fixer self-certification.
