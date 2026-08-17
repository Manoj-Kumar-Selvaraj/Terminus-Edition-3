# Research: Operations / Logistics work-package candidates

## CREATION_RULE_CONTEXT

```text
CONTROL_PLANE_COMMIT: 6e3944669a62da5c2a9ae9c6a2528e11b772ca86
RULE_SOURCES: TERMINUS_3_AI_INSTRUCTIONS.md; .terminus/AGENT_SYSTEM.md; .terminus/agents/CREATION_CONTROLLER.md; .terminus/agents/CREATION_PIPELINE.md; .terminus/agents/PRODUCTION_AUTHENTICITY.md; .terminus/reviewers/REVIEWER_CHECKLIST.md; .terminus/agents/STAGE_CONTRACTS.md
ACTIVE_VALIDATORS: validate_task_complexity.py; validate_runtime_authenticity.py; ruff; Harbor oracle/nop
CREATION_PROFILE: large_system_strict
NETWORK_ENVIRONMENT_CONSTRAINTS: public network; separate verifier; digest-pinned canonical Python unless another base is justified; tmux+asciinema in agent image
KNOWN_POLICY_CONFLICTS: none
REQUESTED_DOMAIN: Operations / Logistics
```

Learned work *shapes* from public YMS/air-cargo operations writing (gate→yard→dock, dwell/detention, ULD/cutoff). Do not copy that prose into instruction.md.

## Local inventory to avoid

| Task | Tag | Why not a reskin |
| --- | --- | --- |
| freight-triage-polyglot-ledger-recovery | Software/Systems | Polyglot checksum/epoch/ledger agreement, not dispatch |
| depot-transfer-ledger | Software/Languages | COBOL stock/transit receipts and voids |
| workshop-slot-transaction-control | Operations/Supply chain | Bay/technician booking + Postgres concurrency |
| claims-remittance-auth-desk | Operations/Claims | Claims adjudication |
| hris-midcycle-payroll-close | Operations/Compliance | Payroll close |
| wire-dual-control-release-desk | Operations/Finance | Dual-control money movement |

```text
STATUS: CANDIDATES_READY
CANDIDATES:
- ID: L1
  PERSONA: DC yard control / gate lead completing a live YMS cutover so gate, yard inventory, dock doors, jockey moves, and detention clocks agree.
  ENGINEERING_OBJECTIVE: Finish the inherited yard control plane so every trailer is accounted from gate-in through dock spot to gate-out, with appointment windows, door constraints, chassis pairing, and dwell/detention evidence.
  REQUIRED_END_STATE: Operator CLI publishes a consistent yard snapshot, move journal, dock occupancy, and detention ledger. Restart does not invent or drop trailers. Gate events that miss appointments or seals fail closed.
  REQUIREMENT_FAMILIES: gate identity/appointment; yard slot occupancy; door class/temp/equipment fit; jockey move dispatch and confirm; dwell vs detention thresholds; hold/release; seal/chain-of-custody; restart/idempotent replay.
  INHERITED_SYSTEM_STATE: 12k–16k trailer/visit/move records across carriers, doors, and drops; live sqlite/jsonl journals; appointment book; chassis pool.
  REASONING_CHAIN: appointment validity -> gate timestamp -> slot assignment -> door eligibility -> move confirmation -> dwell clock -> detention vs free time; a wrong key or clock order corrupts occupancy and charges.
  PARTIAL_FIX_TRAPS: fixing gate-in without door class still spots reefers on dry doors; fixing occupancy without chassis pairing still dispatches undroppable moves; fixing dwell without appointment timezone still bills the wrong free-time window.
  PRESERVATION_OBLIGATIONS: keep public CLI, visit/move schemas, and historical visit IDs; do not wipe the inherited yard dump.
  SCALE_FIT: PASS — natural modules (gate, inventory, doors, moves, detention, holds) exceed 3k LOC; 25–30 F2P from states/transitions without stacking unrelated products.
  EDGE_FAILURE_SURFACE: early/late arrival, duplicate SCAC+trailer, missing seal, overlapping door claims, empty yard, kill mid-move, replay same gate event, chassis already mounted, hold blocks gate-out.
  INSTRUCTION_FIT: PASS — one work request, <=20 bullets: CLI, contract, fail-closed gate, occupancy, door fit, moves, detention, restart, leave warehouse dump.
  REFERENCES: public YMS gate-in/gate-out and dock-vs-yard distinction (work shape only).
  DUPLICATE_RISK: LOW vs local inventory. Not a freight checksum task and not workshop bay booking.

- ID: L2
  PERSONA: Linehaul operations completing relay-point dispatch so trailers, drivers, and HOS clocks stay legal across a bounce.
  ENGINEERING_OBJECTIVE: Complete relay planning so each trailer has one legal driver segment, HOS remaining, tractor pairing, and late-relay cascade that does not double-assign a driver.
  REQUIRED_END_STATE: Dispatch board, relay manifest, HOS remaining file, and exception list reconcile after restart.
  REQUIREMENT_FAMILIES: relay graph; HOS remaining; tractor/trailer pairing; late arrival cascade; team vs solo; restart fencing.
  INHERITED_SYSTEM_STATE: 10k+ segment/driver/trailer rows; HOS clocks; relay yards.
  REASONING_CHAIN: remaining HOS -> legal next relay -> trailer wait -> downstream cascade.
  PARTIAL_FIX_TRAPS: legal HOS on one segment still double-books a driver on the next relay; pairing tractors without trailer dwell still strands freight.
  PRESERVATION_OBLIGATIONS: keep driver IDs and published relay schema.
  SCALE_FIT: PASS but higher legal-model risk (HOS rules are easy to underspecify or over-copy from FMCSA text).
  EDGE_FAILURE_SURFACE: zero remaining HOS, split sleeper, missed relay, duplicate driver IDs.
  INSTRUCTION_FIT: MEDIUM — HOS edge cases can blow the 20-bullet budget or hide in docs.
  REFERENCES: linehaul relay / HOS operations shape.
  DUPLICATE_RISK: MEDIUM if it collapses into generic scheduling like workshop-slot.

- ID: L3
  PERSONA: Origin cargo close lead finishing ULD build and flight close so AWB pieces, ULD tags, cutoffs, and weight/balance agree.
  ENGINEERING_OBJECTIVE: Complete flight close: piece tender, screening/cutoff, ULD assignment under MGW/contour, split AWB, manifest freeze.
  REQUIRED_END_STATE: Closed flight manifest, ULD tags, leftover/rollover list, and AWB piece reconciliation; freeze after cutoff.
  REQUIREMENT_FAMILIES: cutoff classes; ULD MGW/tare/gross; piece-count vs weight; split shipments; DG exclusion; restart after partial build.
  INHERITED_SYSTEM_STATE: 10k+ AWB/piece/ULD rows; flight schedule; cutoff table.
  REASONING_CHAIN: tender time vs cutoff -> ULD eligibility -> gross vs MGW -> AWB piece remainder -> freeze.
  PARTIAL_FIX_TRAPS: assigning ULDs without cutoff still loads late cargo; matching weights without piece counts still splits AWBs wrong.
  PRESERVATION_OBLIGATIONS: keep ULD IDs and AWB numbers; no post-freeze silent rewrite.
  SCALE_FIT: PASS — rich, but IATA contour/DG can become trivia or prompt overflow.
  EDGE_FAILURE_SURFACE: miss cutoff, overweight ULD, split remainder, empty ULD, freeze then late piece.
  INSTRUCTION_FIT: MEDIUM — must keep safety rules in the contract without dumping ULDR.
  REFERENCES: air-cargo cutoff / ULD build-up work shape.
  DUPLICATE_RISK: LOW locally; watch against becoming a packing-optimization puzzle.

- ID: L4
  PERSONA: Last-mile hub supervisor closing a delivery wave: stops, van cube, failed-delivery returns, and next-wave leftover.
  ENGINEERING_OBJECTIVE: Close the wave so every parcel is delivered, returned, or explicitly leftover; cube/weight caps and stop sequence constraints hold.
  REQUIRED_END_STATE: Wave close report, van load list, failed-delivery returns, leftover for next wave; idempotent re-close.
  REQUIREMENT_FAMILIES: stop sequence; cube/weight; failed delivery codes; return-to-depot; wave freeze; restart.
  INHERITED_SYSTEM_STATE: 12k parcels across routes/waves.
  REASONING_CHAIN: stop order -> capacity -> attempt outcome -> return vs leftover.
  PARTIAL_FIX_TRAPS: sequencing without cube still overloads vans; returns without wave freeze still reappear as deliveries.
  PRESERVATION_OBLIGATIONS: keep parcel IDs and public wave schema.
  SCALE_FIT: BORDERLINE — can look like a TSP toy unless returns/freeze/capacity stay coupled.
  EDGE_FAILURE_SURFACE: empty wave, oversized piece, duplicate scan, mid-wave crash.
  INSTRUCTION_FIT: PASS if we refuse to grade optimal routing and only grade constraint-legal close.
  REFERENCES: hub wave close / failed-delivery operations.
  DUPLICATE_RISK: MEDIUM vs generic routing puzzles; must not grade shortest-path.

- ID: L5
  PERSONA: Intermodal ramp clerk completing container holds: rail cutoff, customs hold vs logistics release, chassis availability, and gate-out.
  ENGINEERING_OBJECTIVE: Release only containers that clear rail cutoff, hold codes, and chassis pairing; publish ramp inventory and exceptions.
  REQUIRED_END_STATE: Ramp inventory, hold register, chassis assignments, gate-out journal; restart-safe.
  REQUIREMENT_FAMILIES: rail cutoff; hold codes; chassis pool; dual-authority release; dwell.
  INHERITED_SYSTEM_STATE: 10k+ container/visit rows.
  REASONING_CHAIN: cutoff -> hold -> chassis -> gate-out; customs hold must beat logistics desire.
  PARTIAL_FIX_TRAPS: chassis pairing without hold still gates a seized box; cutoff without timezone still loads late rail.
  PRESERVATION_OBLIGATIONS: keep container IDs and hold-code enum.
  SCALE_FIT: PASS, but overlap with L1 (yard/gate/chassis) is real — pick one, do not merge.
  EDGE_FAILURE_SURFACE: dual holds, missing chassis, late rail, empty ramp.
  INSTRUCTION_FIT: PASS.
  REFERENCES: ramp/hold/release operations shape.
  DUPLICATE_RISK: HIGH vs L1 if both are built; choose L1 or L5.

RECOMMENDATION: L1
SELECTED: L1 (user 2026-08-17)
SLUG: yard-gate-dock-dwell-control
ARCHITECTURE: `.terminus/designs/yard-gate-dock-dwell-control-architecture.md` STATUS ARCHITECTURE_READY
WHY_THIS_ONE: Unused Operations/Logistics pair; coherent production work package (gate, occupancy, doors, moves, detention) with organic 25–30 F2P; 10k+ varied visits; not a checksum ledger, not COBOL stock, not workshop booking. L3 is the runner-up if we want air cargo instead of yard. Do not combine L1+L5.
```
