# Human Writing Calibration Pack

This file is required evidence for the Instruction Reviewer and Engineering Documentation Reviewer. It is a calibration set, not a style template. Do not copy example wording into tasks.

The goal is not to make text informal or deliberately imperfect. The goal is to make it read like an engineer communicating a real piece of work: selective, context-aware, economical, and uneven only where the underlying information is uneven.

## Core distinction

Human engineering writing usually starts from a work problem and includes only the details needed to act or review it. AI-generated task prose often starts from an imagined complete specification and tries to make every paragraph symmetrical, exhaustive, and self-contained.

A human ticket commonly says:

- what is going wrong;
- what must be true when it is fixed;
- where the relevant system lives;
- one or two constraints that are easy to miss.

It does not usually narrate the full implementation, restate every interface, enumerate every internal field, explain why each requirement exists, or close every possible ambiguity in one polished block.

## High-confidence AI-writing signals

Treat these as signals, not mechanical rules. Several together are strong evidence.

### 1. Synthetic completeness

AI-like:

> Repair the controller so it performs duplicate detection, validates eligibility, preserves atomic financial effects, reconciles population counts and values, gates publication, verifies delivery acknowledgment, writes completion state, and guarantees idempotent retries.

Why it looks generated: the sentence inventories the whole hidden rubric in one perfectly balanced sequence.

More human:

> The EOD rerun is replaying financial work that was already completed. Fix the restart path so existing postings/reservations are resumed rather than created again. The final files should only be published after the existing reconciliation and completion checks are satisfied.

Why: it describes the observed incident and the important outcome. Supporting contract/documentation can carry lower-level semantics.

### 2. One sentence per rubric item

AI-like prose often mirrors verifier construction: requirement A sentence, requirement B sentence, requirement C sentence. Human tickets group related behavior by operational concern.

Bad pattern:

> Internal postings must be atomic. External reservations must be unique. Clearing items must be unique. Ledger entries must balance. Completion records must be unique. Authorizations must be unique.

Better:

> Rerunning the cycle must not repeat a financial effect. That includes internal postings and the external reservation/clearing path, and the resulting ledger must still reconcile.

### 3. Excessive implementation narration

AI-like:

> Modify `run.sh` to query the active reservations table, subtract those values from account capacity, call the COBOL program with the resulting value, then use `INSERT OR IGNORE` when creating clearing rows.

Human outcome wording:

> Existing active reservations still consume payer capacity, and resuming them must not create another reservation or clearing item.

### 4. Schema dumping in the instruction

A structured-output schema is necessary when the solver cannot discover it elsewhere. But copying 15–30 field names into prose when an included interface/contract already defines them is a strong synthetic-spec signal.

Prefer:

> Preserve the output schemas defined in `/app/eod/contracts/eod_contract.md`.

Use inline schema only when the file is not otherwise available or ambiguity would make the task untestable.

### 5. Benchmark preamble

Avoid generic openings such as:

> In this task, you are required to...
> Your goal is to...
> You must carefully...
> The system currently has several issues that need to be resolved...

Real tickets generally start directly with the incident or request.

### 6. Essay transitions

Watch for repeated connective language that adds no engineering information:

> Additionally...
> Furthermore...
> Moreover...
> It is important to note that...
> In order to ensure...
> This will ensure that...

Delete unless the transition genuinely clarifies causality.

### 7. Symmetrical three-part prose

AI often produces paragraphs with an even cadence: problem sentence, implementation sentence, validation sentence. Do not force paragraph symmetry. Let the information density determine the shape.

### 8. Unnecessary justification

Bad:

> This is important because duplicate financial effects can result in inconsistent downstream state and customer impact.

If the incident already says financial effects are duplicated, the justification is obvious and consumes words.

### 9. Reviewer-facing leakage

Avoid phrases like:

> The verifier will check...
> Hidden tests include...
> To pass all tests...
> The expected solution should...

Instructions are for the engineer solving the incident, not the benchmark evaluator.

### 10. Artificially polished domain taxonomy

A generated support document often has exactly five headings, each covering one hidden test family with perfect scope. Real documentation may have structure, but it usually reflects operational ownership or existing system boundaries rather than the grading rubric.

## Human task instruction patterns

Good instructions often fit one of these natural shapes. Do not turn these into templates.

### Incident report

> The batch completes normally from a clean state, but rerunning after the external reservation step duplicates the financial effect and publishes a second clearing row. Make the restart path safe without changing the existing COBOL decision interfaces. The SQL state is authoritative.

### Change request

> Move the service to the new trust store without changing the externally visible TLS behavior. Existing clients and the health check must keep working after a fresh container start.

### Maintenance request

> The current compaction job can drop versions that are still visible to an older snapshot. Fix the retention behavior so compaction remains safe while preserving the existing on-disk format.

### Operational acceptance statement

> When reconciliation is held, no customer/clearing publication should remain from that invocation. A later successful rerun must publish exactly one authoritative result.

Notice: none explains the implementation sequence.

## Human vs AI transformation pairs

### Pair A — too much specification

AI-like:

> Update the implementation so exact source references already present in accepted or completed history are classified as duplicates while payments with matching payer, beneficiary, amount, currency, and purpose but a distinct source reference remain eligible. Ensure that duplicate payments do not generate internal postings, reservations, clearing items, ledger entries, completion records, or success authorizations.

Human:

> Duplicate control is rejecting legitimate repeat business because it treats commercial similarity as a replay. Only an already-accepted source reference should be treated as the same instruction, and a replay must not create another financial effect.

### Pair B — hidden test enumeration

AI-like:

> The implementation must support clean execution, resumed external reservations, completed reruns, blocked beneficiaries, insufficient capacity, failed reconciliation, and missing delivery acknowledgment.

Human:

> Fix this for both fresh and resumed cycles. In particular, a partially completed external payment must be safe to continue, and the normal reconciliation/completion gates still apply.

### Pair C — procedure leak

AI-like:

> Add unique constraints to the posting and clearing tables, use a partial unique index for active reservations, and replace inserts with conflict-aware statements.

Human:

> The database must make repeated execution safe; one payment cannot acquire a second active posting/reservation/clearing effect.

### Pair D — documentation explanation

AI-like:

> The verification strategy is comprehensive because it validates a wide range of scenarios covering normal operation, edge cases, retries, and failure conditions, ensuring robust correctness across the system.

Human:

> The tests rebuild the database for each case and run the submitted batch end to end. They cover a clean cycle, a resumed external payment, a completed rerun, and the two gates that can hold publication/completion.

### Pair E — difficulty explanation

AI-like:

> This task is challenging because it requires understanding multiple interconnected components and ensuring consistency across them while handling edge cases and maintaining idempotency.

Human:

> The awkward part is that a restart can be correct at one layer and still be wrong at the next. Reusing an existing reservation avoids a duplicate debit, for example, but clearing and ledger state still have to agree with that resumed effect.

## Concision discipline for `instruction.md`

Target the minimum text that leaves the task fair and testable.

Before keeping a sentence, ask:

1. Would a competent engineer need this to identify the requested end state?
2. Is it already stated in a supplied contract/interface/readme that the instruction can point to?
3. Does it prescribe a method rather than an outcome?
4. Is it here only because a hidden test exists?
5. Can two adjacent requirements be expressed as one operational invariant?

Delete sentences that fail #1 unless they are necessary constraints. Reference existing documents for #2. Rewrite #3. Reconsider task design for #4. Compress #5.

For Edition 3, prefer one or two short paragraphs. Word count is a diagnostic, not the objective. A 90-word ambiguous prompt is worse than a 150-word precise ticket.

## Engineering documentation is different from task instructions

README / Difficulty / Solution / Verification explanations may be longer, but natural engineering writing still avoids synthetic completeness.

### Difficulty explanation

Should explain the actual reasoning bottleneck. It should not list every feature or say only "multiple components make this complex."

Good questions:

- What plausible partial fix fails?
- What state interaction is easy to miss?
- Why does the bug survive normal happy-path testing?

### Solution explanation

Describe the design decision and invariants, not a file-by-file diff. Mention implementation details only where they explain the key insight.

### Verification explanation

Explain why the scenarios distinguish correct from plausible-but-wrong solutions. Do not claim tests are "comprehensive" or "robust" without saying what failure they expose.

## Documentation anti-pattern bank

Avoid these stock phrases unless they carry specific information:

- "This task is challenging because..."
- "The solution involves..."
- "The tests verify that..."
- "This ensures..."
- "robust and reliable"
- "comprehensive coverage"
- "seamlessly"
- "properly"
- "correctly handles"
- "various edge cases"
- "multiple interconnected components"
- "real-world scenario"
- "production-grade"

The words are not forbidden. The reviewer should reject them when they substitute for concrete reasoning.

## Evidence examples from public benchmark tasks

Public Terminal-Bench examples demonstrate that concise task writing can be extremely short when the environment carries the rest of the contract. One public payments task simply states the worker-startup problem, the required notification semantics and latency, and where dependencies go. Another live-database-cutover task states the migration goal, zero-downtime/consistency requirement, behavioral equivalence and latency requirement. These are useful evidence that a task instruction does not need to restate the whole implementation landscape.

Conversely, some public tasks legitimately contain longer exact schemas or mathematical definitions when those details *are* the task and cannot be discovered from supplied artifacts. Concision must therefore be contextual, not a fixed word-count rule.

## Reviewer protocol

The Instruction Reviewer must read:

1. `instruction.md`;
2. all documents the instruction explicitly references;
3. verifier test names/docstrings or a requirement↔test matrix (not hidden solution details when avoidable);
4. this calibration pack;
5. at least three relevant entries from `.terminus/GOLDEN_TASKS.md` or public task references, chosen for writing diversity rather than topical similarity.

Then produce:

```text
VERDICT: PASS | REVISE
WORD_COUNT:
HUMAN_SIGNAL: LOW | MEDIUM | HIGH
AI_TEMPLATE_SIGNAL: LOW | MEDIUM | HIGH
OVER_PRESCRIPTION: NONE | LOW | MEDIUM | HIGH
SPEC_DUMP: NONE | LOW | MEDIUM | HIGH
MATERIAL_REQUIREMENTS_PRESERVED:
UNNECESSARY_TEXT:
MISSING_CONTEXT:
SUSPICIOUS_PHRASES:
REPLACEMENT_TEXT:
RATIONALE:
```

A `PASS` requires `HUMAN_SIGNAL=HIGH`, `AI_TEMPLATE_SIGNAL=LOW`, no material ambiguity, and no material solution leakage.

## Learning from future evidence

This calibration pack is intentionally versioned. When Harbor LLMaJ, portal review, human committee feedback, or accepted/rejected tasks reveal a new pattern:

- record the exact finding without secret/test leakage;
- classify it as instruction, documentation, originality, verifier, difficulty, or compliance;
- add a generalized positive/negative example here;
- do not overfit to a single review phrase;
- never weaken correctness merely to satisfy a stylistic detector.

The objective is cumulative reviewer calibration, not imitation of one judge.
