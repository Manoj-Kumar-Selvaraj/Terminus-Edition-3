# Rollout state

A rollout is identified by generation and digest and has one of `preparing`, `activating`, `active`, `rejected`, or `aborted`. The durable record includes source revision, candidate digest, phase deadline, required quorum, current-session responses, and the preceding active generation.

Prepare responses count only when node ID, session ID, monotonically increasing sequence, generation, and digest all match current authority. Disconnected sessions and sessions superseded by a later `hello` do not count. Reconnect does not imply preparation.

Activation is sent only after prepare quorum. It is sent only to a session that prepared the candidate. `active` responses are fenced by the same identity tuple. Repeated matching responses are idempotent; conflicting replay is rejected.

A rejection or deadline leaves the preceding active generation untouched. A later apply may create a new generation, but cannot reuse the failed generation number. Rollout history is bounded while retaining any generation referenced by active connections, checkpoints, or rollback authority.

Readiness is true only when the node has completed listener publication for the generation it reports active. Control-plane readiness additionally requires durable repository access and a coherent active rollout pointer.