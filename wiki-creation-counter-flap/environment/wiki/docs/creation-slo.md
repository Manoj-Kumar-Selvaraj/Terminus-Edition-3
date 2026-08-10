# Creation SLO

Two replica processes listen on `127.0.0.1:8001` and `127.0.0.1:8002`. SQLite file is `/app/wiki/var/wiki.db`. Flap moves it to `/app/wiki/var/wiki.db.flapped`. Restore moves it back.

## Probes

| Path | Meaning |
| --- | --- |
| `/health/live` | process up, never queries the database, 200 `{"status":"alive"}` |
| `/health/ready` | `SELECT 1` succeeds → 200 `{"status":"ready"}`; else 503 |
| `/health/startup` | 200 `{"status":"started"}`, no DB |

## Metrics

`users_created_total` and `posts_created_total` must equal `COUNT(*)` on those tables after restore. Reconstitute from durable rows; do not require a process restart.

POST `/posts` with a missing user returns HTTP 404 `{"detail":"User not found"}`. User JSON uses `id`; post JSON uses `post_id`.

## `/app/wiki/out/probe-matrix.json`

```json
{
  "live_8001": "alive",
  "live_8002": "alive",
  "ready_8001": "ready|not_ready",
  "ready_8002": "ready|not_ready",
  "db_present": true
}
```

`ready_*` is `ready` when that replica returned 200, else `not_ready`. `db_present` is whether `/app/wiki/var/wiki.db` exists.

## `/app/wiki/out/creation-reconcile.json`

```json
{
  "users_table": 0,
  "posts_table": 0,
  "users_metric": 0,
  "posts_metric": 0,
  "reconciled": true,
  "scrape_targets": ["127.0.0.1:8001", "127.0.0.1:8002"]
}
```

`reconciled` is true only when both metric totals equal the table counts and both scrape targets are listed.
