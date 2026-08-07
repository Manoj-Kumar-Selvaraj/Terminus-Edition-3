The GnuCOBOL workshop terminal at /app/workshop behaves correctly when bookings arrive one at a time. Overlapping and retried requests can create duplicate reservations, lose slots after failed moves, accept stale changes, or leave gaps in the audit sequence. Repair the existing COBOL application without moving its transaction logic into another language.

- Treat /app/workshop/docs/terminal-contract.md as binding for commands, states, concurrency, idempotency, and line-based responses. Keep the public fields and schemas unchanged.
- Build with /app/workshop/bin/build-workshop. Use the supplied environment variables for the live PostgreSQL connection and /app/workshop/bin/workshopctl as the operator interface. Reject malformed use before touching the database.
- Commit each accepted state change, its request record, and its audit entry in one PostgreSQL transaction. Killing the process mid-operation must leave no partial request, booking, or audit data.
- Follow the required booking and cancellation states without creating orphan rows.
- An identical retry returns the stored response byte for byte and runs no more SQL. If any argument changes under the same request ID, return REQUEST_CONFLICT and leave the original record alone. Store and replay business rejections too.
- Concurrent first use of one request ID must settle on one stored result. Stale revisions and invalid state changes fail closed, with the documented rejection order.
- Reject inactive resources and incompatible classes. When claims overlap on the same bay or technician, pick one deterministic winner and return RESOURCE_BUSY to the loser. This also applies when different bays share a technician. Unrelated claims must still commit together.
- Treat booking intervals as half-open, so adjacent slots do not conflict. A failed move must leave every booking field unchanged.
- Keep audit numbers unique and gap-free across committed events, including concurrent work.
- Apply the alternating roster window, duration limits, and stored policy fields from the contract. A move may replace those fields only after the whole change has been approved.
- Leave the submitted /app/workshop tree buildable offline, with the repaired COBOL and SQL migration sources included.
