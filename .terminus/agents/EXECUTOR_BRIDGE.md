# Terminus Executor Bridge

Executor-bridge policy version: `1.0`

The executor bridge connects one `READY` StageInvocation to an execution surface. It does not add lifecycle authority and does not replace `ExecutionRecordBuilder`, the execution ledger, or workflow-state resolution.

Canonical flow:

`workflow state -> StageInvocation -> executor handoff -> executor -> StageResult -> ExecutionRecordBuilder -> ledger -> workflow state`

Supported modes are:

- `MANUAL_CHAT`: produces a paste-ready bounded handoff for a fresh authorized chat session. No hosted-model API is required.
- `LOCAL_COMMAND`: passes the handoff JSON on stdin to one argv command and expects one StageResult JSON object on stdout. The process is always started with `shell=False`.

`controller_cli continue` may optionally prepare the handoff in the same response for normal `INVOKE_STAGE` or `RETRY_STAGE` actions. External gates remain dispatch/await-only and never become executor handoffs.

## DO

- execute only the stage and role named in the invocation;
- preserve the exact `invocation_id`;
- read every `mandatory_exact_reads` file exactly at the bound control-plane commit;
- use only declared inputs and authorized evidence;
- return one StageResult JSON object;
- use only legal stage statuses and declared outputs;
- preserve immutable evidence references for acceptance-sensitive claims;
- return the existing task commit when task files were unchanged, or a committed descendant when the authorized stage changed task files;
- pass the returned StageResult to the canonical recorder as a separate operation.

## DO NOT

- choose or write the next lifecycle stage;
- write execution records, ledger events, materialized state, or submission readiness from an executor;
- treat an executor's PASS text as acceptance authority;
- alter invocation authority, evidence visibility, retrieval restrictions, acceptance predicates, or routing;
- add undeclared result fields;
- persist private scratchpad or hidden reasoning fields;
- invent evidence, review, run, commit, or policy identities.

## Controller + manual-chat example

```bash
python .terminus/execution/controller_cli.py continue \
  --task-id <task> \
  --task-commit <task-commit> \
  --control-plane-commit <control-commit> \
  --inputs-json /tmp/stage-inputs.json \
  --prepare-executor MANUAL_CHAT
```

For an ordinary invoke/retry action, the JSON response contains both `invocation` and `executor_handoff`. For `DISPATCH_EXTERNAL_GATE` or `AWAIT_EXTERNAL_GATE`, `executor_handoff` remains `null` and the existing dispatch contract remains authoritative.

## Manual-chat example

```bash
python .terminus/execution/runner_cli.py prepare \
  --invocation /tmp/invocation.json \
  --executor MANUAL_CHAT \
  --text
```

Paste the emitted text into a fresh authorized chat session. Save the returned StageResult JSON and validate it separately through the existing result/controller recorder.

A correct executor response has the form:

```json
{
  "schema_version": "1.0",
  "invocation_id": "inv_<sha256>",
  "output_task_commit": "<git-commit>",
  "status": "<legal-stage-status>",
  "outputs": {},
  "evidence_refs": []
}
```

The exact required outputs and legal statuses come from the handoff's `result_contract`.

## Local-command example

```bash
python .terminus/execution/runner_cli.py run-local \
  --invocation /tmp/invocation.json \
  --timeout 600 \
  -- python local_executor.py
```

The runner sends the handoff JSON on stdin. It reports only a hash and argument count for the command, never claims the StageResult was recorded, and never mutates workflow state.

Default child-process environment inheritance is limited to platform/process basics such as path, home/temp and locale values. Full inheritance is opt-in through `--inherit-env`.

Transport limits:

- positive timeout required;
- stdout maximum: 1 MiB;
- stderr is diagnostic-only and clipped;
- non-zero exit, timeout, malformed JSON, wrong `invocation_id`, or invalid StageResult envelope yields a non-success executor status.

## Acceptance boundary

The executor bridge performs transport checks only. `ExecutionRecordBuilder` remains the authority that independently revalidates invocation integrity, outputs, evidence, acceptance predicates, external-gate constraints and routing before a result can influence durable workflow state.

Harbor and official model evaluation remain external gates controlled by the existing dispatch/await workflow. The executor bridge does not convert them into ordinary local chat stages.
