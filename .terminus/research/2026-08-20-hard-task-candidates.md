# Research: hard work-package candidates (unused taxonomy)

## CREATION_RULE_CONTEXT

Pinned in `2026-08-20-hard-task-rule-context.md` at control-plane commit `72c0df6ee13f275bfa7d9573bb90e6d5711123d7`. Profile: `large_system_strict`. Languages preference: python (+ sql when state-backed).

## Local inventory pressure

Software/Systems is heavily used (Terraform cutovers, JetStream, webhook outbox, event-time sessions, edge-router, etc.). Operations already has Logistics (`yard-gate-dock-dwell-control`), Supply chain, Finance, Claims, Compliance. Prefer **unused** category/subcategory pairs and topologies that are not reskins of yard occupancy, CDC catalogs, WAL storage, or payment EOD.

## Anti-reskin checklist

| Local task | Avoid collapsing into |
| --- | --- |
| yard-gate-dock-dwell-control | Spot occupancy / detention / gate windows |
| event-time-session-window-processor | Pure event-time session gaps |
| tenant-catalog-logical-cdc-plane | Catalog WAL/CDC/LSN fencing |
| stonevault-crash-safe-storage | Generic crash-safe KV |
| freight / depot / workshop | Ledger checksums / bay booking |
| claims-remittance / payment-eod / wire-dual-control | Claims or money movement desks |
| webhook-outbox-delivery-plane | Outbox delivery retries |

```text
STATUS: CANDIDATES_READY
CANDIDATES:

- ID: H1
  SLUG: entity-match-cutover-plane
  TAXONOMY: Software / Data engineering
  PERSONA: Data platform engineer finishing a customer master cutover so blocking, scoring, merge, and quarantine agree under restart.
  ENGINEERING_OBJECTIVE: Complete the inherited entity-resolution plane so source records resolve to one golden party with deterministic blocking, graded matches, merge provenance, and fail-closed quarantine.
  REQUIRED_END_STATE: Operator CLI publishes match-run report, golden party extract, quarantine ledger, and health with journal catch-up. Identical run_id+payload is idempotent; warehouse prior dump stays out of live goldens.
  REQUIREMENT_FAMILIES: blocking keys; match grades/thresholds; merge/supersede; quarantine codes; config-driven thresholds; journal/checkpoint restart; warehouse isolation; usage exit 2.
  INHERITED_SYSTEM_STATE: 12k–16k party/source records across sources and address/phone/email variants; live sqlite + events.jsonl; prior warehouse dump.
  REASONING_CHAIN: normalize -> block -> score -> grade -> merge or quarantine -> publish; wrong block key silently under-matches; wrong merge order corrupts golden lineage.
  PARTIAL_FIX_TRAPS: fixing score without blocking still misses true pairs; fixing merge without quarantine still promotes conflicts; fixing publish without warehouse fence still mixes prior-cycle goldens.
  PRESERVATION_OBLIGATIONS: keep CLI verbs, party IDs, and published schemas; do not wipe inherited source dump.
  SCALE_FIT: PASS — natural modules (normalize, block, score, merge, quarantine, journal, publish) support >=3k LOC and 25–30 organic F2P.
  EDGE_FAILURE_SURFACE: empty block, threshold boundary, duplicate source_id, conflicting merge, restart mid-merge, usage no-touch, config mutation changes grades.
  INSTRUCTION_FIT: PASS — one cutover request; schemas in binding contract.
  DUPLICATE_RISK: LOW vs local inventory (no CDC/WAL catalog twin).

- ID: H2
  SLUG: host-timeline-forensics-desk
  TAXONOMY: Security / Forensics
  PERSONA: IR analyst completing a host timeline desk so evidence ingest, ordering, hash continuity, and case publish stay sound after a bounce.
  ENGINEERING_OBJECTIVE: Finish the inherited forensics control plane so multi-source artifacts land in a single case timeline with civil-time ordering, hash/chain continuity, hold codes, and restart-safe case state.
  REQUIRED_END_STATE: casectl publishes timeline.jsonl, chain-of-custody, rejects, and health. Tear/kill mid-ingest either omits the event or completes it; warehouse prior case dump is never mixed into live cases.
  REQUIREMENT_FAMILIES: multi-source ingest; timezone/DST ordering; hash chain; evidence holds; idempotent event_id; checkpoint replay; warehouse isolation; usage fence.
  INHERITED_SYSTEM_STATE: 10k+ artifact/event rows across sources; live journal/sqlite; prior closed-case warehouse.
  REASONING_CHAIN: parse artifact -> validate hash -> place on timeline -> honor holds -> publish; DST/offset bugs shuffle causality; broken chain fails closed.
  PARTIAL_FIX_TRAPS: sorting UTC strings without zoneinfo still misorders DST windows; hashing files without chain links still accepts spliced histories; publish without warehouse fence mixes closed cases.
  PRESERVATION_OBLIGATIONS: keep case IDs and public CLI; leave warehouse prior cases untouched.
  SCALE_FIT: PASS — ingest/timeline/custody/holds/journal/publish modules; organic F2P from ordering, chain, holds, restart.
  EDGE_FAILURE_SURFACE: torn journal line, hash mismatch, hold blocks export, duplicate event_id conflict, empty case, grace/DST edge.
  INSTRUCTION_FIT: PASS.
  DUPLICATE_RISK: LOW (Security/Forensics unused locally).

- ID: H3
  SLUG: ad-spend-attribution-reconcile
  TAXONOMY: Operations / Marketing
  PERSONA: Growth ops completing attribution reconcile so clicks, conversions, and spend caps agree across TZ and fraud holds.
  ENGINEERING_OBJECTIVE: Complete the attribution desk so click→conversion windows, multi-touch rules, currency/TZ, fraud holds, and spend caps produce a consistent ledger after restart.
  REQUIRED_END_STATE: attrctl publishes attribution.jsonl, spend summary, rejects, and health; warehouse prior campaign dump excluded; usage errors touch nothing.
  REQUIREMENT_FAMILIES: attribution windows; touch models; spend caps; fraud holds; TZ/DST; journal catch-up; warehouse isolation.
  INHERITED_SYSTEM_STATE: 12k+ click/conversion/spend rows; contracts per campaign; live journal.
  REASONING_CHAIN: click time -> window -> eligible conversions -> touch weights -> spend cap -> hold/release; wrong TZ bills the wrong day; holds must pause chargeable spend.
  PARTIAL_FIX_TRAPS: fixing window without touch model still double-counts; fixing spend without holds still books fraud clicks; publish without warehouse fence mixes prior campaigns.
  PRESERVATION_OBLIGATIONS: keep campaign IDs and public schemas.
  SCALE_FIT: PASS.
  EDGE_FAILURE_SURFACE: zero-window, late conversion, currency mismatch, hold blocks, idempotent click_id, config grace mutation.
  INSTRUCTION_FIT: PASS — Marketing subcategory unused.
  DUPLICATE_RISK: MEDIUM if it drifts into generic event-time session windows (must stay attribution/spend specific).

- ID: H4
  SLUG: serving-drift-canary-gate
  TAXONOMY: ML / Inference
  PERSONA: ML platform engineer finishing serving-side drift gating so metrics journals, baselines, and canary promote/abort stay consistent.
  ENGINEERING_OBJECTIVE: Complete the inference monitoring plane so feature/score drift stats, baseline fences, canary promote/abort, and alert journals agree under restart without GPU work.
  REQUIRED_END_STATE: driftctl publishes drift report, canary decision, alert journal, and health; warehouse prior metrics dump excluded.
  REQUIREMENT_FAMILIES: windowed stats; baseline fences; canary thresholds; alert dedupe; journal catch-up; config-driven thresholds; warehouse isolation.
  INHERITED_SYSTEM_STATE: 10k+ scored request metric rows; baseline snapshots; live journal.
  REASONING_CHAIN: ingest metrics -> window aggregate -> compare baseline -> canary gate -> alert; wrong window or baseline mix yields false promote.
  PARTIAL_FIX_TRAPS: fixing PSI without baseline fence still promotes on stale baselines; alerts without dedupe spam; warehouse mix corrupts live drift.
  PRESERVATION_OBLIGATIONS: keep model/version IDs and CLI.
  SCALE_FIT: PASS if stats/canary/alert modules stay substantive (no GPU kernels).
  EDGE_FAILURE_SURFACE: empty window, threshold boundary, duplicate alert_id, restart mid-promote, usage fence.
  INSTRUCTION_FIT: PASS.
  DUPLICATE_RISK: LOW locally; keep CPU-only authenticity.

- ID: H5
  SLUG: hydrograph-stage-forecast-desk
  TAXONOMY: Science / Earth
  PERSONA: Hydrology ops completing a stage-forecast desk so observations, rating curves, and forecast publish stay physically consistent.
  ENGINEERING_OBJECTIVE: Finish the inherited hydro desk so gage observations convert through rating curves with TZ, QC holds, and restart-safe forecast artifacts.
  REQUIRED_END_STATE: hydroctl publishes stage/flow series, QC rejects, forecast package, and health; prior warehouse season excluded from live publish.
  REQUIREMENT_FAMILIES: rating curves; QC flags/holds; TZ/DST; forecast horizons; journal catch-up; warehouse isolation.
  INHERITED_SYSTEM_STATE: 12k+ gage observations; curve segments; live journal.
  REASONING_CHAIN: observe -> QC -> rating lookup -> stage/flow -> forecast window -> publish; wrong curve segment or TZ corrupts peaks.
  PARTIAL_FIX_TRAPS: linear interp without segment bounds still extrapolates illegally; QC without holds still exports bad peaks.
  PRESERVATION_OBLIGATIONS: keep site IDs and public schemas.
  SCALE_FIT: PASS with care — must stay operational hydro desk, not a physics textbook dump.
  EDGE_FAILURE_SURFACE: out-of-range stage, missing curve, DST spring-forward gap, hold blocks export.
  INSTRUCTION_FIT: MEDIUM — keep formulas in contract, not instruction walkthrough.
  DUPLICATE_RISK: LOW (Science/Earth unused).

RECOMMENDATION: H1 (entity-match-cutover-plane) — strongest unused taxonomy (Data engineering), clear organic F2P surface, natural 10k+ record seed, low reskin risk vs yard/CDC/WAL/payment tasks.
ALTERNATE: H2 if Security/Forensics is preferred.
```
