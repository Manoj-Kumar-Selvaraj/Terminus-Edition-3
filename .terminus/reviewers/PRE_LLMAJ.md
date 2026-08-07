# Pre-LLMaJ Review Panel

Panel policy version: `2.0`

Purpose: predict likely Harbor `check` failures before spending Harbor/model time. Pre-LLMaJ is not a replacement for Harbor LLMaJ.

Read first:
- current authoritative Edition 3 rules;
- `.terminus/AGENT_SYSTEM.md`;
- `.terminus/agents/PROTOCOL.md`;
- role prompts in `.terminus/agents/PROMPTS.md`.

## Evidence basis

The panel is calibrated against current Edition 3 rules, public Harbor quality lenses, previous Harbor/portal/human findings, and reviewer regression cases. Public benchmark rules never override current Edition 3 schema/process.

## Stage A — deterministic facts

Run objective checks before semantic reviewers. Typical checks:

- task schema/required files;
- path/identifier validity;
- Docker/base-image/environment rules that can be mechanically validated;
- Python compile/ruff;
- no obvious forbidden/backup/extraneous files;
- Oracle/NOP reward evidence when credentials/runtime permit;
- required reviewer/control-plane files exist and parse.

A deterministic failure blocks semantic PASS where applicable. Do not ask a model reviewer to debate an objective syntax/schema failure.

## Stage B — independent semantic reviews

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
- Do not let the Instruction/Documentation writers perform the final review.
- Do not give writing reviewers hidden oracle/test implementation details; use solver-visible artifacts and a requirement summary.
- Do not give Originality Reviewer the creator’s uniqueness rationale or prior originality result.

The Orchestrator may run independent reviewers in parallel conceptually. In a single-chat implementation, emulate this by constructing isolated bounded context packets and not carrying prior reviewer conclusions into the next review.

## Stage C — evidence sufficiency

Every mandatory reviewer must provide:

- `VERDICT`;
- `CONFIDENCE`;
- `EVIDENCE_STATUS`;
- concrete evidence refs for material findings.

Panel rules:

- `INSUFFICIENT_EVIDENCE` blocks aggregate PASS.
- LOW-confidence PASS does not count as a final PASS; gather more evidence/review again.
- A BLOCKER/HIGH finding without valid evidence is not automatically accepted as true; route to clarification/adjudication.
- Reviewer count is not a vote count.

## Stage D — disagreement scan

After independent reports are frozen, the Orchestrator checks for contradictions.

Examples:
- Instruction Reviewer wants to remove a detail that Verifier Engineer says is required for fairness.
- Originality Reviewer wants to restructure a task in a way Difficulty Reviewer says collapses legitimate reasoning.
- Compliance says artifact inspection is required while Verifier flags implementation coupling.
- Documentation claims a difficulty mechanism not supported by Task Architect/trajectory evidence.

If disagreement is material, invoke the Adjudicator under `.terminus/agents/PROTOCOL.md`. Do not average or majority-vote the verdicts.

## Stage E — aggregate

Only after deterministic checks, independent reviews, evidence sufficiency and any adjudication are complete, record:

```text
PRE_LLMAJ: PASS | REVISE | REJECT | INSUFFICIENT_EVIDENCE
TASK_COMMIT:
PANEL_POLICY_VERSION: 2.0
AGENT_PROMPT_POLICY_VERSION: 2.0
STATIC_CHECK: PASS | FAIL
TASK_ARCHITECT: PASS | REVISE | INSUFFICIENT_EVIDENCE
VERIFIER: PASS | REVISE | INSUFFICIENT_EVIDENCE
ORIGINALITY: PASS | REVISE | REJECT | INSUFFICIENT_EVIDENCE
DIFFICULTY_DESIGN: PASS | REVISE | INSUFFICIENT_EVIDENCE
COMPLIANCE: PASS | REVISE | INSUFFICIENT_EVIDENCE
INSTRUCTION: PASS | REVISE | INSUFFICIENT_EVIDENCE
DOCUMENTATION: PASS | REVISE | INSUFFICIENT_EVIDENCE
ADJUDICATIONS: <none or review ids>
OPEN_FINDINGS: <finding ids>
```

Aggregate PASS requires:

- deterministic stage PASS;
- every mandatory semantic reviewer PASS with SUFFICIENT evidence and at least MEDIUM confidence;
- no unresolved BLOCKER/HIGH;
- no unresolved reviewer conflict;
- Originality not REJECT;
- all reports apply to the same relevant task version and current reviewer policy.

## Review matrix

| Quality lens | Primary owner | Block condition |
| --- | --- | --- |
| coherent/solvable contract | Task Architect | missing/unobservable end state, contradiction, impossible requirement |
| genuine coupled reasoning | Task Architect + Difficulty | clerical checklist, obscure-fact difficulty, trivial local fix |
| functional/deterministic grading | Verifier Engineer | subjective/flaky/source-preference grading where behavior is observable |
| requirement↔test alignment | Verifier Engineer | req-gap, phantom spec, untested material requirement |
| anti-cheat / no answer leakage | Verifier + Compliance | accessible oracle/tests/reward shortcut |
| current E3 structural/security rules | Compliance | current BLOCKER/HIGH violation |
| novelty/authenticity | Originality | clone/renamed topology or artificial benchmark construction |
| instruction fairness/human quality | Instruction | material ambiguity, solution leakage, generated-looking rubric dump |
| explanation quality | Documentation | unsupported/vague/benchmark-style explanation |
| reviewability | Documentation + Architect | critical claims cannot be checked from supplied evidence |
| structured output contract | Instruction + Verifier | solver cannot discover a legitimately graded schema |
| package hygiene | Compliance | forbidden/extraneous/leaked files |

## Producer loop

If a reviewer returns REVISE:

1. freeze the report/finding IDs;
2. route only the relevant findings to the appropriate producer/fixer;
3. apply the smallest coherent change;
4. calculate which reviews became stale using `PROTOCOL.md`;
5. rerun those cold reviews; do not simply ask the writer to self-certify.

If the same finding survives two fixes, trigger the circuit-breaker/adjudication process instead of repeatedly rewriting.

## Harbor confirmation and learning

Only `PRE_LLMAJ: PASS` permits the slow Harbor LLMaJ gate.

If Harbor finds an applicable issue that Pre-LLMaJ missed:

- log it in `.terminus/reviewers/LLMAJ_LEARNING_LOG.md`;
- map the miss to the responsible reviewer;
- add/update a regression case in `.terminus/reviewers/REVIEWER_EVALS.md` where useful;
- improve the reviewer policy/calibration only if the lesson generalizes;
- regression-test the changed reviewer policy;
- rerun Pre-LLMaJ;
- retry Harbor only after local PASS.
