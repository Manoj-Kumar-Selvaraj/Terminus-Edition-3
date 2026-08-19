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

The following Q roles are producer-side specialists and stay in the same task chat:

- Q1 Spec Gap Repairer
- Q2 Verifier Coverage Repairer
- Q3 Spec Ambiguity Repairer
- Q5 Oracle & Runtime Repair Specialist
- Q7 Task Format Enforcer

Q1/Q2/Q3 checks are mandatory through `SPEC_ALIGNMENT` and its required Q1/Q2/Q3 status fields. Q7's format gate is mandatory. Deterministic runtime/oracle validation is mandatory; Q5 repair runs only when that mandatory checkpoint routes a runtime/oracle failure to Q5. A passing runtime/oracle checkpoint records no artificial Q5 repair.

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
3. ordinary controller stages use `ORCHESTRATOR_DIRECT`;
4. A-series producers, Q1/Q2/Q3/Q5/Q7 and other registered `PRODUCER`/`FIXER` stages use `INLINE_SPECIALIST` in the same task chat;
5. external gates remain external dispatch/await stages;
6. genuinely independent non-automated reviewer work may use `FRESH_ROLE_CHAT`.

After any inline specialist result, the same acceptance path still applies: StageResult validation -> canonical execution record -> durable ledger -> replay/materialization -> `controller_cli continue`.

## Security and budget invariants

Execution mode never permits provider fallback, verdict shopping, credential refresh/login recovery, secret material in packets/results, or bypass of durable Q budgets. `SNORKEL_API_KEY` is not a model credential. A semantic `REVISE` remains authoritative regardless of automated or manual review surface.
