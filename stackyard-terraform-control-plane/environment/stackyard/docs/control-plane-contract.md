# Stackyard Control Plane Contract

Stackyard is a local Terraform Cloud replacement. Absolute product root: `/app/stackyard`.

## Environment

| Variable | Meaning | Default |
|---|---|---|
| `STACKYARD_DB` | SQLite database file path | `/app/stackyard/data/stackyard.db` |
| `STACKYARD_ADDR` | HTTP listen address | `127.0.0.1:8080` |
| `STACKYARD_DATA` | Workspace working directories root | `/app/stackyard/data/workspaces` |
| `TERRAFORM_BIN` | Terraform binary or shim | `/app/stackyard/bin/terraform-shim` |
| `STACKYARD_TOKEN` | Bearer token required on mutating API calls when set; empty disables auth | empty |
| `STACKYARD_SYNC` | When `1`, run execution is synchronous inside the create handler (useful for tests) | empty |

On startup the server must:

1. Create parent directories for `STACKYARD_DB` and `STACKYARD_DATA`.
2. Apply `/app/stackyard/db/schema.sql` if tables are missing.
3. Ensure organization `acme` exists (name exact, slug `acme`).
4. Serve static UI files from `/app/stackyard/ui` at `/`.
5. Expose JSON API under `/api/v1/...`.

## Authentication

When `STACKYARD_TOKEN` is non-empty, requests other than `GET /`, static assets under `/css/` and `/js/`, and `GET /api/v1/health` must include `Authorization: Bearer <token>`. Missing or invalid token returns HTTP 401 with `{"error":"unauthorized"}`.

## Organizations

- `GET /api/v1/orgs` → `{"orgs":[Org,...]}`
- `POST /api/v1/orgs` body `{"name":string,"slug":string}` → Org (201)
- `GET /api/v1/orgs/{org_id}` → Org

Org JSON:

```json
{"id":"org_...","name":"acme","slug":"acme","created_at":"RFC3339"}
```

IDs are opaque strings prefixed `org_`, `ws_`, `var_`, `run_`, `lock_`, `aud_`.

## Workspaces

Scoped under an org:

- `GET /api/v1/orgs/{org_id}/workspaces` → `{"workspaces":[Workspace,...]}`
- `POST /api/v1/orgs/{org_id}/workspaces` body `{"name":string,"working_directory":string}` → Workspace (201)
- `GET /api/v1/workspaces/{workspace_id}` → Workspace
- `DELETE /api/v1/workspaces/{workspace_id}` → 204

Workspace JSON:

```json
{"id":"ws_...","org_id":"org_...","name":"prod","working_directory":"infra","locked":false,"lock_id":null,"created_at":"RFC3339"}
```

`working_directory` is relative to `STACKYARD_DATA/{workspace_id}/`. The server creates that tree on workspace create.

### Delete guards

`DELETE` must fail with HTTP 409 and `{"error":"..."}` when:

- a non-terminal run exists for the workspace, or
- an exclusive state lock is held (`locked=true`).

## Variables

- `GET /api/v1/workspaces/{workspace_id}/vars` → `{"vars":[Var,...]}`
- `POST /api/v1/workspaces/{workspace_id}/vars` body `{"key":string,"value":string,"sensitive":bool,"category":"terraform"|"env"}` → Var (201)
- `GET /api/v1/vars/{var_id}` → Var
- `DELETE /api/v1/vars/{var_id}` → 204

Var JSON:

```json
{"id":"var_...","workspace_id":"ws_...","key":"FOO","value":"...","sensitive":false,"category":"terraform","created_at":"RFC3339"}
```

### Sensitive redaction

If `sensitive` is true, every API response (including create) must set `value` to JSON `null`. The plaintext value remains stored for runner injection only.

## Runs

- `GET /api/v1/workspaces/{workspace_id}/runs` → `{"runs":[Run,...]}` newest first
- `POST /api/v1/workspaces/{workspace_id}/runs` body `{"command":"init"|"validate"|"fmt"|"plan"|"apply"|"destroy","message":string}` → Run (201)
- `GET /api/v1/runs/{run_id}` → Run
- `POST /api/v1/runs/{run_id}/discard` → Run
- `POST /api/v1/runs/{run_id}/cancel` → Run

Run JSON:

```json
{
  "id":"run_...",
  "workspace_id":"ws_...",
  "command":"plan",
  "status":"queued",
  "message":"",
  "plan_output":"",
  "apply_output":"",
  "error":"",
  "created_at":"RFC3339",
  "updated_at":"RFC3339"
}
```

### Lifecycle statuses

Allowed values: `queued`, `running`, `planned`, `applied`, `errored`, `discarded`, `canceled`.

Terminal statuses: `applied`, `errored`, `discarded`, `canceled`.
Non-terminal: `queued`, `running`, `planned`.

### Concurrency invariant

At most **one non-terminal run** may exist per workspace. Creating another while a non-terminal run exists returns HTTP 409 `{"error":"workspace has active run"}`.

### Execution

Creating a run enqueues work. With `STACKYARD_SYNC=1` the runner executes before the create response returns; otherwise it may run asynchronously. Execution steps:

1. Transition `queued` → `running` and write audit `run.status` with detail `queued->running`.
2. Invoke `TERRAFORM_BIN` with argv derived from `command` inside the workspace directory.
3. On success:
   - `init` / `validate` / `fmt` / `plan` → `planned` (stdout in `plan_output`).
   - `apply` / `destroy` → `applied` (stdout in `apply_output`).
4. On failure → `errored` with `error` set.

Create also writes audit `run.created` with detail equal to the command name.

### Command argv mapping

Working directory: `STACKYARD_DATA/{workspace_id}/{working_directory}` (create if missing).

| command | argv after binary |
|---|---|
| init | `init -input=false` |
| validate | `validate` |
| fmt | `fmt -check` |
| plan | `plan -input=false -no-color -out=tfplan` |
| apply | `apply -input=false -auto-approve -no-color tfplan` when `tfplan` exists; otherwise `apply -input=false -auto-approve -no-color` |
| destroy | `apply -destroy -input=false -auto-approve -no-color` |

Destroy **must** use `apply -destroy`, never a bare `destroy` subcommand.

### Lock requirement for apply/destroy

Posting `apply` or `destroy` while the workspace is unlocked returns HTTP 409 `{"error":"lock required"}` and must not create a run.

### TF_VAR / env injection

When executing terraform, the runner environment must include:

- For each workspace variable with `category=terraform`: `TF_VAR_<key>=<value>` (including sensitive values).
- For each with `category=env`: `<key>=<value>` directly.
- Inherit process environment otherwise.

### Discard and cancel

- `discard` allowed only from `planned` → `discarded`.
- `cancel` allowed only from `queued` or `running` → `canceled`.
- Any other transition returns HTTP 409 `{"error":"invalid transition"}`.

## Locks

- `POST /api/v1/workspaces/{workspace_id}/lock` body `{"holder":string,"reason":string}` → Lock (201)
- `POST /api/v1/workspaces/{workspace_id}/unlock` body `{"holder":string}` → 204
- `GET /api/v1/workspaces/{workspace_id}/lock` → Lock or 404

Lock JSON:

```json
{"id":"lock_...","workspace_id":"ws_...","holder":"alice","reason":"apply","created_at":"RFC3339"}
```

Rules:

- Only one lock per workspace. Locking when already locked returns 409 `{"error":"already locked"}`.
- Unlock succeeds only when `holder` matches the current lock holder; otherwise 403 `{"error":"not lock holder"}`.
- Successful lock/unlock must write audit entries `lock.acquire` / `lock.release` with detail equal to the holder.

## Audit

- `GET /api/v1/workspaces/{workspace_id}/audit` → `{"events":[AuditEvent,...]}` newest first

```json
{"id":"aud_...","workspace_id":"ws_...","action":"run.status","detail":"queued->running","actor":"system","created_at":"RFC3339"}
```

Required audit actions:

| Event | action | detail |
|---|---|---|
| Run created | `run.created` | command name |
| Run status change | `run.status` | `{from}->{to}` |
| Lock acquired | `lock.acquire` | holder |
| Lock released | `lock.release` | holder |

## UI requirements

`/app/stackyard/ui/index.html` plus `/css/app.css` and `/js/app.js` must provide operator forms that call the JSON API for listing orgs, creating workspaces, creating variables (sensitive checkbox), locking/unlocking with holder, creating runs with field name `command`, discarding/canceling runs, and displaying API `error` messages.

UI must not invent alternate field names such as `cmd` instead of `command`.

## Health

`GET /api/v1/health` returns `{"status":"ok"}`.

## Error shape

All 4xx/5xx JSON errors use `{"error":string}` with the stable short messages specified above when applicable.
