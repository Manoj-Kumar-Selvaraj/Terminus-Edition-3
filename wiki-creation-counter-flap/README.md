# wiki-creation-counter-flap

Wikipedia-like users/posts API after a database flap. The scored problem is probe semantics versus durable creation counters across two replica processes — not a Kubernetes cutover and not a READY digest.

Operators repair `/app/wiki` and use `wikictl` to serve, flap, restore, and emit probe/reconcile reports. Verification repeats flap/restore against the submitted tree.
