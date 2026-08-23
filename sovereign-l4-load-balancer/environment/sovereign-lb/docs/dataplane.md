# Dataplane contract

The dataplane is an epoll-based TCP proxy. A listener accept captures a shared immutable runtime, listener definition, selected target incarnation, and connection identity. Publication of a later runtime does not alter those references.

Selection first computes eligibility from administrative state, draining, active health, passive ejection, and zone policy. Same-zone-preferred considers local eligible targets first and remote targets only when local policy permits fallback. Cross-zone considers all zones. Fail-open may include unhealthy or ejected targets but never administratively disabled, removed, or expired-drain targets.

Round robin advances independently per target group and runtime. Least connections compares counters scoped to target incarnation with canonical identity as tie-breaker. Source hash hashes the binary source address and group seed, then maps over canonical eligible identities.

Both directions use bounded buffers with explicit read and write offsets. EPOLLIN is disabled when its destination buffer is full and restored after progress. Partial reads and writes retain unsent bytes. EOF marks one direction read-closed; the peer receives `shutdown(SHUT_WR)` only after buffered bytes for that direction are flushed.

Connect timeout covers nonblocking backend establishment. Idle timeout applies only when neither socket nor buffered transfer makes progress; pending buffered bytes prevent teardown while writes continue making progress. Errors close both descriptors exactly once and release target ownership exactly once.

When enabled, one binary PROXY protocol v2 header precedes client payload on the backend stream. Reconnect creates a new backend attempt and header state; a single established backend never receives the header twice.

Draining removes a target from new selection immediately. Existing owners continue until normal completion or drain deadline. Runtime retirement waits for listener, connection, prepared-state, checkpoint, and rollback references to be released.

Active probes run outside proxy workers and publish bounded health transitions. Passive connect and stream failures update incarnation-scoped windows. Successful active recovery obeys configured thresholds before clearing ejection.