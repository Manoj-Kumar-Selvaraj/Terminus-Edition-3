# ENVIRONMENT_BUILD — yard-gate-dock-dwell-control

```text
STATUS: BUILT
COMPONENT_GRAPH: yardctl, journal, replay, identity, appointments, timeutil, gate, inventory, doors, chassis, moves, holds, detention, publish, policy, engine, sql views, seed(build)
ENTRYPOINTS: /app/yard/bin/yardctl ; YARD_ROOT=/app/yard
SOLVER_VISIBLE_DOCS: docs/yard-contract.md, docs/layout.md, sql/schema.sql, config/yard.json, config/carrier_contracts.json, logs/gate-desk.log, ops/handoff.txt
INSTRUCTION_DOC_BOUNDARY: contract owns CLI/state/clock/schemas; instruction (later) owns the work request. Docs do not name patch locations or defect ids.
SUBSTANTIVE_LOC: validator-visible environment ~3100 including seed.py and carrier_contracts.json; runtime packages are the operator path. Seed/warehouse dumps are data. Deepen runtime before Q6 if the auditor excludes seed/JSON.
PRODUCTION_CHARACTERISTICS: CLI, sqlite+jsonl, checkpoint, 12600 visits, 72 SCACs, 48 doors, 720 spots, warehouse prior cycle, fail-closed reject vocabulary (partially unimplemented)
RESOURCE_COUNT: journal, sqlite, checkpoint, warehouse, five out files, two configs, schema, contract, shift log, handoff
RUNTIME_REACHABILITY_NOTES: all yard.* packages import from yardctl/engine/replay/publish. cmd/seed.py does not import defective gate/timeutil.
ENVIRONMENT_RULE_CHECKS: digest-pinned python 3.13 slim; tmux+asciinema+tzdata; .dockerignore; no solution/tests COPY; seed at image build
UNRESOLVED_RISKS: instruction.md not written (A7); artifacts include /app/yard/var; Q6 may exclude seed.py (~494) and carrier_contracts.json (~506) leaving runtime under 3000 — deepen domain modules at next env repair if needed; first mutating yardctl replays the full journal (D22)
```

Injected only the approved A3 clusters. No Oracle. No tests.
