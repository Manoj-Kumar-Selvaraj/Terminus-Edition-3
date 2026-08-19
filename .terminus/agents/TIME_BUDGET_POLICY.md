# Terminus Task Time Guidance

Time-guidance policy version: `1.1`

Task duration is **planning guidance only**. Elapsed time is not lifecycle
authority and must never change gate state, block a stage, request a time
extension, stale otherwise-current evidence, or weaken a quality requirement.

## Default guidance

For every task, use **7 hours** (`25200` seconds) as the default end-to-end
planning guideline.

This is not a deadline or hard limit. A task may finish earlier or later. If the
guideline is exceeded, continue the canonical mandatory lifecycle and report the
elapsed time as advisory telemetry only.

## No per-stage time enforcement

Do not assign or enforce per-stage time envelopes. In particular:

- no stage may be stopped because its suggested duration elapsed;
- no controller action may become `REQUEST_TIME_EXTENSION` because of time;
- no human approval is required to continue after seven hours;
- no model/Q/Harbor/deterministic gate may be skipped or weakened to save time;
- queued GitHub Actions time is not a reason to redispatch a duplicate run;
- a still-valid in-flight action remains `PENDING`, not `BLOCKED`, merely because
  a chat polling interval or planning guideline elapsed.

## Optional telemetry

`.terminus/execution/time_budget.py` and
`.terminus/execution/budget_controller_cli.py` remain available for optional
append-only time telemetry under:

`.terminus/executions/<task-id>/time_budget/`

Telemetry may record stage/run duration and category totals. It is diagnostic
only. The canonical workflow ledger remains the sole authority for lifecycle
state and routing.

The advisory projection may report:

- seven-hour guidance in seconds;
- consumed telemetry seconds;
- remaining advisory seconds;
- whether the guidance has been exceeded;
- per-stage and per-category totals.

It must always report `enforcement: ADVISORY_ONLY`, must never project a hard
limit, and must never override the canonical controller's `next` action.

Historical extension records may remain readable for compatibility. They are
legacy metadata only and do not grant or withhold routing authority.

## Polling and waiting

Do not impose a task-level or stage-level timeout merely because GitHub Actions,
Harbor, or another required external execution is queued or running.

The Orchestrator should poll the exact known run/job while its active execution
surface permits. Poll cadence and progress-update cadence are operational
suggestions, not lifecycle deadlines. If the active chat/tool surface ends or
cannot continue polling, return `PENDING` with the exact durable run/job locator
and resume from that same execution later. Never redispatch solely because a
foreground waiting period ended.

## Quality invariant

**Time affects prioritization, never acceptance.**

The agent may avoid speculative cleanup, duplicate validation, or optional
analysis when a task is taking longer than expected. It must still complete all
mandatory deterministic, semantic, quality, external-model, difficulty, final
review, and packaging requirements that apply to the task.
