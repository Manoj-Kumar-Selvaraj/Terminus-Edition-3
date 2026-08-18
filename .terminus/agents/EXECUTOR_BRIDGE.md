# Terminus Executor Bridge

Executor-bridge policy version: `1.3`

The executor bridge connects canonically authorized Terminus work to execution surfaces without transferring lifecycle authority. It does not replace `ExecutionRecordBuilder`, the execution ledger, workflow-state resolution, or packet-bound specialist review provenance.

Canonical stage flow:

`workflow state -> StageInvocation -> canonical pre-execution authorization -> executor handoff -> executor -> StageResult -> ExecutionRecordBuilder -> ledger -> workflow state`

Canonical quality-review flow:

`schema-v3 review packet -> exact task/control-plane evidence projection -> exactly one Q backend -> persistent per-task budget claim -> persisted review JSON -> deterministic validation -> optional review publication`

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

`.terminus/execution/quality_dispatch_cli.py` executes one existing schema-v3 Q packet through one repository-selected backend. The older low-level `.terminus/execution/quality_executor_cli.py` remains the direct Cursor/OpenAI/Anthropic transport, while normal CI selection goes through the flag-driven dispatcher.

Quality execution invariants:

- exactly one repository Q backend flag is active for all Q executions;
- Cursor is always a fresh `cursor-agent -p --model auto` session and never resumes a prior Q session;
- direct OpenAI uses `OPENAI_API_KEY` plus `Q_OPENAI_MODEL`;
- direct Claude uses `ANTHROPIC_API_KEY` plus `Q_CLAUDE_MODEL`;
- STB AI mode uses the already-issued `STB_AI_API_KEY` plus `Q_STB_AI_MODEL` against the Portkey Open Responses gateway;
- there is no automatic provider fallback, second Q review, or retry-after-REVISE verdict shopping;
- there is no Q credential login, key generation, token rotation, config restoration, or `stb keys refresh` path;
- a missing or invalid selected credential fails closed;
- credentials are never inserted into packets, prompts, review results, budget receipts, or execution summaries;
- a git-history-free temporary projection materializes role-appropriate task evidence at `task_commit` and policy/schema files at `control_plane_commit`;
- prior review conclusions, `.git`, reference solution, sibling repositories and project model-rule files are not projected;
- Q4 receives instruction/tests plus only environment interfaces needed to interpret graded behavior and its classification-only test map when present;
- Q6 receives task metadata, solver-visible environment, and packet-authorized task-scoped production/complexity evidence;
- Q8 receives instruction/task metadata/environment and no hidden tests;
- the complete schema-v3 review JSON at `review_output_path` is canonical; Cursor stream output is diagnostic only;
- raw Cursor thinking events are never persisted by the production runner;
- after execution the host independently validates JSON Schema, packet/result provenance bindings, Q4 finding classification/PASS exhaustiveness, and absence of mutations outside the exact review artifact;
- only a deterministically validated review may be copied into the checkout or uploaded as CI evidence.

### Global Q backend flags

Repository variables control the backend for all Q executions:

- `Q_CURSOR_ENABLED=yes` -> `CURSOR_API_KEY`;
- `Q_OPENAI_ENABLED=yes` -> `OPENAI_API_KEY` and `Q_OPENAI_MODEL`;
- `Q_CLAUDE_ENABLED=yes` -> `ANTHROPIC_API_KEY` and `Q_CLAUDE_MODEL`;
- `Q_STB_AI_ENABLED=yes` -> existing `STB_AI_API_KEY` and `Q_STB_AI_MODEL`.

Exactly one flag must resolve to `yes`. If none of these repository variables has been configured yet, CI defaults to Cursor for backward-safe rollout. Once any flag is configured, blank flags mean `no`. `model_override` is available only as an explicit workflow invocation override for non-Cursor backends.

The optional `STB_AI_BASE_URL` repository variable may point at an approved HTTPS gateway; blank/unset uses `https://api.portkey.ai/v1`.

### Per-task Q execution budgets

Before a model-backed Q call, CI claims an immutable receipt on the dedicated `terminus-quality-budget` state branch. Repository-wide quality concurrency serializes claims across all task branches, so a new branch, remediation commit, or fresh runner cannot reset the per-task count.

- Q4 / Spec-Test Contract Reviewer: maximum **3** executions per task.
- Q6 / Production Logic Auditor: maximum **2** executions per task.
- Every other registered Q role: maximum **1** execution per task.

Preflight, SDK installation, and selected-secret presence checks occur before the claim. Once the claim is durably pushed, that model-backed attempt consumes the slot even if the downstream provider call fails. Re-entering the same GitHub run attempt is idempotent; a new GitHub run attempt consumes a new slot.

Budget receipts contain only execution identity/provenance and backend name—never credentials or model reasoning.

### Examples

Cursor is normally selected through repository variables. The low-level direct transport remains available for debugging:

```bash
CURSOR_API_KEY=... python .terminus/execution/quality_executor_cli.py \
  --packet .terminus/reviews/<task>/<sha8>/<review>.packet.json \
  --executor cursor \
  --review-output /tmp/review.json \
  --output /tmp/execution.json
```

Direct OpenAI and Claude remain optional placeholders for independently sourced API credentials. STB AI mode intentionally reuses the already-issued STB/Portkey AI credential and never refreshes it.

The API backends expose only bounded read/list/grep tools plus one exact `write_review` sink. Direct OpenAI requests may use their provider-native prompt-cache controls. STB AI uses Portkey's Open Responses surface without issuing credential refreshes or overriding the existing gateway credential policy. Cache hits are an efficiency optimization only and never affect review identity or acceptance.

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
