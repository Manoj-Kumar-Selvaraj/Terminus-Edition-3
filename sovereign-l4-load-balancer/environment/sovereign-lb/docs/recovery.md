# Recovery

Durable objects are written to a temporary sibling, flushed, renamed, and followed by a directory sync. Generation directories contain canonical `snapshot.json`, `digest`, and `complete` marker. `CURRENT` is advisory until its generation content, marker, and digest verify.

On control-plane startup, scan complete generations, verify canonical digests, load durable desired revision and idempotency records, and reconcile the rollout journal. A missing, corrupt, or dangling `CURRENT` falls back to the highest verified generation that durable rollout state marks active. Incomplete directories never acquire authority.

Idempotency records bind key, request digest, accepted revision, generation, and response. Replay of the same key and body returns the recorded response. Reuse with different content is a conflict. The accepted revision fence is restored before serving mutation APIs.

Node session fences persist node identity, latest session identity, and acknowledgement sequence. Reconnection establishes a new session; it does not inherit prepared authority. A node may advertise a verified active checkpoint in `hello`, after which the coordinator reconciles rather than assuming it prepared pending work.

The dataplane checkpoint uses the same complete-generation layout. Startup verifies length, JSON shape, generation, and digest before publication. If no checkpoint verifies, the node starts unready with no listeners and reconnects to control authority.

Retention never removes a generation referenced by active runtime objects, prepared candidates, current or rollback pointers, or owned connections. Bounded history is pruned only after reference accounting proves it unreachable.