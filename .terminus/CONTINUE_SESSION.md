# Continue a Terminus Session

Use this when a Terminus task moves to a new ChatGPT conversation or controller instance. The repository and GitHub Actions are the durable source of operational truth; chat history is disposable working context.

## Minimal user prompt

`Continue Terminus session for <task-name>.`

## Required controller bootstrap

Before proposing or applying a task change, the controller must:

1. Read `.terminus/AGENT_SYSTEM.md`.
2. Read `.terminus/agents/PROMPTS.md`.
3. Read `.terminus/GOLDEN_TASKS.md` only as calibration/reference material.
4. Read `.terminus/sessions/<task-name>.md`.
5. Read the current task files from the repository.
6. Inspect the current branch/PR and latest GitHub Actions run for that task.
7. Inspect the failed job logs and available Harbor/validation/difficulty artifacts when a gate is not green.
8. Reconcile the checkpoint with live evidence. GitHub/CI evidence wins over stale session text.
9. Resume from the first incomplete or failed gate.
10. Update the session checkpoint after every meaningful state transition, root-cause classification, task fix, validation result, difficulty result, or final audit decision.

## Controller continuity rules

- Never ask the user to repeat information already available in the repository, session checkpoint, PR, workflow logs, or artifacts.
- Never rely on a prior chat's hidden context as the only source for a decision that affects the task.
- Never store API keys, passwords, Portkey credentials, Snorkel keys, GitHub tokens, or other secrets in the session checkpoint.
- Store secret *names* and non-sensitive project IDs only when useful for continuity.
- Keep attempt history compact. Preserve decisions that prevent repeated dead ends; remove noisy/transient details.
- If the task contract, verifier, instruction, environment, or solution semantics change after difficulty measurement, mark difficulty `STALE` and rerun normal validation before new difficulty runs.
- A task cannot become `SUBMISSION_READY` until every gate in `.terminus/AGENT_SYSTEM.md` is satisfied.

## Active-session behavior

During a live task session, after the controller pushes a change and triggers CI, it should check the active workflow approximately every 120 seconds until the run reaches a terminal state. When a run fails, it should immediately fetch the failed step/job logs and relevant artifacts, route the evidence to the appropriate specialist role, apply the smallest justified fix, update the session checkpoint, push, and continue.

This is an interactive controller loop, not a scheduled/background automation. If the chat stops, GitHub Actions and `.terminus/sessions/<task>.md` preserve the state for the next conversation.
