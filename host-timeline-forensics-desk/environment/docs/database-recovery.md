# Database and restart behavior

PostgreSQL is authoritative for plans, attempts, queue claims, leases, event inbox, accepted evidence metadata, custody events, case holds, export jobs, audit, and checkpoints. The filesystem stores only synthetic evidence objects and published exports; it is not an independent authority for case state.

A transaction owns one logical change to claim/attempt state, event consumption, evidence metadata, custody, audit, and progress checkpoint. Filesystem writes are staged and verified before database references or export pointers are committed. Restart recovers expired claims, reconciles lab-visible attempts, consumes accepted inbox records idempotently, and resumes staged publication from durable metadata.

Readiness is derived from database recovery, migrations, active claims, event backlog, worker heartbeat, reconciliation work, holds, and export/retention backlog. A live HTTP process alone does not make the service ready.
