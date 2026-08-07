# Pre-LLMaJ Review Panel

Panel policy version: `2.2`

Purpose: predict likely Harbor `check` and human-review failures before spending Harbor/model time. Pre-LLMaJ is not a replacement for Harbor LLMaJ or final human review.

Read first:
- current authoritative Edition 3 rules;
- `.terminus/AGENT_SYSTEM.md`;
- `.terminus/agents/PROTOCOL.md`;
- `.terminus/agents/PROMPTS.md`;
- `.terminus/reviewers/REVIEWER_CHECKLIST.md`;
- `.terminus/reviewers/reviewer_criteria.json`.

The stored reviewer checklist snapshot was supplied by the project owner on 2026-08-08. Its public URL currently returns 404 through automated web access, so final-review policy freshness must be recorded rather than assumed. Where a checklist statement has been independently confirmed by current authoritative Edition 3 rules, record that resolution rather than preserving a false conflict.

## Stage A — deterministic facts

Run objective checks before semantic reviewers. Typical checks:

- task schema/required files;
- path/identifier validity;
- Docker/base-image/environment rules that can be mechanically validated;
- Python compile/ruff;
- no obvious forbidden/backup/extraneous files;
- Oracle/NOP reward evidence when credentials/runtime permit;
- required reviewer/control-plane files and JSON registries parse.

A deterministic failure blocks semantic PASS where applicable. Do not ask a model reviewer to debate an objective syntax/schema failure.

## Stage B — independent specialist reviews

Run these as independent cold reviews where inputs permit:

1. **Task Architect** — scenario/contract/solvability/coupled reasoning.
2. **Verifier Engineer** — req↔test coverage, semantics, determinism, anti-cheat.
3. **Originality & Authenticity Reviewer** — duplicate/template/authenticity risk.
4. **Difficulty Reviewer (pre-trial)** — genuine reasoning, shortcut/clerical risk.
5. **Compliance Auditor** — current Edition 3 structural/security/package risk.
6. **Instruction Reviewer** — solver-facing fairness/concision/human voice/leakage.
7. **Engineering Documentation Reviewer** — README/explanation evidence and voice.

### Independence constraints

- Do not show reviewers each other’s verdicts before their reports are frozen.
- Do not tell a reviewer that another role already passed/failed the task.
- Do not reveal the desired aggregate outcome.
- Do not let Instruction/Documentation writers perform the final review.
- Do not give writing reviewers hidden oracle/test implementation details; use solver-visible artifacts and a requirement summary.
- Do not give Originality Reviewer the creator’s uniqueness rationale or prior originality result.

## Stage C — evidence sufficiency

Every mandatory reviewer must provide:

- `VERDICT`;
- `CONFIDENCE`;
- `EVIDENCE_STATUS`;
- concrete evidence refs for material findings.

Rules:

- `INSUFFICIENT_EVIDENCE` blocks aggregate PASS.
- LOW-confidence PASS is not a final PASS; gather more evidence or re-review.
- BLOCKER/HIGH findings without evidence are not automatically accepted as true; route to clarification/adjudication.
- reviewer count is not a vote count.

## Stage D — comprehensive checklist cold review

After specialist reviews are frozen but **before their verdicts are shown to the Comprehensive Reviewer**, run `.terminus/agents/COMPREHENSIVE_REVIEWER.md`.

The Comprehensive Reviewer must independently inspect the task against **every criterion** in `.terminus/reviewers/reviewer_criteria.json` plus the cross-cutting checks in `.terminus/reviewers/REVIEWER_CHECKLIST.md`.

Required properties:

- `CHECKLIST_COVERAGE: 100%`;
- one status for every registry criterion;
- all issues reported, not only the first blocker;
- explicit dispositions for all available test-quality eval flags;
- explicit dispositions for all available trial-analysis flags;
- severity aggregation exactly follows the checklist, including special trial-analysis handling;
- policy conflicts are surfaced rather than silently resolved;
- missing acceptance-relevant evidence produces `INSUFFICIENT_EVIDENCE`.

The Comprehensive Reviewer is a breadth backstop. It does not replace specialist reviewers. A task needs both specialist depth and comprehensive breadth.

## Stage E — disagreement and omission scan

Only after the specialist reports and Comprehensive Reviewer report are frozen may the Orchestrator compare them.

Check for:

- specialist finding absent from Comprehensive Reviewer;
- Comprehensive Reviewer finding absent from relevant specialist;
- contradictory severity or applicability decisions;
- Instruction Reviewer asking to remove details that Verifier Engineer considers necessary for fairness;
- Originality changes that Difficulty Reviewer says collapse legitimate reasoning;
- Compliance and Verifier disagreement over artifact/source inspection;
- Documentation claims unsupported by Task Architect/trajectory evidence;
- checklist snapshot conflicts with current authoritative Edition 3 rule files.

For a material disagreement, invoke Adjudicator. Do not average or majority-vote.

An omission is itself useful reviewer-eval evidence: if the Comprehensive Reviewer repeatedly misses a criterion or a specialist repeatedly misses a cross-domain issue, add a regression case to `.terminus/reviewers/REVIEWER_EVALS.md`.

## Stage F — aggregate

Only after deterministic checks, specialist reviews, evidence sufficiency, Comprehensive Reviewer coverage, and any adjudication are complete, record:

```text
PRE_LLMAJ: PASS | REVISE | REJECT | INSUFFICIENT_EVIDENCE | POLICY_CONFLICT
TASK_COMMIT:
PANEL_POLICY_VERSION: 2.2
AGENT_PROMPT_POLICY_VERSION:
CHECKLIST_VERSION:
POLICY_FRESHNESS: CURRENT | UNVERIFIED | STALE
STATIC_CHECK: PASS | FAIL
TASK_ARCHITECT: PASS | REVISE | INSUFFICIENT_EVIDENCE
VERIFIER: PASS | REVISE | INSUFFICIENT_EVIDENCE
ORIGINALITY: PASS | REVISE | REJECT | INSUFFICIENT_EVIDENCE
DIFFICULTY_DESIGN: PASS | REVISE | INSUFFICIENT_EVIDENCE
COMPLIANCE: PASS | REVISE | INSUFFICIENT_EVIDENCE
INSTRUCTION: PASS | REVISE | INSUFFICIENT_EVIDENCE
DOCUMENTATION: PASS | REVISE | INSUFFICIENT_EVIDENCE
COMPREHENSIVE_REVIEW: APPROVE | APPROVE_WITH_NOTE | REQUEST_CHANGES | DECLINE | INSUFFICIENT_EVIDENCE | POLICY_CONFLICT
CHECKLIST_COVERAGE: 100%
ADJUDICATIONS: <none or review ids>
OPEN_FINDINGS: <finding ids>
POLICY_CONFLICTS: <none or ids>
```

Aggregate PASS requires:

- deterministic stage PASS;
- every mandatory specialist reviewer PASS with SUFFICIENT evidence and at least MEDIUM confidence;
- Comprehensive Reviewer is `APPROVE` or an explicitly acceptable `APPROVE_WITH_NOTE` under severity policy;
- checklist coverage is 100%;
- no unresolved High failure;
- no unresolved multiple ordinary Medium failures;
- no valid special trial-analysis revision flag;
- no unresolved reviewer disagreement;
- no acceptance-relevant `POLICY_CONFLICT`;
- Originality is not REJECT;
- all reports apply to the same relevant task version and current role-specific reviewer policy.

## Comprehensive severity rules

The panel must preserve these distinctions:

- **High:** one failure blocks acceptance.
- **Ordinary Medium:** multiple failures block; one may be accepted only with a note.
- **Low:** does not block on its own.
- **Trial-analysis Medium:** each valid flag is judged independently; one valid `difficulty_crux`, `near_miss`, `refusals`, or `low_timeout` flag can require revision even when it is the only Medium issue.

Do not flatten all Medium criteria into one policy.

## Official difficulty/solvability interpretation

Current authoritative Edition 3 guidance confirms the two official evaluation suites:

- Claude Opus 4.8 / Claude Code ×5;
- GPT-5.5 / Codex ×5.

Their combined 10-run mean sets final difficulty. The reviewer checklist's “across 10 runs, every individual test passes at least once” solvability rule therefore applies across the **combined 10 official trials**.

Consequences:

- each five-run model suite is diagnostic only;
- do not require 1/5 per-test success separately in both models;
- do not call 4/5 or 5/5 in one model automatically too easy;
- final tier uses the combined 10-run pass rate: `<20% frontier`, `20–<50% advanced`, `50–<80% core`, `80–<100% base`, `100% reject`;
- any individual verifier test at 0/10 blocks solvability and requires trajectory analysis.

## Producer loop

If a reviewer returns REVISE/REQUEST_CHANGES:

1. freeze the report/finding IDs;
2. route only relevant findings to the appropriate producer/fixer;
3. apply the smallest coherent change;
4. calculate which reviews became stale using `PROTOCOL.md`;
5. rerun affected cold reviews;
6. rerun Comprehensive Reviewer if any checklist-relevant artifact changed;
7. do not let writers self-certify.

If the same material finding survives two fixes, trigger circuit-breaker/adjudication rather than repeatedly rewriting.

## Harbor confirmation and learning

Only `PRE_LLMAJ: PASS` permits slow Harbor LLMaJ.

If Harbor or a human reviewer finds an applicable issue that Pre-LLMaJ missed:

- log it in `.terminus/reviewers/LLMAJ_LEARNING_LOG.md` or the appropriate reviewer-learning log;
- map the miss to the responsible specialist and/or Comprehensive Reviewer criterion;
- add/update a regression case in `.terminus/reviewers/REVIEWER_EVALS.md`;
- improve reviewer policy/calibration only if the lesson generalizes;
- regression-test the changed policy;
- rerun Pre-LLMaJ;
- retry Harbor only after local PASS.
