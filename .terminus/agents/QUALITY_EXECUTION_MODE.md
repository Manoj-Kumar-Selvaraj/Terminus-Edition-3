# Terminus Quality Execution Mode

Quality execution-mode policy version: `1.0`

This policy separates producer-side quality work from independent cold quality judgment while keeping one persistent user-visible task chat for normal creation and remediation.

## Canonical mode variables

The versioned defaults are stored in `.terminus/agents/quality_execution_mode.json`:

- `TERMINUS_Q4_Q6_MODE=AUTOMATED|MANUAL`
- `TERMINUS_Q8_MODE=OFF|AUTOMATED|MANUAL`

`controller_cli continue` accepts `--q4-q6-mode` and `--q8-mode` as explicit per-continuation overrides. Environment variables with the same names override the versioned defaults when no CLI override is supplied. Invalid values fail closed.

Default policy:

- `TERMINUS_Q4_Q6_MODE=AUTOMATED`
- `TERMINUS_Q8_MODE=OFF`

## Same-chat execution

A-series producer work and registered `PRODUCER`/`FIXER` stages execute as `INLINE_SPECIALIST` in the persistent task ChatGPT conversation. The stage invocation remains exact and bounded; changing chat boundaries does not widen evidence access, mutation scope, status values, validators or lifecycle authority.

A10 Complexity Governor is also an explicit same-chat creation governor. Although its stage role class is semantic/reviewer-like rather than `PRODUCER`, `COMPLEXITY_GATE` is a pre-freeze creation gate, not an independent acceptance boundary. `A10_COMPLEXITY_GOVERNOR` therefore executes as bounded `INLINE_SPECIALIST` in the persistent task chat. Its result can advance only to the registered runtime-authenticity/deterministic gates or route repair; it cannot substitute for Q4/Q6 independent acceptance and does not become final task acceptance evidence by itself.

The following Q roles are producer-side specialists and stay in the same task chat:

- Q1 Spec Gap Repairer
- Q2 Verifier Coverage Repairer
- Q3 Spec Ambiguity Repairer
- Q5 Oracle & Runtime Repair Specialist
- Q7 Task Format Enforcer

Q1/Q2/Q3 are mandatory producer-side semantic checks at `SPEC_ALIGNMENT`. `controller_cli continue` returns `INLINE_SPECIALIST_SEQUENCE` for that aggregate stage and freezes the checks in this exact order: Q1 -> Q2 -> Q3. Each substep inherits the exact aggregate StageInvocation input/evidence boundary and cannot expand it. The substeps are not independent acceptance records; after their outputs are frozen, the Creation Controller emits the single canonical `SPEC_ALIGNMENT` StageResult containing `Q1_STATUS`, `Q2_STATUS`, and `Q3_STATUS`.

The mandatory inline pass is evaluation-only with respect to the aggregate invocation. If a substep finds a repair need, it reports that finding into the aggregate result and the controller routes the implicated producer/fixer under fresh task-commit authority. This prevents a same-chat repair from silently mutating the task underneath the still-bound aggregate invocation.

Q7's format gate is mandatory. Deterministic runtime/oracle validation is mandatory; Q5 repair runs only when that mandatory checkpoint routes a runtime/oracle failure to Q5. A passing runtime/oracle checkpoint records no artificial Q5 repair.

These same-chat roles do not consume Q4/Q6/Q8 independent-review budget slots.

## Independent mandatory quality: Q4 + Q6

Q4 Spec-Test Contract Reviewer and Q6 Production Logic Auditor remain cold and independent from the producer task chat and from each other's unfrozen conclusions.

When `TERMINUS_Q4_Q6_MODE=AUTOMATED`, the controller dispatches `.github/workflows/terminus-quality-lifecycle.yml` for `QUALITY_INTERLOCK`. Q4 and Q6 execute through the packet-bound isolated quality executor, retain durable per-task budgets (Q4 maximum 3, Q6 maximum 2), and must both satisfy the canonical interlock before advancement.

When `TERMINUS_Q4_Q6_MODE=MANUAL`, the controller returns `MANUAL_INDEPENDENT_QUALITY`. Q4 and Q6 must run in fresh isolated reviewer contexts, never in the producer/orchestrator context. Manual attempts remain subject to the same semantic attempt limits and must not be accepted as canonical lifecycle evidence until their packet/result provenance and attempt accounting are durably recorded.

## Optional independent diagnostic: Q8

Q8 is never a default mandatory model call.

- `TERMINUS_Q8_MODE=OFF` records the registered Q8 stage as `SIMULATION_NOT_EXECUTED` through the deterministic no-model lifecycle path. No Q8 model call or Q8 budget slot is consumed.
- `TERMINUS_Q8_MODE=AUTOMATED` executes the isolated packet-bound Q8 perspective through the quality workflow. GPT and Claude retain separate one-shot budgets and must not see each other's result before freeze.
- `TERMINUS_Q8_MODE=MANUAL` returns `MANUAL_INDEPENDENT_QUALITY`; the perspective must run in a fresh isolated manual reviewer/simulator context.

Q8 results are diagnostic only and never substitute for Harbor or official model-trial evidence.

## Routing precedence

For a current controller continuation:

1. mandatory Q4/Q6 or optional Q8 stages use the mode variables above;
2. hosted deterministic controller stages use their registered controller workflow when available;
3. controller aggregate stages with a configured inline sequence use `INLINE_SPECIALIST_SEQUENCE` and execute those bounded subroles in the persistent task chat before the aggregate result is recorded;
4. ordinary controller stages use `ORCHESTRATOR_DIRECT`;
5. A-series producers, A10 Complexity Governor, Q1/Q2/Q3/Q5/Q7 and other registered `PRODUCER`/`FIXER` stages use `INLINE_SPECIALIST` in the same task chat;
6. external gates remain external dispatch/await stages;
7. genuinely independent non-automated reviewer work may use `FRESH_ROLE_CHAT`.

After any inline specialist result, the same acceptance path still applies: StageResult validation -> canonical execution record -> durable ledger -> replay/materialization -> `controller_cli continue`.

## Security and budget invariants

Execution mode never permits provider fallback, verdict shopping, credential refresh/login recovery, secret material in packets/results, or bypass of durable Q budgets. `SNORKEL_API_KEY` is not a model credential. A semantic `REVISE` remains authoritative regardless of automated or manual review surface.
