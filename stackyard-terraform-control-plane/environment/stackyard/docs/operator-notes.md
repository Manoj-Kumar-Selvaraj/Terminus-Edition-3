# Stackyard operator notes

These notes are ambient product documentation for engineers working on the
control plane. They intentionally do not enumerate defects. Behavior that must
hold in production is defined by `docs/control-plane-contract.md`.

## Layout

```
/app/stackyard
  cmd/stackyard          HTTP process entrypoint
  internal/api           JSON routes + static UI hosting
  internal/store         SQLite persistence
  internal/runner        terraform process execution
  internal/policy        concurrency, locks, redaction, argv/env mapping
  internal/audit         transition provenance writer
  internal/model         shared types and status vocabulary
  internal/config        environment loading
  db/schema.sql          relational schema
  ui/                    operator console
  bin/terraform-shim     deterministic terraform stand-in
  bin/stackyard          built server binary
  data/                  runtime DB + workspace trees (created at boot)
```

## Local boot

```bash
cd /app/stackyard
go build -o bin/stackyard ./cmd/stackyard
export STACKYARD_SYNC=1
export TERRAFORM_BIN=/app/stackyard/bin/terraform-shim
./bin/stackyard
```

Open `http://127.0.0.1:8080/`. The API lives under `/api/v1`.

## Workspace directories

Each workspace receives `STACKYARD_DATA/{workspace_id}/{working_directory}`.
Runs execute with that directory as the process cwd. The shim writes
`terraform-shim.log` and `terraform-shim.env` when `STACKYARD_SHIM_LOG_DIR` is
set, which tests use to assert argv and environment injection.

## Safety model (summary)

Stackyard treats apply/destroy as exclusive mutations: a workspace lock is the
admission ticket, and a single non-terminal run is the serialization key for
plan/apply pipelines. Secrets marked sensitive are write-only over the API after
create, but remain available to the runner as `TF_VAR_*` when categorized as
terraform variables.

## Extending commands

New commands require coordinated updates to:

1. `model.AllowedCommands`
2. policy argv mapping
3. success status selection (`planned` vs `applied`)
4. UI command select options
5. contract documentation

Do not add commands only in the UI.
