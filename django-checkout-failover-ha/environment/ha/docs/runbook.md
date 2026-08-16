# Shopdesk writer cutover

App boxes load `shopdesk.wsgi`. Operator commands are Django management commands:

```
python manage.py sync_standby
python manage.py cutover --node az-b
python manage.py dump_failover --output /app/ha/out/failover-status.json
```

`DATABASES['default']` is the writer file (`state/primary.sqlite` at lab start). `DATABASES['replica']` is the lagged copy (`state/standby.sqlite`). Sticky read hints use cache alias `pins`, key `sticky:shopper:<id>`. Do not store those hints in `django_session`.

Writer ownership is row `checkout-primary` in `ha_fence_lease`. The pair is `(owner_node, epoch)`; epoch only moves forward. A demoted box must have `writable=0`. `sync_standby` copies business tables and the replica seq watermark. It must not make the standby lease writable.

Reads after a write stay on the writer for `sticky_seconds` (see `config/ha.json`). Other reads may use replica only when `primary.wal_lsn - replica.applied_lsn` is `<= max_lag_lsn`. Place rejects a blank `attempt_id`. Capture/pay must not emit effects while the order `write_lsn` is ahead of the writer primary `wal_lsn`.

`/healthz` means the process answers. Live `/readyz` is the traffic gate and returns 503 unless all of the following hold: exactly one writable writer across both shop files, seq gap inside `max_lag_lsn`, the `pins` store is reachable, and `repeat_captures` is 0. Dump `accepting_checkout` is stricter than live `/readyz`: it is true only when the live `/readyz` gates pass, `pins` is `"shared"`, `standby_only_orders` is 0, incident-window orders exist on standby, and the standby lease is not writable (`fence_copied_to_standby` is false).

`dump_failover` writes `/app/ha/out/failover-status.json`:

```json
{
  "desk": "shopdesk",
  "accepting_checkout": false,
  "writer": "az-b",
  "writer_epoch": 1,
  "writers_seen": ["az-a", "az-b"],
  "standby_readable": false,
  "primary_seq": 0,
  "standby_seq": 0,
  "seq_gap": 0,
  "pins": "shared",
  "double_primary": true,
  "repeat_captures": 0,
  "standby_only_orders": 0,
  "incident_orders_on_standby": false,
  "fence_copied_to_standby": false
}
```
