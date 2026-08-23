# Persistence and Recovery Contract

State snapshots live in monotonic generation directories with a canonical manifest and content digests. `CURRENT` contains one generation name and is trusted only after full verification. Recovery chooses the highest valid generation, not the newest timestamp, and safely falls back when `CURRENT` is torn, missing, or corrupt.

Jobs, shards, leases, worker sessions, checkpoints, accepted batch identities, finding lineage, report generations, policy pins, source fences, audit sequence, and retention leases are recovered together. A restart cannot revive expired authority or forget an accepted batch.

Retention keeps a bounded number of unreferenced generations. Active jobs, checkpoints, current and fallback state, report exports, and explicit retention leases protect their referenced generations. Cleanup publishes its own audited generation.