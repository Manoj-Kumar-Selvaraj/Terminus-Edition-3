# Writing Example Bank

These examples are synthetic calibration data for Terminus reviewers. They are not templates and must not be copied verbatim. The reviewer should learn the *difference in information selection and cadence*, not imitate phrases.

## Task instruction pairs

### 1. Generic opening
**AI-like:** In this task, you are required to repair a production batch processing system that currently exhibits several issues during restart scenarios.

**Human:** The nightly batch is safe from a clean start, but a restart after settlement can replay work that already completed.

### 2. Rubric enumeration
**AI-like:** Ensure duplicate detection, execution eligibility, posting, reservation, clearing, reconciliation, completion, and authorization all behave correctly.

**Human:** Make the restart path safe end to end. Existing financial effects should be resumed, and nothing should publish before the normal reconciliation/completion gates pass.

### 3. Procedure leak
**AI-like:** Add unique indexes, update the SQL queries, change the shell conditions, and use conflict-aware inserts to enforce idempotency.

**Human:** Reprocessing the same payment must not create a second posting, active reservation, clearing item, or authorization.

### 4. Hidden-test list
**AI-like:** Your implementation must handle fresh runs, completed reruns, partial reservations, blocked accounts, insufficient balances, held reconciliation, and missing acknowledgements.

**Human:** Fix both fresh and resumed cycles. A partially completed external payment should be safe to continue, and the existing hold conditions still apply.

### 5. Excessive path narration
**AI-like:** Modify `/app/service/bin/run.sh`, `/app/service/sql/schema.sql`, `/app/service/src/check.c`, and `/app/service/conf/policy.json` as needed.

**Human:** Repair the service under `/app/service`; keep the existing policy interface and persistent state authoritative.

### 6. Obvious justification
**AI-like:** This is important because repeated settlement can create duplicate financial effects and impact customers.

**Human:** Omit the sentence; the incident already says settlement is duplicated.

### 7. Schema dump
**AI-like:** The JSON output must contain `id`, `date`, `source`, `status`, `count_a`, `count_b`, `sum_a`, `sum_b`, `difference`, `reason`, and `run_id`.

**Human:** Preserve the reconciliation schema defined in `/app/contracts/reconciliation.md`.

### 8. Unnecessary politeness/preamble
**AI-like:** Please carefully review the existing implementation and make the necessary changes so that all expected behaviors are satisfied.

**Human:** The service loses the active route after a config reload. Fix reloads without changing the client-facing endpoint.

### 9. Artificial completeness
**AI-like:** The solution must be robust, production-ready, deterministic, idempotent, secure, scalable, and maintainable.

**Human:** State only the actual required invariant(s).

### 10. One test per sentence
**AI-like:** A blocked user must be rejected. An expired token must be rejected. A valid token must be accepted. A rotated key must be accepted.

**Human:** Token validation must continue to reject invalid identities across key rotation while valid clients keep working.

### 11. Reviewer leakage
**AI-like:** Hidden tests will verify that no stale cache file remains after restart.

**Human:** A restart must not reuse stale cache state.

### 12. Overexplained constraint
**AI-like:** Do not replace the parser with Python because the goal of this task is to ensure that the existing C implementation remains responsible for parsing.

**Human:** Keep parsing in the existing C component.

## Difficulty explanation pairs

### 13. Generic complexity claim
**AI-like:** This task is challenging because it involves multiple interconnected components and requires careful reasoning across several edge cases.

**Human:** A fix can be correct at the reservation layer and still duplicate clearing on restart. The hard part is preserving one authoritative effect across components that recover independently.

### 14. Feature list posing as difficulty
**AI-like:** The task includes COBOL, SQL, shell scripting, reconciliation, accounting, and idempotency, making it complex.

**Human:** Language count is not the difficulty. Explain which state interaction makes a plausible partial fix fail.

### 15. Inflated praise
**AI-like:** Solving this requires deep expertise and sophisticated reasoning.

**Human:** Omit self-assessment; describe the actual trap.

### 16. Test narration
**AI-like:** The task is difficult because there are many tests that cover many different scenarios.

**Human:** The happy path hides the bug; it only appears when state from an earlier attempt is already durable.

## Solution explanation pairs

### 17. Diff walkthrough
**AI-like:** First I changed the schema, then I updated the shell script, then I modified the duplicate program, and finally I fixed the output generation.

**Human:** The repair makes prior financial effects authoritative. Resume decisions no longer execute them again, and publication derives from reconciliation/completion state rather than control-flow success.

### 18. Empty abstraction
**AI-like:** I implemented a robust idempotent architecture that ensures consistency across all components.

**Human:** Say what becomes idempotent and which state is authoritative.

### 19. Implementation trivia
**AI-like:** I used `INSERT OR IGNORE` in three places and `BEGIN IMMEDIATE` in another place.

**Human:** Database constraints make duplicate effects impossible, while the controller distinguishes new execution from resume.

### 20. Claim without rationale
**AI-like:** The solution is efficient and reliable.

**Human:** Omit unless efficiency/reliability is actually measured and explain the evidence.

## Verification explanation pairs

### 21. Generic coverage
**AI-like:** The tests provide comprehensive coverage of normal behavior and edge cases to ensure robust correctness.

**Human:** Each case rebuilds state, runs the submitted workflow, and checks resulting database/artifacts. The resume case starts with an existing reservation so reinserting it fails semantically rather than merely syntactically.

### 22. Restating assertions
**AI-like:** One test checks that the count is four, another checks that the status is balanced, and another checks that the file exists.

**Human:** Explain what class of wrong solution those assertions rule out.

### 23. Overclaim
**AI-like:** The verifier proves the implementation is fully correct.

**Human:** The verifier checks the stated contract under the modeled scenarios; do not claim more.

### 24. Test-file implementation detail
**AI-like:** `test_outputs.py` calls `reset_db()`, then `run_batch()`, then `rows()`.

**Human:** The verifier recreates independent database states and exercises the submitted batch end to end.

## Review-feedback pairs

### 25. AI reviewer voice
**AI-like:** Overall, the instruction is well-structured and comprehensive, but there are several opportunities to improve clarity and concision.

**Human reviewer:** Too much of the second paragraph is a schema dump. The contract already defines those fields; keep the incident and publication rules here and point to the contract for the schema.

### 26. Vague criticism
**AI-like:** The task could be made more realistic and less templated.

**Human reviewer:** The starter has one planted defect for nearly every verifier requirement. Collapse that into two coupled restart faults so the solver has to trace state rather than tick off a checklist.

### 27. Vague approval
**AI-like:** The task appears sufficiently difficult and realistic.

**Human reviewer:** The restart path crosses duplicate classification, durable reservation state and clearing publication, so a local fix can still fail end-to-end. I do not see a single-command shortcut.

### 28. Style-only humanization
**AI-like approach:** Replace formal words with casual words and add contractions.

**Correct approach:** Change information selection, remove synthetic completeness, combine related invariants, and preserve the engineer's actual operational concern. Human writing is not slang.

## Signals reviewers should learn

- Human text is selective; AI text tends toward exhaustive coverage.
- Human tickets privilege the incident and end state; AI prompts often privilege the rubric.
- Human explanations focus on one or two real insights; AI explanations summarize the entire artifact.
- Humans may use exact schemas when necessary, but do not repeat them when an authoritative interface already exists.
- Short is not automatically human. A compressed rubric checklist is still synthetic.
- Imperfect grammar is not a target. Deliberately adding mistakes is not humanization.
- Domain jargon helps only when it is the natural vocabulary of the system, not when inserted to sound expert.
