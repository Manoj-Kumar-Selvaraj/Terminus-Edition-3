The click/telemetry session processor under `/app/sessions` produces plausible output on tidy single-tenant samples, but late events, out-of-order arrivals, watermark stalls, and process restarts produce wrong session closes, merged tenants, duplicate side-outputs, or a watermark journal that moves backwards. Repair the existing Python processor; do not move the session logic into another language or discard the journal protocol.

- Treat `/app/sessions/docs/session-contract.md` as binding for event-time semantics, schemas, lateness, gap rules, restarts, and CLI behavior. Keep public fields and paths unchanged.
- Drive all work through `/app/sessions/bin/run-sessions`. Reject unknown flags before touching state.
- Key sessions by event time, not wall or processing time. Session identity and half-open intervals follow the contract, including multi-tenant isolation.
- Apply gap closes and watermark advances exactly as the contract defines. Late-but-allowed events may still update open sessions; too-late events belong only in the late side output with required provenance.
- Persist and reload `/app/sessions/data/watermark.journal` plus open-session state so a restart continues in-flight sessions and keeps the watermark non-decreasing.
- A second identical run must leave the same digests for closed sessions and late output. An empty input must leave empty outputs without advancing the watermark.
- Read gap, allowed lateness, and duration limits from the configured paths. Fail closed on malformed records and invalid watermark inputs using the documented rejection codes.
- Leave `/app/sessions` buildable offline with the repaired sources included. Do not rewrite the contract to excuse the current behavior.
