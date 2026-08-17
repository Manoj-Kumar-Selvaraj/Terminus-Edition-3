# Yard desk contract

Binding rules for `/app/yard`. Operators use `/app/yard/bin/yardctl` only. Load `/app/yard/config/yard.json` on every command. Honor `yard_tz`, grace fields, and the path map. Changing those values must change behavior.

## CLI

```
yardctl <verb> [flags]
```

Mutating verbs require `--event-id` (non-empty). Identical `event_id` and payload return the stored result and must not add occupancy. The same `event_id` with a different payload is `EVENT_CONFLICT` and leaves state unchanged.

Usage and parse failures (unknown verb/flag, missing required flag, empty `--event-id`) exit `2` and must not create, truncate, or append the journal, sqlite, checkpoint, or any file under `/app/yard/out`.

| Verb | Required flags |
| --- | --- |
| `gate-in` | `--event-id --scac --trailer --visit-type --equipment --at --appointment-id` plus `--spot-id`. Optional `--door-id --seal --on-ground` |
| `gate-out` | `--event-id --visit-id --at`. Optional `--seal` |
| `dispatch-move` | `--event-id --visit-id --dest-spot-id` |
| `confirm-move` | `--event-id --move-id` |
| `cancel-move` | `--event-id --move-id` |
| `hold` | `--event-id --visit-id --hold-code --at` |
| `release-hold` | `--event-id --visit-id --hold-code --at` |
| `mount-chassis` | `--event-id --visit-id --chassis-id` |
| `dismount-chassis` | `--event-id --visit-id` |
| `snapshot` | optional `--as-of` |
| `detention-run` | optional `--as-of` |
| `health` | none |
| `replay` | none |

`--at` and `--as-of` are UTC instants with a trailing `Z`. `visit-type` is one of `LIVE_IN`, `DROP_IN`, `LIVE_OUT`, `EMPTY_OUT`, `LOADED_PICKUP`. `equipment` is one of `DRY_53`, `REEFER_53`, `TANK`, `CONTAINER_40`. `hold-code` is one of `YARD_OSND`, `YARD_SAFETY`, `CARRIER_SEAL`, `CARRIER_DOCS`. `--on-ground` is `0` or `1` (default `0` for live types, `1` for `DROP_IN` if omitted).

On process start of a mutating verb, if sqlite `applied_seq` lags the journal, apply journal events with `seq > checkpoint.last_applied_seq` before the new event.

## Time

Store instants as UTC with trailing `Z`. Convert to `yard_tz` (`America/Chicago`) for appointment windows and free-time arithmetic, including DST. `grace_early_minutes` applies before `window_start`; `grace_late_minutes` applies after `window_end`. Inclusive window after conversion: gate-in local instant in `[window_start, window_end]` or within grace.

## Appointments

Match one OPEN appointment: same `facility_id`, `scac`, `visit_type`, compatible `door_class`, and either an equal `trailer_number` or a pool slot (`trailer_number` null) for that SCAC only. No match → `APPOINTMENT_MISSING`. Outside window and grace → `APPOINTMENT_WINDOW`.

## Identity

At most one open visit (`ON_YARD`, `MOVING`, `DOCKED`) per `(scac, trailer_number)`. A second open visit is `VISIT_OPEN`. Closed visits do not block a later gate-in of the same unit. Loaded `LIVE_IN`, `LIVE_OUT`, and `LOADED_PICKUP` require a non-empty seal (`SEAL_REQUIRED`). Missing `(scac, visit_type)` in `carrier_contracts.json` is `CONTRACT_MISSING` at gate-in.

## Occupancy and doors

One occupant per spot. A dest spot of an `IN_TRANSIT` move is reserved for that `move_id` (`SPOT_OCCUPIED` if occupied or reserved). Door eligibility: `REEFER_53` requires `reefer_plug=1`; `LIVE_IN`/`LIVE_OUT` require `live_capable=1`; `DROP_IN` may not occupy a door with `drop_capable=0`; equipment must be in `allowed_equipment`. Failures use `DOOR_CLASS` or `DOOR_OCCUPIED`.

Live types that name a door occupy that door's `DOCK_APRON` spot. Drop types occupy `DROP_LOT` or `STAGING` only.

## Moves and chassis

States: `REQUESTED → DISPATCHED → IN_TRANSIT → COMPLETED`, or `CANCELLED` / `FAILED` from `IN_TRANSIT`. While `IN_TRANSIT` the trailer occupies neither origin nor dest; dest is reserved. `COMPLETED` occupies dest and frees origin (and sets door occupant when dest is `DOCK_APRON`). `CANCELLED`/`FAILED` restore origin and clear the reservation.

Dropped `DRY_53`, `REEFER_53`, and `CONTAINER_40` with `on_ground=1` cannot enter `IN_TRANSIT` until a chassis is mounted (`CHASSIS_REQUIRED`). Live visits with tractor wheels do not need pool chassis. One chassis mounts at most one open visit. `mount-chassis` sets `on_ground=0` and pairs `chassis_id`. `dismount-chassis` returns the unit to `CHASSIS_STACK`.

Gate-out while `MOVING` is `MOVE_IN_FLIGHT`.

## Holds and detention

All four hold codes block gate-out (`HOLD_BLOCKS_OUT`) until released. Duplicate active `(visit_id, hold_code)` is `HOLD_ACTIVE`. `release-hold` of an inactive/unknown hold is `HOLD_MISSING`. Hold on a closed visit is `VISIT_MISSING`.

Pause-class holds (`YARD_OSND`, `YARD_SAFETY`) stop detention accrual while active. `CARRIER_SEAL` and `CARRIER_DOCS` do not pause. Clock continues through carrier holds.

**clock_start**

- `LIVE_IN` / `LIVE_OUT`: `max(appointment.window_start converted to UTC, gate_in)`
- `DROP_IN` / `EMPTY_OUT` / `LOADED_PICKUP`: `gate_in`

**free_minutes** from `carrier_contracts.json`. **chargeable_minutes** are whole minutes after `clock_start + free_minutes`, excluding pause intervals, until `gate_out` or `--as-of` for still-open visits. Negative values publish as `0`.

## Journal, restart, warehouse

`/app/yard/var/events.jsonl` is the source of truth for accepted events. Sqlite is derived. `/app/yard/var/checkpoint.json` stores `last_applied_seq`, sorted `open_visit_ids`, and occupancy digest. Replay from checkpoint must not invent or drop open visits.

`/app/yard/warehouse/prior_cycle.sqlite` is a prior cycle. Snapshot, detention, and health must not mix those rows into live occupancy or live charges. `health.warehouse_untouched` is true only when live publish ignored that file.

Kill mid-command: either the journal line is absent (no occupancy change after replay) or the line is complete and sqlite may catch up. No half-applied occupancy.

Rejected mutating commands (after a successful parse) append one JSON object to `/app/yard/out/rejects.jsonl`. Usage errors do not append. Accepted commands do not append rejects.

## Publish schemas

`/app/yard/out/snapshot.json` object, keys in this order:

`facility_id` string, `generated_at` UTC Z, `yard_tz` string, `as_of` UTC Z, `open_visits` array sorted by `visit_id`, `occupancy` array of `{spot_id, zone, visit_id}` sorted by `spot_id`, `doors` array of `{door_id, door_class, visit_id}` (`visit_id` may be null) sorted by `door_id`, `in_transit` array of `{move_id, visit_id, origin_spot_id, dest_spot_id}` sorted by `move_id`, `holds` array of `{visit_id, hold_code, placed_at}` active only, sorted by `visit_id` then `hold_code`, `counts` object `{open_visits, occupied_spots, doors_occupied, in_transit, active_holds}` integers.

Visit objects in `open_visits`, field order: `visit_id`, `scac`, `trailer_number`, `visit_type`, `equipment`, `state`, `spot_id` (null if `MOVING`), `door_id` (null if not `DOCKED`), `gate_in`, `appointment_id`, `seal`.

`/app/yard/out/detention.jsonl` one object per live visit (open or closed in the operating sqlite, never warehouse), fields in order: `visit_id`, `scac`, `visit_type`, `clock_start`, `free_minutes`, `pause_minutes`, `chargeable_minutes`, `status` (`OPEN` or `CLOSED`). Sorted by `visit_id`.

`/app/yard/out/moves.jsonl` one object per move in sqlite, fields: `move_id`, `visit_id`, `state`, `origin_spot_id`, `dest_spot_id`, `seq`. Sorted by `seq`.

`/app/yard/out/rejects.jsonl` objects: `code`, `event_id`, `detail`.

`/app/yard/out/health.json`: `ok` bool, `applied_seq` int, `journal_seq` int, `occupancy_digest` string, `open_visit_ids` sorted array, `warehouse_untouched` bool. `ok` is true only when `applied_seq` equals `journal_seq`, the occupancy digest matches journal-derived occupancy, and `warehouse_untouched` is true.

Occupancy digest is lowercase hex SHA-256 of `spot_id=visit_id` lines sorted by `spot_id`, one line each, UTF-8, newline-terminated. Reserved dest spots use `spot_id=#move_id`.
