# Lifecycle Contract

Jobs move `PLANNED -> RUNNING -> FINALIZING -> COMPLETE`, with `CANCELLING -> CANCELLED` and `FAILED` terminal alternatives. Shards move `PENDING -> LEASED -> COMMITTING -> COMMITTED`; policy skips and terminal failures are explicit terminal states. Invalid transitions leave persisted state unchanged.

A lease is authoritative only for its tenant, job, shard, scan generation, source generation, policy digest, worker session, attempt, token, and unexpired deadline. Renewal preserves attempt and token and cannot revive expired or superseded authority. Expiry makes a shard reassignable with a higher attempt. Cancellation prevents new leases and commits that would complete the job.

Finalization requires every required shard to be committed, skipped by the pinned policy, or terminally failed under policy completion rules. Partial batches, active leases, and missing shards keep a report incomplete. Retried requests and reconnects are idempotent.