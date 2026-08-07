# LLMaJ Learning Log

Purpose: turn expensive Harbor `check` findings into cheaper local reviewer knowledge. This file stores generalized lessons, never secrets or leaked hidden-test content.

## How to use

For every Harbor LLMaJ run:

1. Record task, date/run ID, PASS/FAIL, and the specific review finding.
2. Map the finding to one owner: Task Architect, Verifier Engineer, Originality & Authenticity Reviewer, Difficulty Reviewer, Compliance Auditor, Instruction Reviewer, or Engineering Documentation Reviewer.
3. Decide whether Pre-LLMaJ should reasonably have caught it.
4. If yes, update the responsible reviewer prompt/calibration pack with a generalized rule/example before rerunning Harbor.
5. If no, document why the finding genuinely requires Harbor/model-specific judgment.
6. Do not overfit to one judge phrase; retain only reusable engineering-quality lessons.

## Entry format

```text
### <date> — <task> — Harbor run <id>
RESULT: PASS | FAIL
FINDING:
OWNER:
PRE_LLMAJ_SHOULD_HAVE_CAUGHT: YES | NO
ROOT_CAUSE:
GENERALIZED_LESSON:
CALIBRATION_CHANGE:
RECHECK_REQUIRED:
```

## Current evidence

### 2026-08-07 — payment-eod-control-chain — run 31200979809
RESULT: PASS
FINDING: Harbor LLMaJ completed successfully on the task version validated in run #49.
OWNER: none
PRE_LLMAJ_SHOULD_HAVE_CAUGHT: N/A
ROOT_CAUSE: N/A
GENERALIZED_LESSON: A successful Harbor check is evidence for the technical task version that ran, but it does not waive later instruction/originality/documentation review after substantive text changes.
CALIBRATION_CHANGE: The controller now treats Harbor LLMaJ, Instruction Reviewer, Originality Reviewer, Documentation Reviewer, and difficulty as independent gates.
RECHECK_REQUIRED: YES after the later `instruction.md` rewrite because the solver-facing contract changed.

## Public rubric evidence incorporated into Pre-LLMaJ

The public Harbor benchmark-template review automation/rubric exposes quality lenses including verifiability, solvability, genuine difficulty, real-world interest, outcome-based grading, anti-cheat/security, functional verification, determinism, essential difficulty, instruction/test alignment, novelty, agentic work, reviewability, concise human-written instructions, solution quality, separate-verifier behavior, environment hygiene, structured output schemas, critical identifiers, explanation quality, classification/resources, README quality, schema hygiene, and extraneous files.

These are treated as predictive quality lenses only. Current Terminus Edition 3 rules in this repository remain authoritative where schema or process differs.
