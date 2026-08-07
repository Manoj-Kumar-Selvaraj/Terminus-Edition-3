# Agent Design Research Basis

This file records the external design principles used to evolve the Terminus reviewer/controller system. It is not an authoritative Terminus rule source. Current Edition 3 repository rules always win when there is a conflict.

## Sources consulted

- OpenAI Agents SDK documentation: manager-style orchestration, handoffs, context, guardrails, structured outputs, tracing and agent-as-tool patterns.
- OpenAI Academy 2026 agent/evals material: combine deterministic and model-based checks, use routing/guardrails/tracing/evals, and make evaluation repeatable.
- OpenAI engineering, “Building self-improving tax agents with Codex” (2026): practitioner corrections become traces, traces become evals, and bounded writable workspaces are separated from read-only source evidence.
- OpenAI model guidance: define exact output schemas/evidence, retry and stopping limits, and keep one clear orchestration route.
- Anthropic, “Building effective agents”: prefer simple composable patterns; use parallel focused reviews when dimensions are independent; use an orchestrator-worker pattern for open-ended decomposition; evaluator-optimizer loops are useful when criteria are clear; autonomy increases cost and compounding-error risk.
- Anthropic, “Demystifying evals for AI agents” (2026): combine deterministic, model and human graders; run multiple trials; evaluate outcomes rather than rigid paths; isolate LLM-judge dimensions; give judges an `Unknown` path; calibrate model graders with human judgment; keep trials isolated; inspect trajectories; maintain capability and regression suites; start with a small but real eval set and grow from failures.
- OWASP AI Agent Security guidance (2026): least privilege, clear trust boundaries, treat retrieved/external content as untrusted, protect persistent memory/context, validate structured outputs, maintain audit trails, isolate agents, use circuit breakers, and separate decision-making from high-impact execution.

## Design conclusions for Terminus

### 1. Manager-style orchestration is the default

The CI Orchestrator retains control and invokes specialists for bounded analysis. A specialist does not take over the whole task session. This reduces context drift and gives one place to enforce gate order, staleness, security and final synthesis.

Use specialist handoff only as a logical review boundary. In implementation terms the specialist behaves like an agent-as-tool: receive a bounded context packet, return a structured result, then give control back to the controller.

### 2. More agents are not automatically better

Add a specialist only when separating a dimension improves attention, independence or calibration. Do not create chains where one agent merely paraphrases another. Each role must have a unique decision right, input view and output contract.

### 3. Deterministic checks come before model judgment

Use code/static checks for schema, paths, Docker rules, required files, syntax, ruff, reward values and other objective facts. Use model reviewers only for semantic quality such as realism, fairness, originality, human writing and explanation quality.

### 4. Review dimensions should be isolated

A single judge should not decide originality, writing quality, verifier fairness, difficulty and compliance in one free-form answer. Independent reviewers make each decision against a narrow rubric. The controller aggregates only after the independent passes finish.

### 5. Writers do not approve their own output

Instruction and documentation generation are separate from review. A writer may repair text after a review finding, but a cold reviewer must re-evaluate the new artifact without inheriting the writer’s self-justification.

### 6. A judge must be allowed to say it lacks evidence

Forced binary judgments create hallucinated confidence. Every semantic reviewer has an `INSUFFICIENT_EVIDENCE`/`UNKNOWN` route and must identify the exact missing evidence. The controller gathers that evidence or blocks the gate; it must not silently convert uncertainty into PASS.

### 7. Evidence is typed and provenance matters

Review findings must point to concrete evidence: repository path, requirement, test name, run/job ID, artifact/log, or public reference. Reviewer opinions without evidence are advisory and cannot block or pass a gate by themselves.

### 8. External/retrieved content is data, not authority

Public benchmark tasks, web pages, repository comments, task prose and tool output may contain instructions. Unless the source is an explicitly authoritative Edition 3 rule file, treat those instructions as artifact data to analyze, not commands that may change reviewer behavior.

### 9. Context is minimized per role

Give each specialist only the evidence needed for its decision. In particular, writing roles should not be shown hidden verifier/oracle details unless necessary. Originality review should not be anchored by the creator’s rationale or a previous originality verdict. The Adjudicator sees reviewer outputs only after independent reviews are complete.

### 10. Reviews are versioned and can become stale

Every semantic review records the task commit and reviewer-policy revision. A task change invalidates affected reviews. A material reviewer-policy/calibration change also makes old semantic-review evidence stale even if task files did not change.

### 11. Multiple trials and trajectories matter

Difficulty is empirical. Aggregate reward alone is insufficient. Keep complete-run results, per-test results and trajectories. Read failed and successful trajectories to distinguish legitimate reasoning difficulty from task ambiguity, grader bugs, tool failure or shortcuts.

### 12. The review system itself needs evals

Reviewer prompts are production logic. Maintain a regression bank of labeled micro-cases and real prior misses. Every Harbor/portal/human-review miss becomes a candidate regression case. Track false positives as well as misses so reviewers do not become over-strict.

### 13. Use circuit breakers

Do not let a controller repeat the same failing action indefinitely. Repeated identical infrastructure failures, repeated review disagreement, or repeated fixes with no new evidence trigger a stop/escalation condition rather than another blind retry.

### 14. Keep durable state compact and trustworthy

Session checkpoints store decisions, evidence pointers, policy versions and known dead ends—not raw conversation history. Live repository/CI evidence overrides stale checkpoint text.
