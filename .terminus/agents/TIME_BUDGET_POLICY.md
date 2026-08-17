# Terminus Task Time Budget Policy

Time-budget policy version: `1.0`

This policy constrains **workflow execution time**, not quality standards. A task
must still satisfy every mandatory deterministic and semantic gate required by
the active Terminus policy. The controller may change strategy, consolidate
repairs, stop optional work, or ask the human owner for more time; it must never
turn a time limit into a fabricated PASS or an implicit gate waiver.

## Default budget

For every new task:

- target budget: **4 hours** (`14400` counted seconds);
- hard budget: **5 hours** (`18000` counted seconds);
- default suggested extension after a hard-limit breach: **60 minutes**.

A task may finish earlier. The 4-hour target is a planning target. The 5-hour
limit is the point at which autonomous continuation stops.

## Counted time

Count active execution attributable to the task, including:

- creator/producer/fixer/reviewer stage execution;
- deterministic validators, builds and tests;
- GitHub Actions/Harbor/model runs when their execution time is part of the
  active task workflow;
- repair/refreeze work;
- adjudication and repeated review attempts;
- tool or infrastructure failures while the workflow is actively attempting
  the task.

Do not count inactive human waiting, overnight inactivity, provider outage
waiting, or credential waiting after the dependency has been classified and no
work is being performed. Manual-chat timing may therefore subtract explicitly
recorded `paused_seconds`.

## Durable accounting

Use `.terminus/execution/budget_controller_cli.py` as the budget-aware wrapper
around the canonical controller CLI.

It writes append-only task timing data under:

`.terminus/executions/<task-id>/time_budget/`

Every routed stage must have a START/FINISH span, and independent CI/model/run
time that is not already included in a stage span must be recorded with
`record-run`. Do not double-count a run already fully contained in a counted
stage span.

The canonical workflow ledger remains the authority for gate state. The time
ledger is authority only for time accounting and budget routing.

## Adaptive modes

The budget projection assigns one mode:

- `NORMAL`: under 50% of target;
- `BUDGET_AWARE`: 50% to under 70%;
- `CONSERVE`: 70% to under 85%;
- `CRITICAL`: 85% of target through the hard limit;
- `HARD_LIMIT`: counted time is at or above the effective hard limit.

Required behavior:

### NORMAL

Proceed normally while avoiding speculative breadth.

### BUDGET_AWARE

Keep stages bounded, prefer targeted evidence, and preserve reserve for all
remaining mandatory gates.

### CONSERVE

Stop optional analysis. Consolidate compatible repairs. Reuse current,
Protocol-valid evidence. Do not repeat full repository reviews or deterministic
runs without new evidence or a changed dependency.

### CRITICAL

Take the shortest **protocol-valid** route to an acceptance decision. Do not
perform speculative cleanup, stylistic polishing, or ordinary no-progress
loops. A material defect may still require repair; quality is not weakened.

### HARD_LIMIT

Do not invoke another stage.

Return `REQUEST_TIME_EXTENSION` to the human owner with:

- counted time;
- effective hard limit;
- mandatory work still remaining;
- suggested extension;
- the reason more time is required.

Only explicit human approval may extend the budget.

## Human extension

Record explicit approval with:

```bash
python .terminus/execution/budget_controller_cli.py --root . extend \
  --task-id <task> \
  --minutes <minutes> \
  --approved-by <human-identity> \
  --reason "<why the extension is justified>"
```

An extension increases both the target and hard limits by the approved amount,
preserving the one-hour planning reserve between the original target and hard
limit.

The agent must not infer consent from silence, prior tasks, or a general desire
to finish. If the hard limit is reached, ask.

## Controller commands

Use the wrapper for normal controller operations:

```bash
python .terminus/execution/budget_controller_cli.py --root . status ...
python .terminus/execution/budget_controller_cli.py --root . next ...
python .terminus/execution/budget_controller_cli.py --root . continue ...
python .terminus/execution/budget_controller_cli.py --root . record ...
```

`continue` starts the timed span for the routed stage. `record` closes that span
only after the canonical controller accepts the result. Use `--paused-seconds`
to remove genuine inactive waiting.

Record separate quality/CI/model execution when required:

```bash
python .terminus/execution/budget_controller_cli.py --root . record-run \
  --task-id <task> \
  --stage-id <stage> \
  --seconds <seconds> \
  --category DETERMINISTIC_VALIDATION \
  --run-ref <run-or-job-id>
```

## Planning output

Every budget-aware `status`, `next`, and `continue` projection includes:

- target and hard limits;
- consumed and remaining seconds;
- burn ratio and adaptive mode;
- per-stage and per-category totals;
- remaining mandatory stage count;
- recommended next-stage time envelope;
- a concrete budget directive.

The Orchestrator must carry that directive into specialist handoffs. Specialists
should use the envelope to choose depth and sequencing, but must still return
the stage's complete required output.

## Time categories

Use one of:

- `PLANNED_EXECUTION`
- `QUALITY_REVIEW`
- `DETERMINISTIC_VALIDATION`
- `SEMANTIC_REPAIR`
- `REVIEWER_REWORK`
- `INFRA_FAILURE`
- `AGENT_TOOL_FAILURE`
- `UPLOAD_FAILURE`
- `POLICY_DISAGREEMENT`
- `UNNECESSARY_LOOP`
- `OTHER`

These categories are learning signals. They are intended to reveal where task
time is being lost so future task design and stage envelopes can improve.

## Non-negotiable invariant

**Quality requirements remain fixed; strategy and task scope adapt to budget.**

Time pressure may justify a simpler initial architecture, fewer optional
refinements, consolidated repairs, valid evidence reuse, or an explicit request
for more time. It never justifies hidden test weakening, skipped mandatory
acceptance evidence, false PASS, or silent continuation beyond the approved
hard limit.
