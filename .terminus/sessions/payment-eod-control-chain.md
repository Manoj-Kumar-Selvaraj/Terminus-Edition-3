# Terminus Task Session

## Identity

- Task: `payment-eod-control-chain`
- Controller state: `PRE_LLMAJ`
- Working branch: `agent/ci-payment-eod-validate`
- Pull request: `#2`
- Last checkpoint task commit: `38eb445e976be327a8fb2064ff896df24a85cd7d`

## Current gates

| Gate | Status | Evidence |
| --- | --- | --- |
| Preflight/static | PASS | run 31200979809 (#49); no structural verifier change since |
| Ruff verifier | PASS | run 31200979809 (#49) |
| STB auth/AI credentials | BLOCKED | active Edition-2 Portkey project/account reached maximum refresh limit 20 |
| Oracle = 1 | PASS | run 31200979809 (#49) |
| NOP = 0 | PASS | run 31200979809 (#49) |
| Pre-LLMaJ panel | REVISE | baseline review after new panel implementation |
| Originality & Authenticity | REVISE | duplicate risk LOW, template risk MEDIUM, realism HIGH |
| Instruction Reviewer | PASS | revised ~126-word incident-style instruction; must rerun after any structural contract change |
| Documentation Reviewer | REVISE | README still uses synthetic benchmark-style Difficulty/Solution/Verification structure and polished rubric-like prose |
| Harbor LLMaJ | STALE | old task version passed run #49; instruction changed afterward; do not rerun until Pre-LLMaJ PASS and reusable credentials exist |
| Difficulty 5x | NOT_RUN | blocked by Pre-LLMaJ findings and reusable-credential problem |
| Per-test 1/5 minimum | NOT_RUN | difficulty not run |
| Compliance audit | PENDING | final audit not run |
| Human quality audit | PENDING | final audit not run |
| Final package | PENDING | task not submission-ready |

## Latest meaningful validation evidence

- Run `31200979809` (#49): Oracle=1, NOP=0, Harbor LLMaJ PASS on the earlier instruction version; only the then-old evidence-manifest command failed after substantive gates.
- `38eb445`: rewrote `instruction.md` to ~126 words. This makes Harbor LLMaJ text review stale even though Oracle/NOP functional evidence remains useful.
- Later attempts were infrastructure-only failures: Snorkel HTTP 502, Harbor read timeout, then Portkey maximum refresh limit 20.

## Pre-LLMaJ checkpoint

- Aggregate: `REVISE`
- Task Architect: `PASS` — coherent payment restart/reconciliation problem with credible cross-component invariants.
- Verifier Engineer: `PASS` provisionally — semantic end-to-end scenarios, Oracle/NOP previously proven; final req↔test audit still required after structural changes.
- Originality & Authenticity: `REVISE`
- Difficulty design: `PASS` as Advanced candidate, not empirically calibrated.
- Compliance: `PENDING` final audit.
- Instruction: `PASS` on current wording.
- Documentation: `REVISE`.
- Open findings: reduce artificial benchmark construction signals in failure topology/supporting contract and rewrite README/explanations in natural engineering review voice before spending another Harbor LLMaJ run.

## Originality & Authenticity baseline

- Verdict: `REVISE`
- Duplicate risk: `LOW`
- Template risk: `MEDIUM`
- Realism: `HIGH`
- Provenance: payment EOD functional flow with COBOL decision programs, SQL durable state, shell orchestration, accounting/reconciliation/completion semantics.
- Nearest public reference reviewed: Terminal-Bench `payments-pipeline-fix`; overlap is only financial/restart correctness. Its Python worker startup/overdraft-notification topology is materially different.
- Distinctive features: COBOL + SQL + shell; internal-vs-external payment effects; reservation-before-clearing; ledger reconciliation; completion prerequisite; single authorization; restart idempotency.
- Artificial-construction signal: current starter/supporting contract is unusually tidy, with a sequence of planted defects and documentation sections that align closely with verifier families. It can look like a benchmark assembled one invariant at a time rather than one organically coupled production incident.
- Required structural review: consolidate the failure story around fewer coupled restart/reconciliation defects rather than a neat one-bug-per-requirement pattern; keep verifier coverage broad without making starter defects mirror the rubric one-to-one.

## Instruction review checkpoint

- Verdict: `PASS` on current version.
- Word count: `~126`.
- Human signal: `HIGH`.
- AI-template signal: `LOW`.
- Spec dump: `NONE` in `instruction.md`; detail is referenced through the supplied contract.
- Rerun required after any structural task/contract change.

## Documentation review checkpoint

- Verdict: `REVISE`.
- Main issue: README currently uses explicit `Difficulty rationale`, `Solution approach`, `Verification approach`, and source mapping in a polished, comprehensive benchmark voice. The content is useful, but the presentation reads as if written to satisfy a review rubric rather than as an engineer explaining the work.
- Next documentation change should retain technical evidence while explaining the actual reasoning bottleneck, key invariant choices, and why the verifier catches plausible partial fixes. Avoid generic phrases and feature enumeration.

## Current blocker

Two blockers remain before another expensive Harbor review:

1. Pre-LLMaJ is `REVISE` because originality/authenticity and documentation need structural/prose work.
2. Fresh GitHub-hosted runners cannot generate another Portkey key because the current Edition-2 allocation hit its refresh ceiling.

Neither blocker should be addressed by weakening verifier requirements.

## Next action

Refine the current task structurally to reduce one-bug-per-requirement/template signals, then rewrite README/Difficulty/Solution/Verification through the Engineering Documentation Reviewer. Re-run Instruction/Originality/Verifier reviewers after that change. Only when aggregate Pre-LLMaJ=PASS should Harbor LLMaJ be retried; difficulty follows after reusable AI credentials are available.

## Difficulty checkpoint

- Suite/model: `NOT_RUN`
- Complete-run passes: `NOT_RUN`
- Complete-run failures: `NOT_RUN`
- Verifier tests at 0/5: `NOT_RUN`
- Evidence: `none`
- Freshness: `NOT_RUN`

Acceptance policy: at least two complete attempts fail; every verifier test must pass at least once among five attempts; 4/5 or 5/5 complete passes is too easy; any test at 0/5 blocks acceptance.

## Durable reviewer system

- Pre-LLMaJ panel: `.terminus/reviewers/PRE_LLMAJ.md`
- Human-writing calibration: `.terminus/reviewers/HUMAN_WRITING_CALIBRATION.md`
- Synthetic contrast/example bank: `.terminus/reviewers/WRITING_EXAMPLE_BANK.md`
- Harbor feedback learning loop: `.terminus/reviewers/LLMAJ_LEARNING_LOG.md`
- Specialist prompts: `.terminus/agents/PROMPTS.md`
- Golden references: `.terminus/GOLDEN_TASKS.md`

## Decisions that must survive chat changes

- Use the ten-role agent system in `.terminus/AGENT_SYSTEM.md`.
- Originality & Authenticity review is mandatory before difficulty.
- Pre-LLMaJ must PASS before slow Harbor `check` is invoked.
- Harbor findings missed by Pre-LLMaJ must be converted into generalized reviewer calibration evidence before retrying.
- Instruction and engineering-documentation writing are separate review roles.
- Writing reviewers must read the calibration/example bank; do not merely prompt them to "sound human".
- GitHub + CI/artifacts are durable state; chat is replaceable.
- Infrastructure 502/timeouts/credential quotas are not task failures.

## Known infrastructure facts

- CI uses `snorkelai-stb==2.4.1`.
- Until Edition 3 allocation exists, the workflow defaults to Edition-2 Portkey project `bfe79c33-8ab0-4061-9849-08d3207c9927`.
- Never store credential values in repository files or chat.
- Repeated `stb keys refresh` on fresh hosted runners is not sustainable and has reached the current allowance.

## Do not retry blindly

- Do not spend Harbor LLMaJ/model credentials while Pre-LLMaJ is REVISE.
- Do not rerun Portkey refresh after the current max-refresh error.
- Do not treat external auth/network failures as verifier failures.
- Do not mark the current task submission-ready from run #49; instruction/originality/documentation/difficulty gates are newer and still incomplete.

## Resume rule

A new controller must read `.terminus/CONTINUE_SESSION.md`, `.terminus/AGENT_SYSTEM.md`, `.terminus/reviewers/PRE_LLMAJ.md`, this checkpoint, current task files, PR #2, and latest Actions/artifact evidence. Live evidence wins over stale checkpoint text.
