# Payment EOD restart control

This package is a cut-down payment EOD chain used to reproduce a restart problem. Small COBOL programs make the business decisions, the shell controller moves the cycle through the batch stages, and SQLite holds the durable state.

The important cases start after some work has already committed. An internal posting may already exist, or an external payment may already have its reservation while clearing, reconciliation or close is still unfinished. On the next invocation that state has to be continued, not treated as another payment execution. Source-reference history has the same wrinkle: history written by the current cycle is restart state, while a source reference accepted by an earlier cycle is a replay.

The files under `environment/eod/docs/` are the operating notes for those rules and for the COBOL/file interfaces. They deliberately describe the existing controls rather than the repair. The database remains the restart authority; the flat-file outputs are publication or operator artifacts derived from it.

A balanced cycle can publish its customer response and clearing submission, but completion is a separate step. Delivery acknowledgement, reporting and archive work must all be finished before the authorization is written. A repeated completed run should therefore reproduce the same outward result without adding another posting, reservation, clearing item, ledger obligation or authorization.
