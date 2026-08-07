# Payment EOD batch

This fixture models the end-of-day part of a corporate payment cycle after upstream validation, risk and pricing have already completed. Durable state lives in SQLite under `/app/eod/state`; `PAYDUP` and `PAYEXEC` make the duplicate/execution decisions; `/app/eod/bin/run_eod.sh` coordinates the financial work and cycle close.

Restart behavior is the point of the exercise. The same runner may see a fresh payment, an accepted source replay, or a payment whose posting or reservation was committed before the previous run stopped. Those states remain in the database and must be treated as authoritative on the next invocation.

Record layouts, financial invariants and published-file schemas are kept in `/app/eod/contracts/eod_contract.md`. `/app/eod/sql/seed.sql` is only a sample cycle for local inspection; it is not the complete business contract.
