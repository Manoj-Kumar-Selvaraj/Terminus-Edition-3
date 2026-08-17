# SYSTEM_ARCHITECTURE — yard-gate-dock-dwell-control

```text
STATUS: ARCHITECTURE_READY
CONTROL_PLANE_COMMIT: 6e3944669a62da5c2a9ae9c6a2528e11b772ca86
CREATION_PROFILE: large_system_strict
CATEGORY/SUBCATEGORY: Operations / Logistics
LANGUAGES: python, sql
NETWORK_MODE: public
TASK_SLUG: yard-gate-dock-dwell-control
WORKDIR: /app/yard
```

This is the **clean inherited yard control plane**. No defects, incomplete behaviors, starter gaps, Oracle, or tests are decided here.

The work package is a live DC yard desk: every trailer is accounted from gate-in through yard/dock occupancy to gate-out, with appointment windows, door fit, chassis pairing, holds, and detention clocks agreeing after restart. It is not a freight checksum ledger, not COBOL stock/transit receipts, not workshop bay/technician booking, and not rail/customs hold-and-release.

---

## COMPONENT_GRAPH

Solver-visible runtime lives under `/app/yard`. Image-build seed is an operator tool, not the production decision path.

| Package | Responsibility |
| --- | --- |
| `yardctl` (`cli/`) | Operator CLI. Parse/validate args, fail usage errors before any journal or output write, dispatch one command, print the documented JSON/text result. |
| `yard.journal` | Append-only event log with monotonic `seq`, durable `event_id` idempotency, and `EVENT_CONFLICT` when the same id arrives with a different payload. |
| `yard.replay` | Restart: restore checkpoint occupancy, apply only `seq > checkpoint.last_applied_seq`, refuse to invent or drop open visits. |
| `yard.identity` | Visit identity: `scac` + `trailer_number` uniqueness among **open** visits; visit_id assignment; equipment class parse (SCAC, unit number, optional ISO size/type for containers). |
| `yard.appointments` | Appointment book match, yard-local window/grace, door-class reservation, no-show close of leftover appointments. |
| `yard.timeutil` | Instant storage in UTC; all window and free-time arithmetic in `America/Chicago`; DST-safe conversion. |
| `yard.gate` | Gate-in / gate-out: appointment, seal, tractor, open-visit, hold, in-transit, and occupancy release rules. |
| `yard.inventory` | Exclusive spot occupancy. Zones: `DROP_LOT`, `STAGING`, `DOCK_APRON`, `CHASSIS_STACK`. One occupant per spot. |
| `yard.doors` | Door catalog and eligibility: equipment class, reefer plug, live vs drop, one live occupant per door, apron spot coupling. |
| `yard.chassis` | Chassis pool, mount/dismount, “needs wheels to roll” for dropped equipment. |
| `yard.moves` | Jockey move state machine: request → dispatch → in_transit → completed \| cancelled \| failed. Origin/dest reservation. |
| `yard.holds` | Hold register, pause vs non-pause classes, gate-out blocking, release. |
| `yard.detention` | Free-time start, pause intervals, whole-minute accrual, ledger rows for closed visits. |
| `yard.publish` | Write snapshot, move journal extract, detention ledger, reject log, health. Reconcile sqlite occupancy views with journal-derived state. |
| `yard.policy` | Load `/app/yard/config/yard.json` and carrier free-time table. No hidden defaults that contradict the contract. |
| `sql/` | Physical schema, check constraints, occupancy/door views used at publish/health time. |
| `cmd/seed` | Deterministic image-build materializer of the 14-day visit/appointment/move history. Not counted as production decision logic. |

Coupling that must stay in the architecture (this is the work package, not a list of chores):

```text
appointment window (yard TZ)
  -> gate-in accept/reject
  -> visit open + spot occupancy
  -> door eligibility (class / plug / live-drop)
  -> chassis required for a roll
  -> move confirm relocates occupancy
  -> holds block gate-out and may pause detention
  -> gate-out closes visit and occupancy
  -> detention ledger uses clock_start + pauses + gate-out
```

A wrong key, timezone, or move state corrupts occupancy **and** charges. Partial completion of one box without the next is an A3 concern later, not an architecture defect map.

---

## ENTRYPOINTS

| Surface | Path / name |
| --- | --- |
| Operator CLI | `/app/yard/bin/yardctl` |
| Image-build seed | `/app/yard/bin/seed` |
| Workdir | `/app/yard` |
| Config | `/app/yard/config/yard.json` |
| Carrier free-time | `/app/yard/config/carrier_contracts.json` |
| Binding contract | `/app/yard/docs/yard-contract.md` |
| Schema | `/app/yard/sql/schema.sql` |
| Env | `YARD_ROOT` default `/app/yard` |

CLI verbs (public, stable). Usage/parse failures exit `2` and must not create, truncate, or append journal, sqlite, checkpoint, or `/app/yard/out/*`.

| Verb | Mutates | Result |
| --- | --- | --- |
| `gate-in` | yes | open visit + occupancy or reject |
| `gate-out` | yes | close visit + release occupancy or reject |
| `dispatch-move` | yes | move DISPATCHED/IN_TRANSIT or reject |
| `confirm-move` | yes | relocate occupancy or reject |
| `cancel-move` | yes | restore origin occupancy or reject |
| `hold` / `release-hold` | yes | hold register |
| `mount-chassis` / `dismount-chassis` | yes | chassis pairing |
| `snapshot` | no (publish only) | `/app/yard/out/snapshot.json` |
| `detention-run` | no (publish only) | `/app/yard/out/detention.jsonl` |
| `health` | no | `/app/yard/out/health.json` |
| `replay` | derived state only | rebuild sqlite from checkpoint + journal |

Every mutating verb requires `--event-id`. Identical id + payload is a stored replay (byte-stable documented fields). Same id + different payload is `EVENT_CONFLICT` and leaves state unchanged.

On process start of any mutating verb, if sqlite `applied_seq` lags the journal, run the same replay path before the new event.

---

## STATE_MODEL

### Source of truth

- **Journal** `/app/yard/var/events.jsonl` is the source of truth for accepted operational events.
- **Sqlite** `/app/yard/var/yard.sqlite` is derived occupancy, appointments, holds, chassis, and visit projections.
- **Checkpoint** `/app/yard/var/checkpoint.json` stores `last_applied_seq`, sorted `open_visit_ids`, and an occupancy digest so restart does not scan the whole history every time.
- **Warehouse** `/app/yard/warehouse/prior_cycle.sqlite` is an immutable prior-cycle dump. Publish, detention, and replay must not mix those rows into live occupancy or live detention. Do not count warehouse SQL as production LOC.

### Visit lifecycle

```text
SCHEDULED (appointment only)
  -> ON_YARD          (accepted gate-in, occupies a spot)
  -> MOVING           (in_transit move; occupies neither origin nor dest; dest reserved)
  -> DOCKED           (occupies the door's DOCK_APRON spot; door.occupant = visit)
  -> CLOSED           (accepted gate-out)
SCHEDULED -> NO_SHOW  (window + late grace elapsed, never gated)
```

Open visits are `ON_YARD | MOVING | DOCKED`. At most one open visit per `(scac, trailer_number)`.

### Move lifecycle

```text
REQUESTED -> DISPATCHED -> IN_TRANSIT -> COMPLETED
                       \-> CANCELLED
                       \-> FAILED
```

- `IN_TRANSIT`: trailer is not counted in origin or dest occupancy; dest spot is reserved for this `move_id`.
- `COMPLETED`: dest occupied, origin free, door occupant updated when dest zone is `DOCK_APRON`.
- `CANCELLED` / `FAILED` from `IN_TRANSIT`: origin occupancy restored, dest reservation cleared.
- Kill mid-command: either the journal line is absent (no occupancy change) or the journal line is complete and sqlite may lag until replay. No half-applied occupancy.

### Appointment match (gate-in)

Match **one** appointment:

1. `facility_id` equals config.
2. `scac` equals.
3. `visit_type` equals the gate-in type.
4. `door_class` on the appointment is compatible with requested door (if a door is supplied) or with the assigned door/spot class.
5. Optional `trailer_number`: if the appointment names a unit, it must match; if the appointment is a pool slot (`trailer_number` null), any unit of the SCAC may claim it once.
6. Gate-in instant converted to `America/Chicago` falls in `[window_start, window_end]` **or** within `grace_early_minutes` before start **or** `grace_late_minutes` after end.

No match → `APPOINTMENT_MISSING`. Outside window and grace → `APPOINTMENT_WINDOW`. Claiming a second appointment for an already-open visit → `VISIT_OPEN`.

### Clock and detention (complete-system rule)

All event timestamps are UTC instants. Windows and free-time math use `yard_tz = America/Chicago`.

**clock_start**

- `LIVE_IN` / `LIVE_OUT`: `max(appointment.window_start_utc, gate_in_utc)`.
- `DROP_IN` / `EMPTY_OUT` / `LOADED_PICKUP`: `gate_in_utc`.

**free_minutes** come from `carrier_contracts.json` keyed by `(scac, visit_type)`. Missing contract → reject gate-in `CONTRACT_MISSING` (fail closed).

**pause**: while a pause-class hold is open, detention does not accrue. Pause-class: `YARD_OSND`, `YARD_SAFETY`. Non-pause (clock continues): `CARRIER_SEAL`, `CARRIER_DOCS`. All four block gate-out until released.

**accrual**: whole minutes after `clock_start + free_minutes`, excluding pause intervals, until `gate_out_utc`. If the visit is still open, `detention-run` uses the run's `as_of` instant (CLI `--as-of` or journal head time). Negative accrual is published as `0`.

Early arrival does not start live free time before `window_start`. Late-within-grace arrival still uses the `max(window_start, gate_in)` rule, so lateness burns free time.

### Gate-in / gate-out fail-closed

Gate-in rejects (no journal accept, no occupancy):

| Code | When |
| --- | --- |
| `APPOINTMENT_MISSING` | no matching appointment |
| `APPOINTMENT_WINDOW` | outside window and grace |
| `VISIT_OPEN` | open visit already exists for scac+trailer |
| `SEAL_REQUIRED` | loaded inbound/outbound requires a non-empty seal |
| `SPOT_OCCUPIED` | requested/assigned spot has an occupant or dest reservation |
| `DOOR_CLASS` | equipment or live/drop does not fit the door |
| `DOOR_OCCUPIED` | door already has an occupant |
| `CONTRACT_MISSING` | no free-time row for scac+visit_type |
| `EVENT_CONFLICT` | event_id reuse with different payload |

Gate-out rejects:

| Code | When |
| --- | --- |
| `VISIT_MISSING` | no open visit |
| `HOLD_BLOCKS_OUT` | any unreleased hold |
| `MOVE_IN_FLIGHT` | visit is `MOVING` |
| `SEAL_REQUIRED` | loaded outbound missing seal |
| `EVENT_CONFLICT` | as above |

Accepted gate-in occupies exactly one spot. Live types that name a door occupy that door's `DOCK_APRON` spot. Drop types occupy a `DROP_LOT` or `STAGING` spot, never a live-only door.

### Door eligibility

Door row fields: `door_id`, `door_class` (`DRY`, `REEFER`, `OUTBOUND`), `reefer_plug` bool, `live_capable` bool, `drop_capable` bool, `allowed_equipment` list.

- `REEFER_53` requires `reefer_plug = true`.
- `LIVE_IN` / `LIVE_OUT` require `live_capable`.
- `DROP_IN` may not occupy a door with `drop_capable = false`.
- Equipment must be in `allowed_equipment`.

### Chassis

Dropped `DRY_53` / `REEFER_53` / `CONTAINER_40` with `on_ground = true` cannot enter `IN_TRANSIT` until a chassis is mounted (`CHASSIS_REQUIRED`). Live visits arrive with tractor+wheels; they do not need pool chassis to roll to a door. `mount-chassis` pairs a free pool chassis to a visit; `dismount-chassis` returns it to `CHASSIS_STACK`. A chassis cannot mount two visits.

### Holds

`hold` on a closed visit → `VISIT_MISSING`. Duplicate active hold of the same `hold_code` on one visit → `HOLD_ACTIVE`. `release-hold` of an unknown/inactive hold → `HOLD_MISSING`.

### Idempotency and restart

- Primary idempotency key: `event_id`.
- Replay key: `seq` (monotonic, assigned at first accept).
- `replay` / start-of-command catch-up must yield the same occupancy digest and `open_visit_ids` as a clean apply of the journal from checkpoint.
- Publishing is a function of derived state plus journal rejects. `snapshot` and `detention-run` are repeatable for the same `as_of`.

### Reject log

Rejected mutating commands append one JSON object to `/app/yard/out/rejects.jsonl` **after** a successful parse (usage errors do not append). Accepted commands do not append rejects.

---

## SOLVER_VISIBLE_DOC_PLAN

| Path | Owns |
| --- | --- |
| `/app/yard/docs/yard-contract.md` | CLI verbs and flags; event_id semantics; visit/move/hold state machines; appointment match; timezone; detention clock; reject codes; JSON schemas for snapshot, detention rows, reject rows, health; restart/replay. |
| `/app/yard/docs/layout.md` | Directory map, sqlite vs journal vs warehouse ownership. |
| `/app/yard/sql/schema.sql` | Tables, checks, occupancy views. |
| `/app/yard/config/yard.json` | Facility, tz, grace, paths. |
| `/app/yard/config/carrier_contracts.json` | Per-SCAC free_minutes by visit_type. |

Docs describe how the inherited system is organized and governed. They must not become a second prompt, a repair map, or a dump of instruction goals. Material work-request bullets stay in `instruction.md` at A7.

No `notes/` incident novel is required unless a later writing stage asserts current-state facts; if it does, those facts need a real log or status file. Architecture does not invent a fake outage story.

---

## PRODUCTION_CHARACTERISTICS

- Differentiated Python packages with distinct yard responsibilities, not cloned CRUD wrappers.
- Real operator CLI as the only mutation path (no hidden HTTP).
- Sqlite + JSONL persistence, checkpoint/replay, fail-closed rejects, event_id idempotency.
- Interacting constraints: appointment TZ, door class, chassis, holds, detention pauses.
- Meaningful validation and closed reject vocabulary.
- Deterministic seed of varied carriers, visit types, equipment, holds, and times.
- SQL views participate at health/publish (occupancy disagreement is a health failure), not decorative schema-only files.

Canonical agent image: digest-pinned Python bookworm, `tzdata` installed (required for `America/Chicago`), `tmux` + `asciinema`, sqlite3. Single container. No GPU. No privileged flags.

---

## SCALE_FIT

Natural modules (gate, appointments/time, inventory, doors, chassis, moves, holds, detention, journal/replay, publish, CLI, SQL views) support well above 3,000 substantive reachable LOC without seed, warehouse, or duplicated templates.

Organic F2P surfaces (for A3/A5 later — not a test list and not defect locations): on-window gate-in; early/late grace; missing appointment; duplicate open visit; seal required; door class / reefer plug; door occupied; spot exclusive; chassis required vs live wheels; move confirm relocates; cancel in-transit restores origin; hold blocks out; pause vs non-pause detention; live vs drop clock_start; timezone window vs UTC stamp; event_id replay; event_id conflict; usage error does not touch outputs; empty-occupancy snapshot after last gate-out; detention zero inside free time; detention whole minutes after; warehouse not mixed into live snapshot; health occupancy digest; kill/replay catch-up; pool appointment trailer wildcard; no-show leftover; mounted chassis uniqueness.

That is a 25–30 F2P range without stacking an unrelated product (no HOS, no ULD, no rail customs, no workshop bays).

If A3 cannot place 4–8 root-cause clusters on this graph without padding, return `SCENARIO_TOO_SMALL` then — the architecture itself is not too small.

---

## RESOURCE_GRAPH

| Resource | Role |
| --- | --- |
| `/app/yard/var/events.jsonl` | accepted event source of truth |
| `/app/yard/var/yard.sqlite` | derived visits, spots, doors, appointments, holds, chassis, moves |
| `/app/yard/var/checkpoint.json` | replay fence |
| `/app/yard/config/yard.json` | facility policy |
| `/app/yard/config/carrier_contracts.json` | free-time table |
| `/app/yard/sql/schema.sql` | physical model |
| `/app/yard/warehouse/prior_cycle.sqlite` | immutable prior cycle |
| `/app/yard/out/snapshot.json` | published occupancy/visits/doors/holds |
| `/app/yard/out/moves.jsonl` | published move extract |
| `/app/yard/out/detention.jsonl` | published detention ledger |
| `/app/yard/out/rejects.jsonl` | parsed-but-rejected commands |
| `/app/yard/out/health.json` | occupancy digest vs views |

Later `task.toml` `artifacts` should list the published outputs the verifier reads (absolute paths). Parent dirs created in the **verifier** image. Do not nest `artifacts` under `[verifier]`.

Suggested artifact set (A7/Q7 will freeze the names that `instruction.md` also cites):

```text
/app/yard/out/snapshot.json
/app/yard/out/moves.jsonl
/app/yard/out/detention.jsonl
/app/yard/out/rejects.jsonl
/app/yard/out/health.json
```

Live journal/sqlite are also native state; if the verifier must see them after Harbor copy, they must be named in `artifacts` too. Decision deferred to A7 so instruction and `task.toml` stay aligned. Architecture assumes the verifier will need **both** published files and `/app/yard/var` if restart/replay is graded on live state.

---

## DATA_VOLUME_PLAN

Primary business records: **visits** in live sqlite, target **12,600** (inside 10k–20k). Deterministic, varied. Not 12,600 copies of one row.

| Dimension | Plan |
| --- | --- |
| Facility | `DC-AUR-01`, `yard_tz = America/Chicago` |
| Horizon | 14 operating days, `2026-03-02` through `2026-03-15` (fixed; seed does not use `now`) |
| Doors | 48 (32 DRY inbound live, 8 REEFER, 8 OUTBOUND) |
| Spots | 720 (400 DROP_LOT, 200 STAGING, 48 DOCK_APRON, 72 CHASSIS_STACK) |
| Carriers | 72 SCACs with distinct free-time rows |
| Visits | 12,600 (~900/day): 40% LIVE_IN, 25% DROP_IN, 20% LIVE_OUT, 10% EMPTY_OUT, 5% LOADED_PICKUP |
| Appointments | ~13,200 including no-shows that never became visits |
| Open at image start | ~100 open visits mixed ON_YARD / DOCKED / MOVING, plus leftover SCHEDULED appointments |
| Moves | derived, ~1.6 completed moves per closed visit on average (journal history, not a second primary count) |
| Holds | subset of visits with each of the four codes; mix of released and still-open |

Variation that must affect reasoning: SCAC, visit_type, equipment, door_class, seal present/absent on loaded moves, hold class, early/on-time/late-within-grace timestamps, DST-adjacent local times during the March 2026 US DST change (2026-03-08) so timezone math is not a constant offset.

Seed is deterministic from a fixed seed integer in `yard.json`. Warehouse `prior_cycle.sqlite` holds an older closed cycle (~4k visits) that must remain unused by live publish.

Do not count seed generator LOC or warehouse dumps toward the 3,000 floor.

---

## Published snapshot schema (clean contract)

`/app/yard/out/snapshot.json` object, keys in this order:

```text
facility_id: string
generated_at: string (UTC instant, trailing Z)
yard_tz: "America/Chicago"
as_of: string (UTC instant used for occupancy)
open_visits: array of visit objects sorted by visit_id
occupancy: array of {spot_id, zone, visit_id} sorted by spot_id
doors: array of {door_id, door_class, visit_id or null} sorted by door_id
in_transit: array of {move_id, visit_id, origin_spot_id, dest_spot_id} sorted by move_id
holds: array of {visit_id, hold_code, placed_at} active holds only, sorted by visit_id, hold_code
counts: {open_visits, occupied_spots, doors_occupied, in_transit, active_holds}
```

Visit object fields (order): `visit_id`, `scac`, `trailer_number`, `visit_type`, `equipment`, `state`, `spot_id` (null if MOVING), `door_id` (null if not DOCKED), `gate_in`, `appointment_id`, `seal`.

Detention JSONL row fields (order): `visit_id`, `scac`, `visit_type`, `clock_start`, `free_minutes`, `pause_minutes`, `chargeable_minutes`, `status` (`OPEN` or `CLOSED`).

Moves JSONL row: one completed/cancelled/failed/in-flight move per line as defined in the contract; sorted by `seq` when published.

Health: `ok` bool; `applied_seq`; `journal_seq`; `occupancy_digest`; `open_visit_ids` sorted; `warehouse_untouched` bool.

Exact field types and ISO formatting belong in `yard-contract.md` at materialization, matching this architecture.

---

## Reachability plan

Every package above is imported from `yardctl` or from replay that `yardctl` always runs on catch-up. No orphan library. `cmd/seed` is reachable from the image build (`RUN /app/yard/bin/seed`) and from an operator re-seed that the agent is **not** required to run (inherited state already exists).

SQL views are selected by `health` and `snapshot` reconciliation, so they are runtime-reachable.

---

## UNRESOLVED_RISKS

1. **Instruction budget.** Appointment TZ, detention clock, chassis, holds, and replay must all appear as *what* in ≤20 bullets. If A7 cannot state them without a walkthrough, shrink published schema comments into the contract, not into instruction — but do not hide material requirements in docs.
2. **Artifact copy.** Restart tests need live `/app/yard/var`. A7 must name every path Harbor copies. Under-declaring artifacts is a format defect, not extra difficulty.
3. **DST on 2026-03-08.** Seed must include visits whose local window crosses the US spring-forward; slim images need `tzdata`.
4. **Do not merge L5.** No customs/rail hold authority. Yard holds only.
5. **Python+SQL only.** Justified: the domain is yard operations, not language tooling. Do not add a second compiled language to imitate freight-triage.
6. **Seed vs runtime LOC.** Seed must not become the bulk of counted lines. Detention, moves, and appointment matching must be real code.
7. **A3 trap.** Do not pre-assign bugs to modules here. Topology is the next stage.

```text
STATUS: ARCHITECTURE_READY
COMPONENT_GRAPH: yardctl, journal, replay, identity, appointments, timeutil, gate, inventory, doors, chassis, moves, holds, detention, publish, policy, sql views, seed(build)
ENTRYPOINTS: /app/yard/bin/yardctl ; YARD_ROOT=/app/yard ; docs/yard-contract.md
STATE_MODEL: events.jsonl source of truth; sqlite derived; checkpoint fence; warehouse immutable and excluded from live occupancy
SOLVER_VISIBLE_DOC_PLAN: yard-contract.md, layout.md, schema.sql, yard.json, carrier_contracts.json
PRODUCTION_CHARACTERISTICS: differentiated modules, CLI, sqlite+jsonl, replay, fail-closed, idempotent event_id, coupled door/chassis/hold/detention
SCALE_FIT: PASS — 12,600 visits, 48 doors, 720 spots; 25–30 organic F2P surfaces; LOC floor met by runtime packages not seed
RESOURCE_GRAPH: var/{events.jsonl,yard.sqlite,checkpoint.json} config/* sql/schema.sql warehouse/prior_cycle.sqlite out/{snapshot,moves,detention,rejects,health}
DATA_VOLUME_PLAN: 12600 visits over 14 days at DC-AUR-01 America/Chicago including 2026-03-08 DST; ~100 open at start; 72 SCACs
UNRESOLVED_RISKS: instruction budget; artifact copy of var/; tzdata+DST; no L5 merge; keep seed LOC out of the floor
```
