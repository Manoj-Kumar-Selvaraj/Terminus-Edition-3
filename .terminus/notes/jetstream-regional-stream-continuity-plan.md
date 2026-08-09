# JetStream regional continuity creation note

Controller state: IDEA -> RESEARCHING

This task is being authored under the current Terminus Edition 3 creator workflow with profile `large_system_strict`.

Target system: two intermittently connected edge JetStream domains feeding a central archive domain. The task will exercise real JetStream stream/source/consumer behavior plus a durable application-side event journal, checkpoint store, replay planner, reconciliation engine, retention controller and operator control plane.

Creation goals:
- more than 3,000 substantive solver-visible runtime/configuration LOC with all major modules reachable;
- 10,000-20,000 deterministic varied event-journal records;
- 20-30 observable manifestations from materially fewer root causes, with at least 15 connected;
- 25-30 independent F2P behavioral verifier cases plus P2P where preservation risk warrants it;
- solver-visible incident logs plus an independent shift handoff/state artifact;
- no benchmark framing, no generated-code padding, no hidden-test leakage.

External technical grounding used for scenario design comes from current official NATS documentation for JetStream sources/mirrors, domains/leaf nodes, deduplication, consumers and stream retention. These references are calibration/evidence, not task authority.
