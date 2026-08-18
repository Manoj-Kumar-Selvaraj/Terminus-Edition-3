# Terminus Executor Bridge

Executor-bridge policy version: `1.2`

The executor bridge connects canonically authorized Terminus work to execution surfaces without transferring lifecycle authority. It does not replace `ExecutionRecordBuilder`, the execution ledger, workflow-state resolution, or packet-bound specialist review provenance.

Canonical stage flow:

`workflow state -> StageInvocation -> canonical pre-execution authorization -> executor handoff -> executor -> StageResult -> ExecutionRecordBuilder -> ledger -> workflow state`

Canonical quality-review flow:

`schema-v3 review packet -> exact task/control-plane evidence projection -> exactly one Q executor -> persisted review JSON -> deterministic validation -> optional review publication`

## Stage executor modes

- `MANUAL_CHAT`: paste-ready bounded handoff for a fresh authorized chat session. No hosted-model API is required.
- `LOCAL_COMMAND`: read-only Linux/WSL executor using a projected evidence-aware workspace inside `bubblewrap`. There is no unsafe host-process fallback.

`controller_cli continue` may optionally prepare a handoff for normal `INVOKE_STAGE` or `RETRY_STAGE` actions. External gates remain dispatch/await-only and never become executor handoffs.

### Pre-execution authority

Before either stage executor receives an invocation, the bridge reuses the canonical invocation validation owned by the execution-record layer. Hash self-consistency alone is insufficient. The bridge revalidates stage ownership, task/control commits, loaded control-plane snapshot, declared inputs, evidence classes, retrieval mode/context, exact reads, acceptance predicates and routing.

A modified invocation that is merely rehashed must be rejected before any executor sees it.

### Stage executor DO

- execute only the stage and role named in the invocation;
- preserve the exact `handoff_id` and `invocation_id`;
- read every `mandatory_exact_reads` file at the bound control-plane commit;
- use only declared inputs and authorized evidence;
- return one StageResult JSON object;
- use only legal stage statuses and declared outputs;
- preserve immutable evidence references for acceptance-sensitive claims;
- for `MANUAL_CHAT`, return the existing task commit when unchanged or a committed descendant when the authorized role changed task files;
- pass the returned StageResult to the canonical recorder as a separate operation.

### Stage executor DO NOT

- choose or write the next lifecycle stage;
- write execution records, ledger events, materialized state, or submission readiness from an executor;
- treat executor PASS text as acceptance authority;
- alter invocation authority, evidence visibility, retrieval restrictions, acceptance predicates, or routing;
- add undeclared result fields;
- persist private scratchpad or hidden reasoning fields;
- invent evidence, review, run, commit, policy, handoff, or invocation identities.

## MANUAL_CHAT

```bash
python .terminus/execution/runner_cli.py prepare \
  --invocation /tmp/invocation.json \
  --executor MANUAL_CHAT \
  --text
```

The text transport starts with the exact `Handoff ID`. The executor must echo that ID and the invocation ID in its StageResult. The handoff identity binds the generated instruction body.

Executor-produced StageResult shape:

```json
{
  "schema_version": "1.0",
  "handoff_id": "handoff_<sha256>",
  "invocation_id": "inv_<sha256>",
  "output_task_commit": "<git-commit>",
  "status": "<legal-stage-status>",
  "outputs": {},
  "evidence_refs": []
}
```

`handoff_id` remains optional for non-executor legacy/direct result paths, but executor transport requires it exactly. When present it is carried into the immutable execution record as attempt provenance.

## LOCAL_COMMAND

`LOCAL_COMMAND` remains deliberately narrower than `MANUAL_CHAT`:

- only non-mutating role classes may use it;
- `PRODUCER` and `FIXER` stages are rejected and must use `MANUAL_CHAT` until a controlled change-import mechanism exists;
- Linux `bubblewrap` (`bwrap`) is mandatory; native Windows must use WSL/Linux or `MANUAL_CHAT`;
- no fallback runs the untrusted process directly on the host;
- the authoritative repository and user home are masked inside the sandbox;
- the child receives a projected workspace containing mandatory exact reads and repository evidence allowed by the invocation;
- the projected workspace is mounted read-only;
- network and other namespaces are unshared;
- the child must return the bound input task commit unchanged.

Example:

```bash
python .terminus/execution/runner_cli.py run-local \
  --invocation /tmp/invocation.json \
  --timeout 600 \
  -- python -c '<executor program>'
```

Command arguments may not point into the authoritative repository. The runner reports only a SHA-256 and argument count for the original command.

## Packet-bound quality executor

`.terminus/execution/quality_executor_cli.py` executes one existing schema-v3 Q4/Q6/Q8 packet. It is separate from the generic StageInvocation transport because the review packet already carries the specialist role, task commit, control-plane commit, evidence boundary, schema and exact review output path.

Quality execution invariants:

- Q4 and Q6 use exactly one backend per invocation: `cursor` **or** `api`;
- Q8/model-perspective difficulty simulation is API-key-only and rejects Cursor;
- Cursor is always a fresh `cursor-agent -p --model auto` session and never resumes a prior Q session;
- API mode selects exactly one provider (`openai` or `anthropic`) and one explicit model;
- there is no automatic provider fallback, second Q review, or retry-after-REVISE verdict shopping;
- credentials are read only from `CURSOR_API_KEY`, `OPENAI_API_KEY`, or `ANTHROPIC_API_KEY` environment variables and are never inserted into packets, prompts, results or execution summaries;
- a git-history-free temporary projection materializes role-appropriate task evidence at `task_commit` and policy/schema files at `control_plane_commit`;
- prior review conclusions, `.git`, reference solution, sibling repositories and project model-rule files are not projected;
- Q4 receives instruction/tests/environment plus its classification-only test map when present; Q6 receives only task metadata and solver-visible environment; Q8 receives instruction/task metadata/environment and no hidden tests;
- the minimal executor prompt points to the packet and asks for efficiency without trading accuracy or completeness;
- the complete schema-v3 review JSON at `review_output_path` is canonical; Cursor stream output is diagnostic only;
- raw Cursor thinking events are never persisted by the production runner;
- after execution the host independently validates JSON Schema, packet/result provenance bindings, Q4 finding classification/PASS exhaustiveness, and absence of mutations outside the exact review artifact;
- only a deterministically validated review may be copied into the checkout or uploaded as CI evidence.

Cursor example:

```bash
CURSOR_API_KEY=... python .terminus/execution/quality_executor_cli.py \
  --packet .terminus/reviews/<task>/<sha8>/<review>.packet.json \
  --executor cursor \
  --review-output /tmp/review.json \
  --output /tmp/execution.json
```

OpenAI example:

```bash
OPENAI_API_KEY=... python .terminus/execution/quality_executor_cli.py \
  --packet .terminus/reviews/<task>/<sha8>/<review>.packet.json \
  --executor api \
  --provider openai \
  --model <admin-selected-model> \
  --review-output /tmp/review.json
```

Anthropic uses the same API path with `ANTHROPIC_API_KEY`, `--provider anthropic`, and an explicit admin-selected model.

The API backends expose only bounded read/list/grep tools plus one exact `write_review` sink. OpenAI requests use a stable role-contract-derived prompt-cache key; Anthropic marks the stable system prefix cacheable. Cache hits are an efficiency optimization only and never affect review identity or acceptance.

## Transport limits

For the generic `LOCAL_COMMAND` executor:

- positive timeout required;
- stdout hard limit: 1 MiB while the process is running;
- stderr hard diagnostic limit: 256 KiB while the process is running, then clipped to 4,000 characters in the response;
- the process group is killed on timeout or output-limit violation;
- malformed JSON, schema-invalid StageResult, wrong `handoff_id`, wrong `invocation_id`, task-commit mutation, non-zero exit, timeout or sandbox unavailability yields a non-success executor status;
- `shell=False` is mandatory.

Default generic executor environment propagation is reduced to PATH and locale values. Full environment inheritance remains explicit opt-in and still occurs inside the filesystem/network sandbox.

## Runtime schemas and acceptance

Generated stage executor handoffs are validated at runtime against `executor_handoff.schema.json`. Returned StageResult objects are validated at runtime against `stage_result.schema.json` before transport-level acceptance. Semantic stage status/output/evidence acceptance remains exclusively with `ExecutionRecordBuilder`.

Packet-bound quality reviews are independently validated against the packet-selected `review_result.schema.json` plus packet provenance and role-specific deterministic invariants. A model's own claim that its output is valid is never acceptance evidence.

Neither executor surface advances workflow state by itself. Harbor LLMaJ and official difficulty remain external model-backed gates and are not converted into normal executor handoffs.
