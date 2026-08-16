The webhook outbox under `/app/outbox` is supposed to enqueue tenant events, claim them with lease fencing, deliver signed HTTP POSTs, honor quotas and pauses, and leave an audit trail. Behavior has drifted off the shipped contract — bring the API, CLI, and UI back in line without reshaping the public tree.

Treat `/app/outbox/docs/delivery-contract.md` as binding for routes, payloads, claim leases, HMAC headers, backoff/DLQ/replay, quotas, pause, audit, env vars, and how the UI talks to the API. Graded delivery is the claim→deliver path with `OUTBOX_SYNC=1` (API helpers); a background worker is optional for operators and is not a separate graded surface. After Go changes, rebuild so `/app/outbox/bin/outboxd` and `/app/outbox/bin/outboxctl` are the binaries you start.

- Wire startup through `OUTBOX_DB`, `OUTBOX_ADDR`, `OUTBOX_DATA`, `OUTBOX_TOKEN`, and `OUTBOX_SYNC` instead of hard-coding paths or ports.
- Apply `/app/outbox/db/schema.sql` on boot, keep schema plus seed tooling and the image-seeded default database under `/app/outbox/data` available for operators, and serve the static UI from `/app/outbox/ui` at `/`.
- Claim, delivery completion, pause, quota, signature canonicalization, DLQ replay auth, and audit must match the contract; concurrent second claims return 409; paused endpoints reject new claims.
- Keep UI forms on the contract field names and surface API errors instead of failing quietly. A fresh DB boot of the repaired binaries should satisfy the contract for API, CLI, and UI flows.
