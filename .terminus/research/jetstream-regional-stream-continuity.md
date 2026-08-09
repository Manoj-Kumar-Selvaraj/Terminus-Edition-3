# Scenario research — jetstream-regional-stream-continuity

Creation profile: `large_system_strict`

## Public technical grounding

Primary calibration sources are current official NATS documentation and release material:

- JetStream sources and mirrors: https://docs.nats.io/nats-concepts/jetstream/source_and_mirror
- JetStream streams / retention / deduplication: https://docs.nats.io/nats-concepts/jetstream/streams
- JetStream consumers / acknowledgements: https://docs.nats.io/nats-concepts/jetstream/consumers
- Leaf-node JetStream domains: https://docs.nats.io/running-a-nats-service/configuration/leafnodes/jetstream_leafnodes
- NATS server releases: https://github.com/nats-io/nats-server/releases

The task does not copy wording, topology, tests or solution shape from those sources. They establish real platform semantics: sourced replication is asynchronous, stream sequence spaces remain stream-local, duplicate tracking is windowed, consumer ack state is durable evidence, and JetStream domain/leaf topology affects source routing.

## Candidates considered

### JS-A — delayed replay after regional carrier outage
Persona: streaming platform/SRE operator.
Normal workflow: edge domains accept telemetry locally; hub sources edge origins; required durable consumers apply archive effects.
Observed incident: carrier reconnect restores transport but journal/archive membership and consumer checkpoints remain inconsistent; delayed retries create duplicate effects.
Durable state: edge journal, stream origin generation, hub archive index, effect ledger, consumer checkpoints, replay plans, retention watermark.
Reasoning chain: event identity -> publish acknowledgement -> source topology -> archive identity -> consumer effect/checkpoint -> replay -> retention/fencing.
Partial-fix traps: larger duplicate window; reset checkpoint; replay full range; increase retention age; trust aggregate hub sequence.
Scale fit: strong. Natural 12k-event state, 7 root-cause clusters, 26 manifestations and 28 distinct behavioral F2P cases.
Duplicate risk: low in local repository; no existing NATS/JetStream task found.

### JS-B — WorkQueue source loss across intermittently connected leaf domains
Persona: job-processing platform owner.
Observed incident: edge WorkQueue retention deletes jobs after local consumption while a remote sourced copy is unavailable, causing irrecoverable central audit gaps.
Reasoning chain: retention ownership -> consumer interest -> leaf reachability -> source replication -> replay authority.
Partial-fix traps: adding consumers or extending ack wait changes local behavior but does not create robust multi-domain authority.
Scale fit: medium. Platform semantics are interesting but the incident tends to collapse around one retention limitation; reaching strict 20-30 manifestations risks padding.
Duplicate risk: low.
Disposition: rejected as too narrow for strict profile.

### JS-C — stream recreation behind remembered source sequence
Persona: regional platform engineer after storage repair.
Observed incident: one edge stream is recreated at low sequence while the hub source target remembers old progress, so new events never appear centrally.
Reasoning chain: stream incarnation -> source sequence memory -> consumer state -> reconciliation.
Partial-fix traps: reset source, manually copy records, or reset all checkpoints.
Scale fit: medium-high but still centered too heavily on one origin-recreation mechanism.
Duplicate risk: low.
Disposition: retained as one root-cause cluster inside JS-A rather than inflated into a whole strict task.

### JS-D — hub raw subject contamination by local derived writes
Persona: data-platform operator.
Observed incident: workers accidentally republish transformed records into the same raw archive subject family, creating loops and false reconciliation counts.
Reasoning chain: source subject transforms -> hub listen subjects -> derived routing -> consumer delivery -> archive membership.
Scale fit: medium; strong coupled symptom but insufficient breadth alone.
Disposition: incorporated into JS-A topology cluster.

## Recommendation

Use JS-A. It is one coherent regional continuity incident and naturally supports strict scale without combining unrelated technologies. JS-C and JS-D become causal subclusters that a real operator could encounter during the same reconnect/recovery path. The resulting task remains understandable as one question: whether accepted edge events can converge through archive, processing, replay and retention without loss or duplicate effects.
