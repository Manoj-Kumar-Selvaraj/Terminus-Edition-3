# Operator contract

The service is an offline case-evidence acquisition desk. `casectl` manages case inspection, collection plans, status, holds, coverage, and deterministic export. The HTTP API exposes the same case-scoped operations for local automation. `forensic-worker` drains durable source requests; `collection-lab` is the only live-source target in the packaged environment. `offline-intake` accepts self-contained synthetic bundles without network access.

A case plan is immutable after submission. A new request that changes source, policy, inventory generation, or limits is a new plan identity. Every requested source ends in an explicit disposition. `complete` means the source reported all requested artifacts and the evidence store verified them; `partial`, `unavailable`, `rejected`, `cancelled`, and `failed` are distinct outcomes and remain visible in coverage.

Case reads and exports are tenant- and case-scoped. Holds block release and retention deletion. Evidence items preserve the case, endpoint, source, plan, collection item, attempt, digest, capture time, and quality traits. Custody events are append-only. The bundled collection lab and seed contain synthetic metadata/payloads only and never contact real endpoints.
