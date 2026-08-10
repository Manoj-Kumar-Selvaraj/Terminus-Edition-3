# Scenario research — django-checkout-failover-ha

Creation profile: `large_system_strict`

Requested domain: Python Django, highly available checkout/storefront.

## Public technical grounding

Failure *shapes* (not copied wording, topology, or tests):

- Sticky-primary after writes so replica lag does not break read-your-writes (Django DB router + Redis pin; never store the pin on the replica itself).
- Replica `default_transaction_read_only` so stray writes fail loudly.
- Failover needs promote + traffic redirect + fence of the old primary; split-brain is the integrity failure, not the outage.
- Application reconnects, cache/session invalidation, and idempotent in-flight checkout/webhook retries after role switch.
- Liveness ≠ readiness: a gunicorn that is up can still be unsafe for writes.

Local inventory: no Django, Redis-session, or checkout-HA task exists. Nearest Edition 3 neighbors are `payment-eod-control-chain` (COBOL/DB2 batch integrity) and `jetstream-regional-stream-continuity` (NATS source/replay). This incident is application-tier HA routing + fencing, not batch close or stream archive.

## Candidates considered

### DJ-A — mid-cutover dual-AZ checkout after primary promotion
Persona: storefront platform/SRE for a Django order desk.
Normal workflow: place-order / pay / reload confirmation; reads scale on a streaming standby; sessions in Redis; fulfillment webhooks once per checkout attempt.
Observed incident: west AZ blip promoted the standby; AZ-B app nodes still prefer a writable old primary; some writes land on standby; confirmation reloads show unpaid carts; fulfillment fires twice.
Durable state: primary+standby order books, fencing lease/epoch, replica LSN watermark, Redis session pins, side-effect ledger.
Reasoning chain: write affinity → fence old primary → lag-gated reads → sticky pin independent of replica → exactly-once attempt effects → readiness distinct from liveness.
Partial-fix traps: point DATABASES['default'] at the new host but leave AZ-B router affinity; make standby writable “so checkout works”; store sticky flag in Django DB sessions; treat /healthz 200 as ready.
Scale fit: strong. 20k orders, 7 root-cause clusters, 26 manifestations, 28 F2P behaviors without unrelated products.
Duplicate risk: low.

### DJ-B — Celery beat split after dual-node enablement
Persona: async platform owner.
Observed incident: two beats enqueue the same periodic capture; inventory double-decrements.
Reasoning chain: leader election → beat lock → task idempotency.
Scale fit: medium. Collapses to one lock + one unique constraint; reaching 20–30 manifestations would require padding.
Disposition: reject as whole task; keep webhook/attempt idempotency as one cluster inside DJ-A.

### DJ-C — cache poisoning across failed-over Redis shard
Persona: session-platform engineer.
Observed incident: sessions pinned to a drained Redis replica; CSRF/auth flaps.
Scale fit: medium; strong cache semantics but thin DB/HA coupling unless combined with unrelated DB failover (forbidden merge).
Disposition: reject as standalone; Redis as session/pin store is a subcluster of DJ-A.

### DJ-D — migration lock left on demoted primary
Persona: release engineer during HA cutover.
Observed incident: `migrate` holds advisory lock on old primary; new primary schema drifts; half the nodes 500.
Scale fit: narrow (one lock + one schema version).
Disposition: reject; schema/role mismatch can appear as a readiness symptom in DJ-A, not a second incident.

### DJ-E — greenfield “make single-node Django HA”
Persona: developer asked to invent Patroni+k8s from a tutorial.
Observed incident: none — construction task.
Scale fit: fails authenticity (no durable incident, walkthrough-shaped).
Disposition: reject.

## Recommendation

Use DJ-A. One coherent checkout-HA incident after a real promotion. DJ-B/C/D become causal subclusters (duplicate effects, pin store, readiness/schema) rather than bolted-on products. STATUS: CANDIDATES_READY.
