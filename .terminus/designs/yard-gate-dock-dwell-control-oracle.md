# REFERENCE_SOLUTION — yard-gate-dock-dwell-control

```text
STATUS: IMPLEMENTED
RESTORED_INVARIANTS:
- America/Chicago windows + grace + DST via zoneinfo
- live clock_start = max(window_start_utc, gate_in); whole-minute detention; YARD holds pause, carrier holds do not
- exclusive occupancy + IN_TRANSIT vacancy + dest reservation; confirm/cancel occupancy
- door plug/live/drop/equipment; chassis required for grounded drops; exclusive mount; on_ground cleared
- all holds block gate-out; release-hold clears the named row
- scac+trailer open uniqueness; loaded seal; CONTRACT_MISSING; pool appointments SCAC-only
- usage exit 2 before journal/sqlite/out writes; event_id payload fence; journal append then sqlite commit
- replay applies only seq > applied/checkpoint fence
- publish/detention/health ignore warehouse; health.ok is computed
FILES_CHANGED: solution/solve.sh + solution/fixed/*.py copied onto /app/yard/yard at oracle time
RESTART/IDEMPOTENCY_BEHAVIOR: identical event_id+payload replays stored result; conflict rejects; catch-up is incremental
DETERMINISM_NOTES: no wall clock; as_of from flag or journal head; seed integer unchanged
PRESERVED_BEHAVIOR: public CLI verbs, schemas, inherited visit IDs, warehouse file bytes, seed generator
RISKS_FOR_INDEPENDENT_VERIFIER: CLAIMED appointments are not reusable (OPEN only); DROP_IN on apron is DOOR_CLASS; health digest is sqlite occupancy after catch-up
```
