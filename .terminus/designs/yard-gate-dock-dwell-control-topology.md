# DEFECT_TOPOLOGY — yard-gate-dock-dwell-control

STATUS: DESIGN_READY

Private design against `.terminus/designs/yard-gate-dock-dwell-control-architecture.md`. Canonical graph: `yard-gate-dock-dwell-control.json`.

Do **not** materialize `yard-gate-dock-dwell-control/environment/` until ENVIRONMENT_BUILD. Do not write tests or Oracle from this file.

## Clusters (7) → manifestations (30)

| RC | Root | Manifestations |
| --- | --- | --- |
| RC_CIVIL_TIME | unused `yard_tz` / zoneinfo | D01 window as UTC, D02 grace unused, D03 DST fixed offset, D04 live clock_start=gate_in |
| RC_OCCUPANCY | no exclusive occupancy + no IN_TRANSIT vacancy/reservation | D05–D10 |
| RC_FIT | door flags and on-ground wheels not constraints | D11–D15 |
| RC_HOLD_PAUSE | holds recorded without class/release semantics | D16–D18, D30 |
| RC_JOURNAL | sqlite working copy; journal/event_id/checkpoint best-effort | D19–D23 |
| RC_IDENTITY | incomplete open key / seal / pool / contract | D24–D27 |
| RC_PUBLISH | reads every sqlite | D28–D29 |

≥15 manifestations sit on causal edges (see JSON). Cross-cluster examples: D01→D04→D17→D30 (time × detention × holds); D07→D16 (move × gate-out); D13→D15 (chassis require × mount); D22→D05 (replay × occupancy); D28→D29 (warehouse × health).

## Injection targets (starter runtime only)

| Package | Inject |
| --- | --- |
| `yard.timeutil` | naive UTC / fixed -06:00; do not call zoneinfo |
| `yard.appointments` | no grace; pool trailer match wrong |
| `yard.detention` | clock_start=gate_in for live; inverted pause map; non-whole minutes |
| `yard.inventory` | last-writer occupant; no dest reservation |
| `yard.moves` | occupy dest on dispatch; confirm/cancel occupancy wrong |
| `yard.doors` | eligibility true if door_id exists |
| `yard.chassis` | no CHASSIS_REQUIRED; mount does not exclusive-lock or clear on_ground |
| `yard.holds` | persist rows; release no-op |
| `yard.gate` | no hold check on out; no seal; trailer-only open key |
| `cli/yardctl` | open out/sqlite before argv complete; sqlite write before journal |
| `yard.journal` | append without event_id+payload fence |
| `yard.replay` | apply entire journal |
| `yard.publish` | UNION warehouse; health ok=true |
| `sql/schema.sql` | omit spot occupant unique; optional wrong unique(trailer_number) |

## Do not inject

- `cmd/seed` (clean inherited 12,600-visit state)
- warehouse file bytes (mix is a publish bug)
- correct `yard.json` tz/grace (must be present and unused)
- contract prose that names patch locations

Leave one SCAC out of `carrier_contracts.json` so CONTRACT_MISSING is reachable.

## Partial-fix traps (must survive A2)

1. Convert to Chicago but skip grace or DST.
2. Exclusive gate-in without dest reservation / IN_TRANSIT vacancy.
3. Require chassis but mount leaves `on_ground=true`, or require chassis on live tractors.
4. Block gate-out on holds while `release-hold` is a no-op.
5. Deduplicate `event_id` without payload hash; replay skip-by-visit_id still duplicates moves.
6. Drop warehouse from snapshot but not detention-run.
7. Pause every hold instead of YARD vs CARRIER classes.

## Organic F2P

SUFFICIENT without 1 defect = 1 test. Verifier later grades invariants (occupancy uniqueness, clock, reject codes, restart, warehouse isolation), not this id list.
