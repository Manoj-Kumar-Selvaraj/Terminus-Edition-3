# Observability

Management readiness is exposed as JSON and returns false when durable state is unavailable or active rollout authority is incoherent. Dataplane readiness returns false until active listeners correspond to the reported active generation and returns false before graceful shutdown stops accepts.

Status views expose bounded summaries: desired revision, active and candidate generation, rollout phase and quorum counts, current node sessions, listener count, target health counts, connection count, draining count, and last durable transition time. Detailed connection views are capped and omit payload and raw source identity.

Metrics use stable names and low-cardinality labels. Allowed labels are operation, result, message type, listener name from bounded configuration, zone from bounded inventory, and reason code from a fixed set. Generation, digest, session ID, source address, target address, and connection ID are values in status where needed, not metric labels.

Control-plane counters cover apply outcomes, protocol frames, session replacement, prepare and activate outcomes, persistence errors, health transitions, and audit drops. Gauges cover connected current sessions, rollout quorum progress, retained generations, and bounded queue utilization.

Dataplane counters cover accepts, connect outcomes, bytes by direction, close reasons, PROXY header outcomes, health probes, passive failures, and checkpoint outcomes. Gauges cover active connections, buffer bytes, eligible targets, draining targets, and active listeners.

The audit ring records timestamp, actor class, operation, request digest prefix, revision, generation, outcome, and fixed reason. It has fixed capacity and an explicit dropped-event counter. It never records traffic bytes, full client addresses, or arbitrary request bodies.