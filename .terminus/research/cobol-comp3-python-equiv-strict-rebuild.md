# Scenario research — strict warehouse inventory cutover

Profile: `large_system_strict`

The selected work package is a warehouse inventory cutover from a legacy COBOL packed-decimal movement feed to a restartable Python runtime. It was selected because the production responsibilities are naturally coupled: COBOL storage semantics determine record framing; framing feeds policy and weighted-cost accounting; durable effects constrain checkpoint/replay behavior; reconciliation controls authorize publication.

The scenario intentionally treats Python equivalence as one subsystem of the migration rather than the entire task. The inherited environment includes a 15,000-row historical state surface, operational log/handoff evidence, dynamic ODO/REDEFINES layout behavior, SQLite durability, reporting and publication.

Scale is architectural rather than padded: the recovered environment measures 3,023 substantive lines under the repository's counting rules before tests, solution and documentation are considered.

Primary calibration used IBM Enterprise COBOL concepts for packed decimal representation, OCCURS DEPENDING ON / REDEFINES storage behavior, and checkpoint/restart operational semantics.

Acceptance intent:
- 3,000+ substantive reachable solver-visible LOC;
- 20–30 genuine defect manifestations with a cross-component causal graph;
- 25–30 organic F2P tests;
- real state/restart/reconciliation/publication behavior;
- no profile downgrade or numeric padding.
