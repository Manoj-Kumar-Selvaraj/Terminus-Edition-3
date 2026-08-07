# HTTP Terraform backend contract

This service is the remote state store for the lab Terraform roots under
`/app/terraform/workspaces/{prod,stage}`. Durable files belong in
`/app/var/backend-store`. Operator commands live in `/app/bin`.

## Endpoints

Bind `127.0.0.1` on the port from `BACKEND_PORT` (default `18765`).

| Method | Path | Behavior |
|--------|------|----------|
| `GET` | `/v1/workspaces/{name}/state` | Return current state JSON body, or `404` when empty. |
| `POST` | `/v1/workspaces/{name}/state` | Commit a new state document. Require lock ID via query `ID` (Terraform) or header `Lock-ID` matching the active lease for that workspace. Optional `Idempotency-Key` must make lost-response retries a no-op. |
| `LOCK` | `/v1/workspaces/{name}/lock` | Acquire a lease. Body is Terraform lock info JSON (`ID`, `Who`, `Operation`, …). `423` when another unexpired lease owns the workspace. |
| `UNLOCK` | `/v1/workspaces/{name}/lock` | Release only when body/header lock ID matches the holder. |
| `POST` | `/v1/control/advance` | Body `{"ticks": N}` advances the deterministic lease clock by `N` (integer ≥ 0). |
| `GET` | `/v1/control/clock` | `{"tick": <int>}` current clock. |
| `GET` | `/v1/control/health` | `{"ok": true}` when the store is open. |

Lease lifetime is `LEASE_TTL_TICKS` (default `10`) measured in control-clock ticks, not wall time. Only an expired lease may be replaced by a different owner.

## State fencing

Each workspace keeps its own state blob, serial, lineage, and lock row. A commit
must:

1. Hold the matching lock ID.
2. Refuse a payload whose `lineage` disagrees with the stored lineage once state exists.
3. Refuse a payload whose `serial` is not exactly `stored_serial + 1` for a non-empty prior state (first commit may create lineage and set serial from the payload). Identical body retries are idempotent.
4. Treat a repeated `Idempotency-Key` for an already-committed body as success without advancing serial again or rewriting history.

## Audit export

`/app/bin/export-audit` writes `/app/output/audit.json`:

```json
{
  "schema_version": 1,
  "events": [
    {
      "seq": 1,
      "tick": 0,
      "workspace": "prod",
      "event": "lock_acquired|lock_rejected|lock_released|state_committed|state_rejected|lease_reclaimed",
      "detail": {}
    }
  ]
}
```

Events are ordered by `seq`. Workspace fields must reflect the workspace that
owned the lock or state mutation. Concurrent work on `stage` must not appear as
mutations under `prod` state.

## Provider provenance

Terraform CLI config is `/app/terraform.tfrc` with filesystem mirror
`/opt/terraform-provider-mirror`. `/app/bin/operator-apply` must `terraform init`
against that mirror, keep `.terraform.lock.hcl` consistent with mirrored
packages, and fail closed before apply when a lockfile hash is missing from the
mirror or an unapproved provider path is supplied via `UNAPPROVED_PROVIDER_DIR`.
