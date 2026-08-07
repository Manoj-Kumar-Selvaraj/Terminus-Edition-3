The GnuCOBOL wire release desk at /app/wire moves funds correctly when operators work one request at a time. Concurrent retries, dual-control approvals, frozen accounts, and twin ledger postings can accept stale revisions, skip the second control step, under-post the credit side, or leave gaps in the audit sequence. Repair the existing COBOL application without moving its transaction logic into another language.

- Treat /app/wire/docs/terminal-contract.md as binding for commands, states, dual-control, ledger posting, concurrency, idempotency, and line-based responses. Keep the public fields and schemas unchanged.
- Build with /app/wire/bin/build-wire. Use the supplied environment variables for the live PostgreSQL connection and /app/wire/bin/wirectl as the operator interface. Reject malformed use before touching the database.
- Commit each accepted state change, its request record, and its audit entry in one PostgreSQL transaction. Killing the process mid-operation must leave no partial request, wire, ledger, or audit data.
- Follow the required wire states without creating orphan ledger rows. RELEASE must post debit and credit ledger lines and update both balances atomically.
- An identical retry returns the stored response byte for byte and runs no more SQL. If any argument changes under the same request ID, return REQUEST_CONFLICT and leave the original record alone. Store and replay business rejections too.
- Concurrent first use of one request ID must settle on one stored result. Stale revisions and invalid state changes fail closed, with the documented rejection order.
- Approvers must differ from initiators. Frozen accounts and insufficient debit balances reject RELEASE with the documented codes and leave balances unchanged.
- Keep audit numbers unique and gap-free across committed events, including concurrent work. Rejected requests and rolled-back attempts consume no audit sequence.
- Leave the submitted /app/wire tree buildable offline, with the repaired COBOL and SQL migration sources included.
