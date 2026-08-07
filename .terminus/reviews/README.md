# Terminus Structured Review Evidence

Store durable semantic reviewer outputs here, outside every task directory.

Recommended layout:

```text
.terminus/reviews/
  <task-name>/
    <task-commit-short>/
      task-architect.json
      verifier-engineer.json
      originality.json
      difficulty-design.json
      compliance.json
      instruction.json
      documentation.json
      human-quality.json
      adjudication-<id>.json
      pre-llmaj-aggregate.json
```

## Rules

- Reports must conform to `.terminus/agents/schemas/review_result.schema.json` where applicable.
- Context packets may be preserved separately when useful and must conform to `context_packet.schema.json`.
- Never store secrets, raw private credentials or unnecessary full chat transcripts.
- Each report must identify the task commit and reviewer policy version it evaluated.
- A report is immutable evidence. If a reviewer reruns, create/replace the current report only when the previous result remains recoverable from Git history; do not silently edit a historical verdict without a commit trail.
- Writers/producers do not create PASS review reports for their own output.
- The task session checkpoint should point to current review paths/IDs rather than restating long reviewer reasoning.
- Review files stay outside the task directory and must never be packaged into a Terminus submission ZIP.

## Aggregate report

`pre-llmaj-aggregate.json` records only frozen independent verdicts plus adjudication references. It does not replace individual evidence reports.

Suggested fields:

```json
{
  "task": "<task>",
  "task_commit": "<sha>",
  "panel_policy_version": "2.0",
  "verdict": "PASS",
  "review_reports": {
    "task_architect": "...",
    "verifier": "...",
    "originality": "...",
    "difficulty": "...",
    "compliance": "...",
    "instruction": "...",
    "documentation": "..."
  },
  "adjudications": [],
  "open_findings": []
}
```

The Orchestrator must verify each referenced report still applies to the same task/input/policy version before using the aggregate.
