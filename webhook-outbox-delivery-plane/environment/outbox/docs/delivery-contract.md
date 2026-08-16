# Outbox Delivery Contract

Absolute product root: `/app/outbox`.

## Environment

| Variable | Meaning | Default |
|---|---|---|
| `OUTBOX_DB` | SQLite database file path | `/app/outbox/data/outbox.db` |
| `OUTBOX_ADDR` | HTTP listen address | `127.0.0.1:8080` |
| `OUTBOX_DATA` | Auxiliary data directory | `/app/outbox/data` |
| `OUTBOX_TOKEN` | Bearer token required for DLQ replay (and other operator mutations listed below) when set; empty disables token checks | empty |
| `OUTBOX_SYNC` | When `1`, claim→deliver→complete runs synchronously inside claim/deliver helpers used by graded API flows | empty |
| `OUTBOX_ROOT` | Product root (docs, ui, schema) | `/app/outbox` |

On startup the server must:

1. Create parent directories for `OUTBOX_DB` and `OUTBOX_DATA`.
2. Apply `/app/outbox/db/schema.sql` if tables are missing.
3. Serve static UI files from `/app/outbox/ui` at `/`.
4. Expose JSON API under `/api/v1/...`.
5. Expose CLI at `/app/outbox/bin/outboxctl` against the same API.

### Graded delivery path vs background worker

The graded delivery contract is exercised through `POST .../claim` then `POST .../deliver` (and `complete`) with `OUTBOX_SYNC=1`. That synchronous helper path is authoritative for signatures, quota, backoff, audit, and lease fencing. An optional background worker loop may deliver pending events for operators when `OUTBOX_SYNC` is unset; it is not a separately graded path unless a verifier explicitly drives it.

Image builds seed a catalog database at the default `OUTBOX_DB` path (`/app/outbox/data/outbox.db`) plus `/app/outbox/bin/seed` and `/app/outbox/scripts/seed.sh`. Fresh verifier databases may be empty; schema application and seed tooling under `/app/outbox` must remain available.

## Authentication

When `OUTBOX_TOKEN` is non-empty:

- `POST /api/v1/events/{id}/replay` requires `Authorization: Bearer <token>`.
- Missing or invalid token → HTTP 401 `{"error":"unauthorized"}`.

Other read/enqueue/claim/deliver routes do not require the token unless noted.

## Identifiers

Opaque strings: `ten_`, `ep_`, `evt_`, `att_`, `aud_`.

## Tenants

- `GET /api/v1/tenants` → `{"tenants":[Tenant,...]}`
- `POST /api/v1/tenants` body `{"name":string,"slug":string,"deliveries_per_hour":int}` → Tenant (201)
- `GET /api/v1/tenants/{tenant_id}` → Tenant

```json
{"id":"ten_...","name":"...","slug":"...","deliveries_per_hour":100,"created_at":"RFC3339"}
```

`deliveries_per_hour` is the rolling-window successful-delivery quota for the tenant.

## Endpoints

- `GET /api/v1/tenants/{tenant_id}/endpoints` → `{"endpoints":[Endpoint,...]}`
- `POST /api/v1/tenants/{tenant_id}/endpoints` body `{"name":string,"url":string,"hmac_secret":string,"enabled":bool,"max_attempts":int}` → Endpoint (201)
- `GET /api/v1/endpoints/{endpoint_id}` → Endpoint
- `PATCH /api/v1/endpoints/{endpoint_id}` body partial fields → Endpoint
- `POST /api/v1/endpoints/{endpoint_id}/pause` → Endpoint (`paused=true`)
- `POST /api/v1/endpoints/{endpoint_id}/resume` → Endpoint (`paused=false`)

```json
{
  "id":"ep_...",
  "tenant_id":"ten_...",
  "name":"hooks",
  "url":"http://127.0.0.1:9/hook",
  "hmac_secret":"...",
  "enabled":true,
  "paused":false,
  "max_attempts":5,
  "created_at":"RFC3339"
}
```

`hmac_secret` is returned on create/get for local operators (not redacted in this product).

### Pause semantics

While `paused=true` or `enabled=false`, `POST .../claim` on events for that endpoint must return HTTP 409 `{"error":"endpoint_unavailable"}`. Enqueue may still succeed for paused endpoints; disabled endpoints reject enqueue with 409 `{"error":"endpoint_disabled"}`.

## Events (outbox)

- `POST /api/v1/endpoints/{endpoint_id}/events` body `{"payload":object,"idempotency_key":string|null}` → Event (201)
- `GET /api/v1/events/{event_id}` → Event
- `GET /api/v1/tenants/{tenant_id}/events?status=&limit=` → `{"events":[Event,...]}` newest first
- `POST /api/v1/events/{event_id}/claim` body `{"lease_owner":string,"lease_seconds":int}` → Event (200)
- `POST /api/v1/events/{event_id}/complete` body `{"lease_owner":string,"outcome":"delivered"|"failed","http_status":int,"error":string}` → Event
- `POST /api/v1/events/{event_id}/deliver` body `{"lease_owner":string}` → performs HTTP POST then complete (used when `OUTBOX_SYNC=1` or by workers)
- `POST /api/v1/events/{event_id}/replay` → moves `dlq` → `pending`, clears lease (200)

Unknown `event_id` on `GET /api/v1/events/{event_id}` → HTTP 404 `{"error":"not_found"}`.

`payload` on enqueue must be a JSON object. Arrays, scalars, or other non-object values → HTTP 400 (validation error body).

```json
{
  "id":"evt_...",
  "tenant_id":"ten_...",
  "endpoint_id":"ep_...",
  "payload":{},
  "idempotency_key":null,
  "status":"pending",
  "attempt_count":0,
  "lease_owner":null,
  "lease_until":null,
  "next_attempt_at":"RFC3339",
  "created_at":"RFC3339",
  "updated_at":"RFC3339"
}
```

Statuses: `pending`, `claimed`, `delivered`, `failed`, `dlq`.

### Idempotency

If `idempotency_key` is non-empty and an event already exists for the same endpoint with that key, return the existing event with HTTP 200 (not 201).

### Quota on enqueue and delivery

Count rows in `delivery_attempts` where `outcome='delivered'` and `created_at` is within the last 3600 seconds for the tenant. If count `>= deliveries_per_hour`:

- enqueue → 429 `{"error":"quota_exceeded"}`
- deliver/complete as delivered → 429 `{"error":"quota_exceeded"}` and do not mark delivered

Failed attempts do **not** consume quota.

### Claim fencing

- Only `pending` (or `claimed` with expired `lease_until`) events may be claimed.
- Successful claim sets `status=claimed`, `lease_owner`, `lease_until=now+lease_seconds` (default 30 if omitted or <1).
- If another non-expired lease is held by a different owner → 409 `{"error":"lease_held"}`.
- Same owner renewing before expiry is allowed (200, refreshed lease).
- After `lease_until` passes, a different owner may claim successfully (reclaim).
- Only the current `lease_owner` may `complete` or `deliver`. Mismatch → 409 `{"error":"lease_mismatch"}`.
- Paused/disabled endpoints reject claim as above.

### Delivery HTTP

`POST` to endpoint URL with body = compact JSON of `payload` and headers:

- `Content-Type: application/json`
- `X-Outbox-Id: <event id>`
- `X-Outbox-Timestamp: <unix seconds decimal string>`
- `X-Outbox-Signature: hex(HMAC-SHA256(secret, canonical))`

**Compact JSON encoding (exact):** serialize the payload object with no insignificant whitespace (same rules as Go `encoding/json` default `Marshal`). Object keys are sorted lexicographically at every nesting level. Nested objects follow the same sorted-key compact form. The signed body bytes must be exactly those compact bytes.

Canonical string (exact bytes):

```text
<id>\n<timestamp>\n<body>
```

Three fields separated by single newline `0x0A`. No trailing newline after body.

HTTP 2xx → outcome delivered. Other statuses or transport errors → failed attempt.

### Backoff schedule

After a failed attempt `n` (1-based), set `next_attempt_at = now + backoff(n)` where seconds are:

`[5, 15, 45, 120, 300]` then stay at 300 for further failures.

When `attempt_count >= max_attempts` after a failure → status `dlq` (not `failed`). Intermediate failures while under max stay `pending` with updated `next_attempt_at` (lease cleared).

### Replay

From `dlq` only. Requires bearer token when `OUTBOX_TOKEN` set. Sets status `pending`, `attempt_count` unchanged, clears lease, sets `next_attempt_at=now`. Audit action `replay`.

## Delivery attempts

- `GET /api/v1/events/{event_id}/attempts` → `{"attempts":[Attempt,...]}`

```json
{"id":"att_...","event_id":"evt_...","attempt_no":1,"outcome":"delivered"|"failed","http_status":200,"error":"","created_at":"RFC3339"}
```

## Audit

- `GET /api/v1/audit?limit=` → `{"events":[AuditEvent,...]}` newest first

Required actions (string `action` field): `enqueue`, `claim`, `deliver.ok`, `deliver.fail`, `dlq`, `replay`, `pause`, `resume`.

```json
{"id":"aud_...","action":"claim","entity_type":"event","entity_id":"evt_...","actor":"worker-1","detail":{},"created_at":"RFC3339"}
```

Every successful claim must write `claim`. Transition into `dlq` must write `dlq`. Pause/resume write `pause`/`resume`. Failed delivery attempts must write `deliver.fail`. Successful deliveries write `deliver.ok`.

For `enqueue` audits, `detail` MUST include `endpoint_id` set to the endpoint that received the event.

## Health / stats

- `GET /api/v1/health` → `{"status":"ok"}`
- `GET /api/v1/stats` → exact shape:

```json
{
  "tenants": 0,
  "endpoints": 0,
  "by_status": {
    "pending": 0,
    "claimed": 0,
    "delivered": 0,
    "failed": 0,
    "dlq": 0
  }
}
```

`tenants` and `endpoints` are integer counts. `by_status` maps each event status string to its count (missing keys may be omitted or zero).

## CLI (`outboxctl`)

Binary path: `/app/outbox/bin/outboxctl`. Subcommands talk to `OUTBOX_ADDR` base URL `http://$OUTBOX_ADDR`:

- `outboxctl health`
- `outboxctl tenants list`
- `outboxctl enqueue --endpoint ep_... --payload '{"a":1}' [--idempotency-key k]`
- `outboxctl claim --event evt_... --owner name [--seconds 30]`
- `outboxctl deliver --event evt_... --owner name`
- `outboxctl replay --event evt_...` (sends bearer when `OUTBOX_TOKEN` set)
- `outboxctl pause --endpoint ep_...`
- `outboxctl resume --endpoint ep_...`
- `outboxctl audit [--limit 50]`

## UI

Static pages under `/app/outbox/ui`. The index document title (and page heading) is `Outbox Delivery Plane`. Forms must POST JSON using contract field names:

- claim: `lease_owner`, `lease_seconds`
- replay: POST with no body (Authorization header from token input)
- enqueue: `payload` (JSON text), optional `idempotency_key`

API error responses must be shown in an element with id `error-box` (textContent = `error` field or raw body). Silent failure is non-compliant.
