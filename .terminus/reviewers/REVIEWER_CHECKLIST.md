# Terminus 3 Comprehensive Reviewer Checklist

Checklist snapshot version: `2026-08-08-user-supplied`

Source supplied by the project owner:
`https://snorkel-ai.github.io/Terminus-EC-Training-stateful/portal/docs/reviewing-tasks/reviewer-checklist`

The public page states that criteria and severities evolve. When the live page is accessible, refresh this snapshot before relying on it for a final submission review. If the live checklist, current Edition 3 repository rules, and this snapshot disagree, record a `POLICY_CONFLICT`; do not silently choose a rule. Current explicitly authoritative Edition 3 rules and explicit project acceptance policies control until the conflict is resolved.

## Review philosophy

A review is exhaustive, not fail-fast.

The reviewer must:

- catch issues before they enter the dataset;
- help the contributor improve the task;
- maintain consistency across submissions;
- inspect **all applicable criteria**, even after finding a rejection-level issue;
- report every material issue found, not only the first blocker;
- make feedback clear, complete, actionable, and specific enough that fixing the listed issues should leave the task ready for acceptance unless new issues appear;
- distinguish observed defects from uncertainty or policy conflict;
- provide file/test/run evidence for every material finding.

A review is incomplete if it stops after the first error.

## Severity guidance

### High

Any failed High criterion blocks acceptance. The task must be revised or declined.

### Medium

- Multiple failed Medium criteria block acceptance.
- A single Medium failure may still be accepted, but the acceptance note must explicitly record it.
- Trial-analysis criteria have special handling below; valid trial-analysis flags can require revision regardless of the normal multiple-Medium rule.

### Low

Low-only failures do not block acceptance. If the task is already being sent to revision for High/Medium issues, include Low issues in the revision feedback too.

## Final recommendations

The Comprehensive Reviewer returns one of:

- `APPROVE` — no blocking issue and no unresolved Medium note;
- `APPROVE_WITH_NOTE` — exactly one ordinary Medium issue, no High issue, no valid trial-analysis revision flag;
- `REQUEST_CHANGES` — a fixable High issue, multiple ordinary Medium issues, or any valid trial-analysis revision flag;
- `DECLINE` — fundamental issue not reasonably salvageable, e.g. essential duplicate, fundamentally flawed core concept, or an acceptance-policy difficulty failure that cannot be repaired without replacing the task;
- `INSUFFICIENT_EVIDENCE` — required evidence is unavailable;
- `POLICY_CONFLICT` — current authoritative sources materially disagree and the reviewer cannot safely decide which rule controls.

## 1. Read the task description

### Authentic prompt styling

Every task instruction should satisfy all six principles:

1. concise;
2. well specified;
3. interesting/useful;
4. no answers or solution hints;
5. unique;
6. absolute paths.

The instruction should read like a realistic prompt a developer/user would give a coding agent, not like a benchmark rubric or an implementation walkthrough.

### Instruction criteria

#### RC-INS-001 — Task instruction is concise — Medium

Use roughly two short paragraphs or up to about 20 bullets as a guide, allowing more when the task itself genuinely needs it. Flag length caused by listing steps, restating requirements, or creating instruction-following burden rather than engineering difficulty.

#### RC-INS-002 — Task instruction is well specified — High

The goal and measurable success state must be clear. Reject tasks whose apparent difficulty comes mainly from a large number of poorly specified edge cases/requirements.

#### RC-INS-003 — Task instruction is interesting — High

The task must be useful or interesting to a plausible group of developers/users, not obscure for obscurity's sake.

#### RC-INS-004 — Instruction does not provide solution hints — High

Requirements are allowed; stepwise guidance, significant implementation hints, answer leakage, or rubric-like solution instructions are not.

#### RC-INS-005 — Environment contains no hidden instructions/hints — High

Environment files, comments, READMEs, configs, scripts and TODOs must not contain a solution walkthrough or prescriptive guidance that bypasses instruction quality rules.

#### RC-INS-006 — Environment spec/docs are realistic and do not bypass instruction rules — High

Solver-visible specs may define requirements, schemas and protocols, but must not be step-by-step solution guides; must not be used to move the logical task prompt out of `instruction.md` merely to shorten it; and should read like realistic engineering artifacts rather than polished LLM prompt extensions.

#### RC-INS-007 — Instruction is unique — High

The initial state/instruction or expected output must differ non-trivially from previously submitted/open-source benchmark tasks. Similarity search is supporting evidence, not the sole decision.

#### RC-INS-008 — Referenced paths are absolute — High

Use absolute references such as `/app/config/settings.json`, not `./config/settings.json`.

#### RC-INS-009 — No canary string in instruction.md — Medium

A canary string usually signals an older task skeleton and should not be present in solver prompt data.

#### RC-INS-010 — Task name not present in instruction.md — Medium

Do not include the benchmark task name/header in `instruction.md`.

### Common instruction issues

Flag ambiguous language such as "make it better", "fix the issues", "handle errors properly", or "optimize the code" when no measurable outcome is defined. Output paths/formats must be specified or clearly discoverable from a solver-visible contract. Unverifiable process requirements such as "use vim" are inappropriate unless actual tool use can be meaningfully verified.

## 2. Review tests

### Core test checklist

- every material instruction requirement has corresponding verification;
- tests have informative docstrings;
- tests verify behavior/outcomes rather than implementation preference;
- avoid brittle exact string matching when formatting is not itself the requirement;
- thresholds are justified and not arbitrary;
- tests are independent and do not rely on execution order;
- randomness is checked by properties/distributions rather than one hardcoded random sequence;
- test complexity is proportionate to the task.

### Test-quality eval categories

The automated test-quality eval is a helper, not a replacement for manual review. Independently review first, then inspect every flag:

- `req-gap` — instruction requires behavior no test asserts;
- `weak-assertion` — a test is too permissive to reject wrong solutions;
- `phantom-spec` — tests enforce behavior not solver-visible in the instruction/legitimate referenced contract;
- `flaky-execution` — correct behavior may fail due to timing, nondeterminism or infrastructure;
- `vacuous-test` — test can pass without validating the claimed behavior.

Every flag must be examined; false positives must be explicitly justified.

### Verifier criteria

#### RC-VER-001 — Reward assignment is reliable — High

`tests/test.sh` must assign `/logs/verifier/reward.txt` on normal success/failure paths. Do not require a trailing `exit $?` after the canonical reward block; Harbor uses reward.txt rather than the script exit code for scoring.

#### RC-VER-002 — Oracle and agent use the exact same verifier logic — High

No conditional logic may give the oracle different grading behavior.

#### RC-VER-003 — Verifier network use matches network_mode — High

For `no-network`, verifier files must not fetch runtime content and dependencies must be baked into the verifier image. For `public`, network use is only acceptable where the task genuinely requires it and grading remains deterministic.

#### RC-VER-004 — Binary rewards only — High

Reward must be 0 or 1, not partial scoring based on passed test count.

#### RC-VER-005 — Verifier aligned with instructions — High

All substantive tests must map to explicit or reasonably implicit solver-visible requirements.

#### RC-VER-006 — Verifier checks correctness, not just format — High

Formatting checks alone are insufficient when semantic correctness can be exercised.

#### RC-VER-007 — Solution logic is not reimplemented in tests — Medium

Tests may run the agent program, parse outputs, use precomputed goldens/hashes, spec-derived invariants or sealed held-out truth. They should not contain a second complete solver that maps task inputs to the expected artifact.

#### RC-VER-008 — Config-driven values are read dynamically when required — Medium

If the instruction requires reading mutable config/input parameters, verifier expectations should derive those values at runtime rather than duplicate literals that allow hardcoding. Exact fixed expected results remain valid when the contract itself fixes them.

### Test anti-patterns

Flag:

- source grep/AST checks used only to enforce implementation choices when behavior can be run;
- exact whole-string comparisons when equivalent formatting should pass;
- tests without informative docstrings;
- order-dependent tests;
- hardcoded random sequences;
- test files disproportionately large for a simple task;
- tests whose mutable expected data can simply be edited by the agent to obtain reward.

## 3. Test-quality eval double-check

The Comprehensive Reviewer must record a disposition for every available test-quality eval flag:

`CONFIRMED_DEFECT | FALSE_POSITIVE | NOT_APPLICABLE | INSUFFICIENT_EVIDENCE`.

No flag may be ignored.

## 4. Check the solution/oracle

#### RC-SOL-001 — Oracle is deterministic and consistently passing — High

No unseeded randomness, fragile latency dependence, hardware-dependent race or similar source of flaky oracle success.

#### RC-SOL-002 — Oracle internet use matches network_mode — High

For `no-network`, all required dependencies must already be present. `public` may use network only when genuinely required by the task.

#### RC-SOL-003 — Oracle reflects instruction.md — High

The oracle must implement every material requirement, not merely whatever current tests happen to check. It must demonstrate actual computation/repair rather than hardcoding expected outputs.

### Solution anti-patterns

Flag hardcoded final answers, nondeterministic commands where stable output is required, incomplete solutions, unnecessary complexity, or missing error handling that lets the script continue after critical failures.

## 5. Verify environment

#### RC-ENV-001 — Build scripts do not fetch arbitrary web content — High

Internet fetches during environment construction should be package dependencies only. Task data/content that must be downloaded should instead be stored locally or otherwise satisfy current authoritative packaging rules.

#### RC-ENV-002 — network_mode matches actual need — High

`public` is the normal default. Use `no-network` only when network access would invalidate the task, such as exposing the answer.

#### RC-ENV-003 — Non-apt dependencies are pinned — High

Pin pip/npm/etc. versions. Apt packages are treated separately.

#### RC-ENV-004 — Environment build context is self-contained — High

Environment/docker build context must not depend on content outside `environment/` through `../` context capture.

#### RC-ENV-005 — No oracle/ground-truth leakage in environment — High

Solution artifacts belong only in `solution/`; verifier artifacts belong only in `tests/` and are mounted by Harbor.

#### RC-ENV-006 — No dangerous Docker operations — High

Reject requirements for privileged mode, dangerous capabilities such as SYS_ADMIN/NET_ADMIN/SYS_MODULE, Docker socket mounts, or comparable host-escape exposure.

#### RC-ENV-007 — No reserved mount conflicts — High

Do not create/modify conflicting Harbor reserved mounts such as `/logs/artifacts/`, `/logs/verifier/`, `/tests/`, `/solution/` (or `/oracle/` where applicable in runtime semantics).

#### RC-ENV-008 — No AI-framework scaffolding filenames — High

Remove task-environment artifacts such as `CLAUDE.md`, `skills.md`, `AGENTS.md`, `.cursor/` and similar framework leftovers. Professionally named task-specific documentation is fine.

#### RC-ENV-009 — Docker images are digest pinned — High

Every `FROM` and compose image must include `@sha256:<digest>`.

#### RC-ENV-010 — Canonical runtime base image or credible justification — High

Use a canonical Terminal-Bench base when one fits. A non-canonical runtime image requires a brief, specific, credible justification; boilerplate justification or a reason contradicted by an existing canonical base is not acceptable.

#### RC-ENV-011 — Build context size stays within limits — High

`environment/` <= 100 MiB total and no single file > 50 MiB.

#### RC-ENV-012 — Apt usage is clean/reproducible — Medium

Prefer one `apt-get update && apt-get install -y --no-install-recommends ... && rm -rf /var/lib/apt/lists/*` transaction per stage; avoid apt upgrade and apt version pins when current CI forbids them.

#### RC-ENV-013 — Non-trivial environment has .dockerignore — Medium

Exclude `.git`, caches, `node_modules`, `.env`, `solution/`, `tests/` and other irrelevant/secrets-heavy context.

#### RC-ENV-014 — Avoid Dockerfile heredocs — Low

Store source as files and COPY them rather than embedding large source/config via heredocs.

### Required agent runtime

Every task image must include the agent runtime dependencies required by current Terminus/Harbor policy, including `tmux` and `asciinema` where the active rule set requires them.

## 6. Verify metadata

#### RC-META-001 — Required task.toml fields present — High

The supplied checklist snapshot expects top-level `artifacts`, task name, and a `[metadata]` section including author, category/subcategory, tags, languages, difficulty, expert estimate, difficulty/solution/verification explanations and relevant experience; `[verifier]`, `[agent]`, and `[environment]` timeout/resource/network fields are also expected. Descriptive fields are expected under `[metadata]`; `artifacts` remains top-level.

**Policy-conflict rule:** if the active Edition 3 schema/validator differs from this snapshot, do not invent or move fields blindly. Record `POLICY_CONFLICT` and follow the current authoritative validator/rule source once resolved.

#### RC-META-002 — Multi-container flag is correct — High

If the task is truly multi-container, `[metadata].is_multi_container = true` should be present where current schema requires it. Do not flag its absence for single-container tasks.

#### RC-META-003 — Category/subcategory/tags/languages match task — Medium

Metadata taxonomy must reflect actual task content.

#### RC-META-004 — Difficulty matches measured behavior — High

Difficulty label must align with accepted empirical pass-rate policy, not author intent.

#### RC-META-005 — Time estimates are realistic — Medium

Expert estimate should reflect actual expected work; do not use inflated estimates to imply difficulty.

#### RC-META-006 — Timeouts are sufficient but not excessive — High

Timeouts must give a capable agent/verifier enough time without using time pressure as the source of difficulty.

#### RC-META-007 — Optional GPU/resource fields are not mandatory — Not Applicable / informational

Do not reject solely because optional `gpus`, `gpu_types`, or `docker_flags` are omitted/blank when the task does not need them.

## 7. Watch and analyze agent runs

### Solvable vs one complete pass

The supplied reviewer checklist defines *solvable* as: across 10 runs, every individual verifier test passes at least once, even if no single run passes the whole suite.

The existing local controller currently uses a custom five-run difficulty policy. Until those are reconciled, record a `POLICY_CONFLICT` rather than treating five runs as equivalent to the checklist's ten-run solvability definition.

Review terminal recording, analysis/debug panes and trajectories. For failures ask whether the agent failed for a legitimate reasoning reason or because of ambiguity, verifier/environment defects, timeout, refusal or infrastructure.

### Trial-analysis criteria

#### RC-TRIAL-001 — task_specification not flagged — High

A valid flag means the solver lacked necessary parameter names, formats, return values or other behavior required by tests. Send for revision.

#### RC-TRIAL-002 — reward_hacking not flagged — High

A valid flag includes manipulating tests/reward files, accessing solution, or otherwise gaming the harness. Send for revision.

#### RC-TRIAL-003 — difficulty_crux examined — Medium, special handling

Check whether the actual failure reason matches the claimed difficulty explanation. If the flag is valid, send for revision; if false positive, record why. The normal multiple-Medium rule does not override this per-flag decision.

#### RC-TRIAL-004 — near_miss examined — Medium, special handling

If many runs are substantively correct but narrowly miss an arbitrary threshold, the threshold may be manufacturing difficulty. If valid, revise; otherwise document false positive.

#### RC-TRIAL-005 — refusals examined — Medium, special handling

If agents refuse due to content/safety rather than engage with the task, examine whether the task itself needs revision. Distinguish from provider failures during Harbor check.

#### RC-TRIAL-006 — low_timeout examined — Medium, special handling

If the agent was making meaningful progress at timeout or completed only just before it, raise timeout so difficulty comes from the task rather than time pressure.

Every available trial-analysis flag requires an explicit disposition. A valid special Medium trial flag can require revision even if it is the only Medium issue.

## 8. Review rubrics when applicable

#### RC-RUB-001 — Rubrics do not reference test logic — High

Agent-trace rubrics must not tell the grader to inspect `/tests/` results.

#### RC-RUB-002 — Rubrics do not reference task.toml/instruction.md — High

The agent trace does not have those artifacts as rubric context; do not use them as rubric criteria references.

#### RC-RUB-003 — Scores use only allowed values — High

Allowed scores are `+1`, `+2`, `+3`, `+5`, `-1`, `-2`, `-3`, `-5`.

#### RC-RUB-004 — Positive scores include explicit `+` — High

Unsigned positive scores are invalid.

#### RC-RUB-005 — Rubric line formatting is correct — High

Each criterion is one line, starts with `Agent`, and ends with `, <score>`.

#### RC-RUB-006 — Criteria are detailed and precise — High

Avoid vague or conditionally applicable criteria that cannot reliably grade the trace.

#### RC-RUB-007 — At least one negative criterion — Medium

Rubric should include at least one negative criterion.

#### RC-RUB-008 — Score magnitude matches importance — Medium

Critical behavior uses the most extreme magnitude; minor/major behavior uses proportionate weights.

#### RC-RUB-009 — Criteria use positive-language event descriptions — Medium

Describe the observable action positively and use negative reward when the action is undesirable.

#### RC-RUB-010 — Rubric does not mention Oracle/NOP — Medium

Agent trace rubric should not refer to runs the agent does not know about.

#### RC-RUB-011 — Maximum positive point range is 10–40 — Low

Treat as nice-to-have unless current platform validation makes it stricter.

## 9. Review task structure and package hygiene

#### RC-STRUCT-001 — Required task files are present — High

Checklist snapshot expects `task.toml`, `instruction.md`, `environment/Dockerfile`, `solution/solve.sh`, `tests/Dockerfile`, `tests/test.sh`, `tests/test_outputs.py`.

The supplied checklist states that `rubrics.txt` and `README.md` may be platform-added rather than expected in the submitted ZIP. If current Edition 3 repository rules require a different layout, record the discrepancy as `POLICY_CONFLICT` rather than silently deleting/adding files.

#### RC-STRUCT-002 — No unnecessary parent-directory files — Low

Remove leftover `jobs/`, redundant top-level `data/`, debug/backup artifacts and other unused content.

## 10. Anti-cheating review

Think adversarially about how an agent could receive reward without solving the intended task:

- reading/decompiling hidden answers;
- replacing programs with dummies that exploit weak tests;
- deleting/modifying tests;
- writing reward files directly;
- reading/copying solution artifacts;
- accessing newer Git commits containing answers;
- editing mutable expected-data files instead of implementing computation;
- exploiting verifier assumptions, environment leakage or source-only checks.

A suspected cheat opportunity must cite a concrete exploit path, not generic speculation.

## 11. Review actions and feedback quality

### Approve

Use only when the task is ready under the severity policy, or `APPROVE_WITH_NOTE` for one ordinary Medium issue allowed by severity guidance.

### Request changes

Feedback must say:

- what is wrong;
- where it is;
- why it violates a criterion;
- how to fix the problem at the outcome level;
- what should be rechecked afterward.

Good feedback identifies the exact test/file/line/behavior and proposes a principle-based repair. Avoid vague notes like "tests need work."

### Decline

Use for fundamental issues that are not easily salvageable, including an essential duplicate, fundamentally flawed core concept, or difficulty failure that invalidates the task under current acceptance policy. Explain whether any realistic revision could salvage it.

## 12. Comprehensive review completion contract

The reviewer must produce:

```text
REVIEWER_CHECKLIST_VERSION:
TASK_COMMIT:
POLICY_FRESHNESS: CURRENT | UNVERIFIED | STALE
CHECKLIST_COVERAGE: 100%
RECOMMENDATION: APPROVE | APPROVE_WITH_NOTE | REQUEST_CHANGES | DECLINE | INSUFFICIENT_EVIDENCE | POLICY_CONFLICT
HIGH_FAILURE_COUNT:
MEDIUM_FAILURE_COUNT:
LOW_FAILURE_COUNT:
SPECIAL_TRIAL_REVISION_FLAGS:
POLICY_CONFLICTS:
TEST_QUALITY_EVAL_DISPOSITIONS:
TRIAL_ANALYSIS_DISPOSITIONS:
ALL_FINDINGS:
- ID:
  CRITERION_ID:
  SEVERITY:
  STATUS: OBSERVED | INFERRED
  EVIDENCE:
  WHAT_IS_WRONG:
  WHY_IT_MATTERS:
  REQUIRED_FIX:
  RECHECK:
ACCEPTANCE_NOTES:
```

The reviewer must enumerate **all applicable failed criteria** before finalizing the recommendation.
