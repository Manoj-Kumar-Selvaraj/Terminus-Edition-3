# Yard control plane layout

All paths are under `/app/yard` unless noted. `YARD_ROOT` defaults to `/app/yard`.

| Path | Role |
| --- | --- |
| `bin/yardctl` | Operator CLI. Only mutation path. |
| `bin/seed` | Image-build / operator rematerialize. Inherited state already exists. |
| `config/yard.json` | Facility, timezone, grace, path map. |
| `config/carrier_contracts.json` | Free-time minutes keyed by `scac` then `visit_type`. |
| `docs/yard-contract.md` | Binding CLI, state, clock, reject, and publish rules. |
| `sql/schema.sql` | Sqlite tables and occupancy views. |
| `var/events.jsonl` | Accepted event journal. Source of truth. |
| `var/yard.sqlite` | Derived visits, spots, doors, appointments, holds, chassis, moves. |
| `var/checkpoint.json` | `last_applied_seq`, sorted `open_visit_ids`, occupancy digest. |
| `warehouse/prior_cycle.sqlite` | Immutable prior cycle. Do not mix into live occupancy or live detention. |
| `out/snapshot.json` | Published occupancy / doors / holds. |
| `out/moves.jsonl` | Published move extract. |
| `out/detention.jsonl` | Detention ledger. |
| `out/rejects.jsonl` | Parsed-but-rejected mutating commands. |
| `out/health.json` | Applied seq, digest, warehouse_untouched. |
| `logs/gate-desk.log` | Inherited shift log. |
| `ops/handoff.txt` | Inherited desk counts. |
