# Active-Turn Autonomous Orchestration

Active-turn autonomy policy version: `1.0`

This policy governs how the Terminus CI Orchestrator behaves after a user has authorized work on one task in an active ChatGPT/Cursor/repository-aware execution turn. It does not create a background daemon, does not authorize new paid/model-backed work by itself, and does not weaken any lifecycle, independence, evidence, budget, or external-gate rule.

## Default run policy

The default active-turn policy is `RUN_TO_BLOCKER`.

Once task execution has begun, the Orchestrator must continue the canonical lifecycle without requiring the user to send `continue`, `proceed`, `poll`, `check the run`, or `what's next?` while a legal already-authorized next action remains executable in the current surface.

A routing cycle completing is not a response-completion condition. After every accepted StageResult, canonical record, ledger append and replay/materialization, immediately call or reconstruct the current `controller_cli continue` result and execute the next legal route.

## Non-stop conditions

None of the following is, by itself, a valid reason to finish the active response:

- an inline A-series producer/fixer stage completed;
- one Q1/Q2/Q3/Q5/Q7 inline role or ordered-inline substep completed;
- a StageResult was validated or canonically recorded;
- a ledger event was appended or workflow state was materialized;
- `controller_cli continue` exposes another legal executable action;
- an already-authorized GitHub Actions workflow was dispatched;
- an exact relevant GitHub Actions run is `queued`, `pending`, `waiting`, `requested`, or `in_progress`;
- a hosted controller run or automated quality run is still non-terminal;
- deterministic CI/validation is still running and its result is required for the next lifecycle decision;
- the lifecycle changes from one same-chat producer/fixer role to another;
- the connected execution API lacks direct `workflow_dispatch` while an authorized repository-write path can trigger the required deterministic workflow through the canonical request-branch adapter.

When advancement depends on an already-authorized GitHub Actions execution, preserve the exact run/attempt/job identity and poll it to a terminal state while the active tool surface permits. On terminal completion, inspect the required evidence, validate/record when applicable, replay state, and continue the lifecycle in the same active turn.

## Deterministic request-branch adapter

`DETERMINISTIC_VALIDATION` has a repository-native dispatch path specifically so lack of a direct GitHub Actions `workflow_dispatch` API is not an orchestration blocker.

When fresh Oracle/NOP evidence is required and direct workflow dispatch is unavailable, but the surface can create a branch and write a repository file, the Orchestrator must use `.terminus/execution/deterministic_request.py` and `.github/workflows/terminus-deterministic-request.yml`:

1. bind the request to the exact task ID, exact current task commit, effective control-plane commit and observed repository head;
2. create the exact `terminus-deterministic-request/<task>/<request-suffix>` branch from the request's `expected_repository_head`;
3. write exactly one request JSON at the generated `.terminus/deterministic-requests/<task>-<request-suffix>.json` path;
4. treat the resulting request commit as a dispatch locator, not as lifecycle PASS evidence;
5. discover and poll the exact `Terminus Deterministic Request` run caused by that request commit;
6. require the workflow to revalidate branch/base identity, unchanged task tree, unchanged effective control-plane commit, Oracle reward `1`, and NOP reward `0`;
7. inspect the uploaded deterministic artifact and construct the stage result only from the exact bound empirical evidence, including non-empty F2P and P2P matrices;
8. canonically validate/record the `DETERMINISTIC_VALIDATION` StageResult, replay state and continue.

Do not redispatch while the exact request-triggered run is queued or running. If the task tree or effective control plane changes before execution, the workflow must fail closed and the controller must generate a fresh request for the new authoritative snapshot.

This adapter is transport only. It does not weaken the deterministic stage predicates, does not infer empirical matrices from stale evidence, and does not permit historical Oracle/NOP evidence from another task commit to satisfy the current stage.

## Legal stop conditions

The Orchestrator may finish the active response only when current evidence establishes at least one genuine stop condition:

1. **Terminal lifecycle state** — `END`, `SUBMISSION_READY`, or another registered terminal outcome.
2. **Manual independent role boundary** — current machine policy requires `MANUAL_INDEPENDENT_QUALITY` or a genuine `FRESH_ROLE_CHAT` that must not execute in the producer-contaminated task context.
3. **Human decision or authorization boundary** — a required user decision, destructive action approval, secret/credential action, new paid/model-backed execution, Harbor/official trial authorization, or another explicitly protected operation is not already authorized.
4. **External gate unable to advance now** — a registered external gate is awaiting evidence that cannot currently be dispatched, inspected, or polled by the available surface.
5. **Circuit breaker or policy blocker** — current durable policy requires a stop rather than another retry/repair.
6. **Required evidence/tool unavailable** — a necessary repository, run, job, log, artifact, validator, or write capability cannot be accessed and no legal alternate evidence path exists. Lack of direct `workflow_dispatch` alone does not qualify when the deterministic request-branch adapter is available.
7. **Active execution surface involuntarily ends** — the chat/tool runtime itself can no longer continue. This is an operational interruption, not a planned lifecycle checkpoint.

A queued/running workflow is never a blocker merely because foreground time has elapsed. There is no autonomous active-turn timeout policy.

## Interrupted active turn

If the active execution surface itself ends before a genuine lifecycle stop condition is reached, preserve enough durable state for deterministic recovery:

- repository HEAD;
- effective control-plane commit;
- current task commit;
- current ledger sequence/event;
- first incomplete stage/gate;
- exact workflow run ID, run number, attempt and numeric job ID when available;
- durable locator path for hosted controller or other indexed runs;
- current status/conclusion;
- next machine action when already known.

Return `PENDING` rather than `BLOCKED` for an ordinary non-terminal run. A later Orchestrator turn must recover from GitHub/ledger evidence and resume the same execution instead of redispatching it.

The Orchestrator must not voluntarily choose interruption as a convenience checkpoint when it still has an executable or pollable legal next action.

## Cost and execution boundary

This policy changes orchestration persistence only. It does **not** introduce a hosted producer backend and does not move normal A-series/producer/fixer work to Cursor or another API.

- normal producer/fixer and routed Q1/Q2/Q3/Q5/Q7 work remains same-task-chat `INLINE_SPECIALIST`/`INLINE_SPECIALIST_SEQUENCE` work when the controller selects those modes;
- Q4/Q6 remain independent and use the configured quality execution mode;
- Q8 remains governed only by `TERMINUS_Q8_MODE`;
- deterministic Oracle/NOP execution through the repository-native request adapter is non-model execution and remains already-authorized whenever the corresponding deterministic gate is already authorized;
- no OpenAI, Anthropic, STB, Cursor, Harbor, official-trial, or other model execution becomes authorized merely because `RUN_TO_BLOCKER` is active;
- provider fallback and verdict shopping remain forbidden.

## Response invariant

Before producing the final user-visible response for an active task run, the Orchestrator must be able to name the exact stop reason.

Recommended response fields:

```text
ACTIVE_TURN_POLICY: RUN_TO_BLOCKER
STOP_REASON: <terminal | manual-independent-boundary | authorization-required | external-gate-wait | circuit-breaker | insufficient-evidence | execution-surface-interrupted>
NEXT_ACTION: <machine next action or none>
NEXT_AGENT_PROMPT: <none unless machine policy genuinely requires a fresh isolated role>
```

If no legal stop reason exists, continue working instead of finishing the response.
