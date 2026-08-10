# Invoking a Terminus Specialist

Invocation policy version: `1.1`

`PROTOCOL.md` defines the evidence contract. This file defines the operating sequence for one specialist review.

## Start the Orchestrator

The CI Orchestrator is not a semantic reviewer and does not receive a review packet. Start it with the project agent `.cursor/agents/terminus-ci-orchestrator.md` or use `.terminus/agents/CI_ORCHESTRATOR.md` as the first prompt in a normal repository-connected chat. Supply exactly one task name. It reconciles Git, session and CI evidence, then returns a separate one-role handoff for the first non-current gate.

Do not reuse the Orchestrator chat as the routed producer, fixer or reviewer chat. Results return to the Orchestrator for provenance validation and durable session updates.

## Generate, do not hand-write

After the task and governing control-plane policy are committed:

```bash
python3 .terminus/new_review_packet.py <task> <role> --change "what changed"
```

Available ordinary role keys:

`task-architect`, `verifier-engineer`, `originality`, `difficulty-design`, `compliance`, `instruction`, `documentation`, `human-quality`, `comprehensive-checklist`, `trajectory`, `adjudication`.

Additional quality-review role keys:

- `spec-test-contract` -> Q4 Spec-Test Contract Reviewer;
- `production-logic` -> Q6 Production Logic Auditor;
- `difficulty-sim-gpt` -> Q8 GPT-perspective diagnostic solve;
- `difficulty-sim-claude` -> Q8 Claude-perspective diagnostic solve.

Q1/Q2/Q3/Q5/Q7 are producer/fixer agents and are routed directly by the Orchestrator; they do not generate semantic PASS evidence for their own work.

The generator refuses a dirty task or dirty governing reviewer policy, derives the task/control-plane commits, computes the role-contract hash, assigns a unique review ID, records `evidence_excluded`, validates schema v3, and writes an immutable `*.packet.json` beside the future result path.

## One role per chat

Open a new chat for the role. Use the packet as the first review context. Do not reuse a producer/fixer chat or a chat that already performed another reviewer role when cold independence matters.

For Q8, `difficulty-sim-gpt` and `difficulty-sim-claude` are separate cold executions. Do not show either perspective the other result before both freeze.

Invocation text:

```text
You are the ROLE named in this Terminus context packet.

Read the packet's authoritative_rules. For ordinary roles, read the matching role section
in .terminus/agents/PROMPTS.md. For Q4/Q6/Q8 quality roles, read the matching section in
.terminus/agents/QUALITY_AGENT_PROMPTS.md. Also read
.terminus/agents/PRODUCTION_AUTHENTICITY.md where applicable. Answer only the packet's question.

For an operational/stateful task, independently check the production evidence surface,
starting-state scale/variance, major business-module decision depth, and whether incident
claims are supported by solver-visible artifacts. Treat micro-program/module inflation,
toy production data, unsupported incident backstory and benchmark/fixture framing as
material authenticity defects; raw LOC/resource/test counts do not waive them.

Read only evidence_allowed. Do not intentionally open evidence_excluded. The packet's
isolation_mode describes whether that boundary is procedural or materialized. If the
decision genuinely requires excluded evidence, return INSUFFICIENT_EVIDENCE instead of
opening it silently.

Return JSON matching .terminus/agents/schemas/review_result.schema.json v3. Copy all
provenance fields exactly from the packet: review_id, task, task_commit,
control_plane_commit, protocol_policy_version, prompt_policy_version,
role_policy_version, role_contract_hash. Set context_packet to this packet's repository
path. Put the role-specific prompt output inside role_output; do not add undeclared
top-level fields.

Use evidence refs for every material finding. LOW confidence or insufficient evidence
must not be converted to PASS.
```

Write the JSON to the exact `review_output_path` in the packet.

Then run:

```bash
python3 .terminus/validate_review_freshness.py --task <task>
```

## Quality-role boundaries

- Q4 may read verifier behavior because its decision right is bidirectional spec/test alignment, but it must not use test names/fixtures as solver-facing wording.
- Q6 evaluates solver-visible production logic independently of Complexity Governor and raw LOC reports.
- Q8 gets solver-visible task evidence only before solve. `solution/`, hidden tests, private defect/test maps, prior trajectories, desired tier and the other perspective result remain excluded.
- Q8 output must explicitly state that it is simulated diagnostic evidence, not actual GPT-5.5/Claude Opus 4.8 trial evidence.

## Exclusion boundary

The generator is the single source for per-role allowed/excluded evidence. Important examples:

- Instruction Reviewer excludes `solution/`, hidden test bodies, private defect IDs, writer rationale and its prior verdict.
- Comprehensive Reviewer excludes all specialist verdicts until its criterion walk is frozen.
- Originality excludes the creator's uniqueness claim and prior originality verdict.
- Difficulty excludes the desired tier.
- Adjudicator may see frozen disputed reviews only after those reviews are complete.
- Q4 excludes Q1/Q2/Q3 conclusions until its own matrix is frozen.
- Q8 perspectives exclude one another until both runs freeze.

Current Cursor review isolation is `PROCEDURAL`, not an ACL. This process reduces anchoring; it does not physically remove repository access.

## After the result

1. The Orchestrator validates packet/result binding and role-contract freshness.
2. Record the exact result path/review ID in the session; do not copy reviewer prose into the checkpoint.
3. REVISE/REQUEST_CHANGES findings go to the responsible producer in a separate chat.
4. Any task or role-contract change that invalidates the result marks it `STALE`.
5. A rerun gets a new review ID and new packet; never overwrite prior evidence.

## Ordering

For the quality-agent workflow:

`deterministic freeze -> Q4 Spec-Test Contract Reviewer + Q6 Production Logic Auditor -> QUALITY_INTERLOCK_PASS -> ordinary Pre-LLMaJ specialists/comprehensive/aggregate -> Q8 GPT and Claude diagnostic perspectives -> Harbor/model gates`.

Q8 is diagnostic. It cannot replace Harbor LLMaJ or the official GPT x5 + Claude x5 difficulty trials.
