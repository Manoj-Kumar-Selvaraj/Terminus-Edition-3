# Terminus Executor Bridge

Executor-bridge policy version: `1.1`

The executor bridge connects one canonically authorized `READY` StageInvocation to an execution surface. It does not add lifecycle authority and does not replace `ExecutionRecordBuilder`, the execution ledger, or workflow-state resolution.

Canonical flow:

`workflow state -> StageInvocation -> canonical pre-execution authorization -> executor handoff -> executor -> StageResult -> ExecutionRecordBuilder -> ledger -> workflow state`

Supported modes are:

- `MANUAL_CHAT`: paste-ready bounded handoff for a fresh authorized chat session. No hosted-model API is required.
- `LOCAL_COMMAND`: read-only Linux/WSL executor using a projected evidence-aware workspace inside `bubblewrap`. There is no unsafe host-process fallback.

`controller_cli continue` may optionally prepare a handoff for normal `INVOKE_STAGE` or `RETRY_STAGE` actions. External gates remain dispatch/await-only and never become executor handoffs.

## Pre-execution authority

Before either executor receives an invocation, the bridge reuses the canonical invocation validation owned by the execution-record layer. Hash self-consistency alone is insufficient. The bridge revalidates stage ownership, task/control commits, loaded control-plane snapshot, declared inputs, evidence classes, retrieval mode/context, exact reads, acceptance predicates and routing.

A modified invocation that is merely rehashed must be rejected before any executor sees it.

## DO

- execute only the stage and role named in the invocation;
- preserve the exact `handoff_id` and `invocation_id`;
- read every `mandatory_exact_reads` file at the bound control-plane commit;
- use only declared inputs and authorized evidence;
- return one StageResult JSON object;
- use only legal stage statuses and declared outputs;
- preserve immutable evidence references for acceptance-sensitive claims;
- for `MANUAL_CHAT`, return the existing task commit when unchanged or a committed descendant when the authorized role changed task files;
- pass the returned StageResult to the canonical recorder as a separate operation.

## DO NOT

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

`LOCAL_COMMAND` is deliberately narrower than `MANUAL_CHAT` in version 1.1:

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

## Transport limits

- positive timeout required;
- stdout hard limit: 1 MiB while the process is running;
- stderr hard diagnostic limit: 256 KiB while the process is running, then clipped to 4,000 characters in the response;
- the process group is killed on timeout or output-limit violation;
- malformed JSON, schema-invalid StageResult, wrong `handoff_id`, wrong `invocation_id`, task-commit mutation, non-zero exit, timeout or sandbox unavailability yields a non-success executor status;
- `shell=False` is mandatory.

Default environment propagation is reduced to PATH and locale values. Full environment inheritance remains explicit opt-in and still occurs inside the filesystem/network sandbox.

## Runtime schemas

Generated executor handoffs are validated at runtime against `executor_handoff.schema.json`. Returned StageResult objects are validated at runtime against `stage_result.schema.json` before transport-level acceptance. Semantic stage status/output/evidence acceptance remains exclusively with `ExecutionRecordBuilder`.

## Acceptance boundary

The executor bridge never advances workflow state. `ExecutionRecordBuilder` independently revalidates invocation integrity, outputs, evidence, acceptance predicates, external-gate constraints and routing before any result can influence the durable ledger. Harbor and official model evaluation remain external dispatch/await gates and are never converted into normal executor handoffs.
