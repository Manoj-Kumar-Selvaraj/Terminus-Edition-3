# Pre-LLMaJ Review Panel

Purpose: catch likely Harbor `check` failures before spending time and model credentials on Harbor LLMaJ. This is a local review contract, not a replacement for Harbor `check`. Current Terminus Edition 3 rules always override public Harbor/template guidance when they differ.

## Evidence basis

The panel is calibrated against:

- current Terminus Edition 3 rules in this repository;
- the public Harbor benchmark-template task implementation rubric, which covers verifiability, solvability, genuine difficulty, real-world interest, outcome-based grading, anti-cheat robustness, security, functional verification, determinism, essential difficulty, instruction/test alignment, novelty, agentic work, reviewability, instruction concision, solution quality, separate-verifier correctness, environment hygiene, structured output schemas, critical typos, explanation quality, classification, resources, README quality, expert estimate, schema hygiene, and extraneous files;
- actual Harbor `check` results from this repository when available. New Harbor findings must be folded back into this file as calibration evidence.

Do not copy old benchmark-template metadata/schema rules into Edition 3. Use them only as quality lenses.

## Panel order

Run these reviewers before Harbor LLMaJ:

1. **Task Architect** — solvable, coherent end state, outcome rather than procedure, realistic scope.
2. **Verifier Engineer** — verifiable, functional behavior, requirement↔test alignment, deterministic, anti-cheat, no phantom specs, Oracle/NOP expectations.
3. **Originality & Authenticity Reviewer** — novel combination, non-duplicate, non-template topology, realistic professional provenance.
4. **Difficulty Reviewer** — genuine/essential difficulty, agentic work, not clerical or formatting difficulty.
5. **Compliance Auditor** — Edition 3 schema, Docker/environment/separate-verifier/security/resources/packaging.
6. **Instruction Reviewer** — concise human-written instruction, WHAT not HOW, exact required paths/schemas without a generated-looking dump.
7. **Engineering Documentation Reviewer** — README and Difficulty/Solution/Verification explanations are natural, useful, congruent, and not synthetic committee filler.

The CI Orchestrator aggregates the panel. Any `REVISE`, `FAIL`, `BLOCKER`, or `HIGH` finding blocks Harbor LLMaJ until resolved.

## Review matrix

| Quality lens | Primary owner | Block condition |
| --- | --- | --- |
| Verifiable and deterministic | Verifier Engineer | subjective/flaky/ambiguous grading |
| Solvable by reference solution | Task Architect + Verifier Engineer | oracle cannot demonstrate complete solution |
| Difficult for good reasons | Difficulty Reviewer | trivial, clerical, obscure-fact, formatting or LLM-trick difficulty |
| Real-world / interesting | Originality Reviewer | contrived puzzle with no credible professional analogue |
| Outcome verified | Task Architect + Verifier Engineer | tests or instruction dictate implementation process unnecessarily |
| Anti-cheat / no leakage | Verifier Engineer + Compliance Auditor | accessible answer/test leakage or obvious reward hack |
| Task security | Compliance Auditor | exfiltration, host escape, destructive/obfuscated behavior |
| Functional verification | Verifier Engineer | source grep/string presence used instead of behavior where behavior is testable |
| Requirement/test alignment | Verifier Engineer | req-gap, phantom-spec, untested material requirement |
| Novel / non-memorized | Originality Reviewer | standard textbook task or close benchmark clone |
| Agentic | Difficulty Reviewer | one-shot/simple-command solution |
| Reviewable | Documentation Reviewer | domain claims cannot be checked by reviewer from supplied evidence |
| Instruction concision | Instruction Reviewer | AI cadence, unnecessary headings/preamble, procedural walkthrough, fluff |
| Solution quality | Task Architect | hardcoded final answer or reference that does not demonstrate real computation |
| Separate verifier | Compliance Auditor | verifier reads undeclared agent state or lacks baked runtime dependencies |
| Environment hygiene | Compliance Auditor | solution/tests leak into agent image, unsafe/forbidden Docker patterns |
| Structured output schema | Instruction Reviewer + Verifier Engineer | required JSON/CSV/API schema neither stated nor clearly referenced |
| Critical identifiers | Compliance Auditor | typo/mismatch in path, command, schema or file name |
| Explanation quality | Documentation Reviewer | vague, boilerplate, contradicts implementation/tests, or narrates steps instead of rationale |
| Classification/resources | Compliance Auditor | implausible category/tags/time/resources under current E3 schema |
| Extraneous files | Compliance Auditor | unused/debug/backup files in task package |

## Originality & Authenticity Reviewer

This reviewer is mandatory before difficulty calibration.

It compares the task against `.terminus/GOLDEN_TASKS.md`, public Terminal-Bench/Harbor tasks when available, and prior local tasks. The goal is not to reject normal thematic overlap. It looks for stronger evidence:

- distinctive phrases or requirement sequences reused with nouns swapped;
- the same failure topology in the same order;
- the same verifier scenario topology with renamed entities;
- the same solution shape or planted-bug pattern;
- benchmark boilerplate that could be generated from a generic template;
- an implausibly clean one-bug-per-requirement construction;
- a scenario with no credible provenance or professional owner.

Output exactly:

```text
VERDICT: PASS | REVISE | REJECT
DUPLICATE_RISK: LOW | MEDIUM | HIGH
TEMPLATE_RISK: LOW | MEDIUM | HIGH
REALISM: LOW | MEDIUM | HIGH
PROVENANCE:
NEAREST_REFERENCES:
SUSPICIOUS_SIMILARITIES:
ARTIFICIAL_CONSTRUCTION_SIGNALS:
DISTINCTIVE_FEATURES:
REQUIRED_CHANGES:
```

`HIGH` duplicate risk is `REJECT`. `MEDIUM` template risk is at least `REVISE` unless concrete provenance and distinctive topology clearly explain the overlap.

## Pre-LLMaJ aggregate result

The Orchestrator records:

```text
PRE_LLMAJ: PASS | REVISE
TASK_ARCHITECT: PASS | REVISE
VERIFIER: PASS | REVISE
ORIGINALITY: PASS | REVISE | REJECT
DIFFICULTY_DESIGN: PASS | REVISE
COMPLIANCE: PASS | REVISE
INSTRUCTION: PASS | REVISE
DOCUMENTATION: PASS | REVISE
STATIC_CHECK: PASS | FAIL
OPEN_FINDINGS:
```

Only `PRE_LLMAJ: PASS` permits the slow Harbor LLMaJ gate. Harbor findings that the panel missed are treated as calibration failures: classify the missed criterion, update the responsible reviewer guidance/evidence pack, then re-run pre-LLMaJ before another Harbor check.
