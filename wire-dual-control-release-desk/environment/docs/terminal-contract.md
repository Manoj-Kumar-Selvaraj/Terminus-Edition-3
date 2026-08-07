# Wire release desk operations contract

This document describes the operator protocol and transaction rules for the dual-control wire release terminal. It is a protocol reference, not a guide to the implementation. The system initiates, approves, and releases funds transfers between seeded accounts under dual-control rules.

## Connection and build

`/app/wire/bin/build-wire` must rebuild the application from the submitted COBOL sources without downloading anything. `/app/wire/bin/wirectl` runs one terminal transaction against the PostgreSQL connection named by `WIRE_DB`, `WIRE_DB_USER`, and `WIRE_DB_PASSWORD`.

This is a native COBOL database application, not a batch file exercise. The command path must execute the GnuCOBOL binary and its embedded OCESQL statements rather than delegate the behavior to another language.

Commands and responses use ASCII. Command names and enumerated values are uppercase. Identifiers are case-sensitive and contain only uppercase letters, digits, and hyphens. Request IDs are 3-24 characters, wire IDs 3-16, account IDs 3-16, and operator IDs 3-16. Revisions and cent amounts are unsigned decimal arguments without signs or padding. Cent amounts are 1 through 999999999999.

## Commands

| Command | Arguments after command |
|---|---|
| `HEALTH` | none |
| `INITIATE` | `request-id wire-id debit-account credit-account amount-cents initiator-id` |
| `APPROVE` | `request-id wire-id expected-revision approver-id` |
| `RELEASE` | `request-id wire-id expected-revision` |
| `CANCEL` | `request-id wire-id expected-revision` |
| `STATUS` | `wire-id` |
| `AUDIT` | `wire-id` |

`amount-cents` is the funds amount moved from the debit account to the credit account on `RELEASE`. Debit and credit accounts must be different seeded accounts.

## Response lines

Every invocation writes only its response to stdout and ends each line with LF. Mutation success is one line in this exact field order:

`OK|request=<id>|command=<name>|wire=<id>|revision=<six digits>|state=<state>|debit=<twelve digits>|credit=<twelve digits>|audit=<ten digits>`

For success lines, `debit` and `credit` are the resulting balances of the wire's debit and credit accounts after the accepted mutation. Before `RELEASE` those balances are unchanged from the prior committed values.

Business rejection is one line:

`ERR|request=<id-or-NONE>|command=<name>|code=<reason>`

`HEALTH` returns `HEALTH|database=READY|schema=1`. `STATUS` returns one line:

`STATUS|wire=<id>|revision=<six digits>|state=<state>|debit-account=<id>|credit-account=<id>|amount=<twelve digits>|initiator=<id>|approver=<id-or-NONE>`

`AUDIT` returns zero or more lines ordered by audit sequence:

`AUDIT|sequence=<ten digits>|request=<id>|wire=<id>|action=<command>|from=<state>|to=<state>|revision=<six digits>`

Usage or malformed argument errors return exit 2 and an `ERR` line on stderr. Database or build failures return a nonzero exit and an `ERR` line on stderr. Business rejections return exit 1. Successful mutations, replays, health, status, and audit return exit 0.

## State rules

`INITIATE` creates revision 1 in state `INITIATED` with the given debit account, credit account, amount, and initiator. Wire IDs are unique. Unknown accounts return `UNKNOWN_ACCOUNT`. Unknown operators return `UNKNOWN_OPERATOR`. Duplicate wire IDs return `WIRE_EXISTS`. Identical debit and credit accounts return `INVALID_ACCOUNTS`.

`APPROVE` requires state `INITIATED` and the exact current revision. The approver must be a known operator and must differ from the initiator; otherwise return `SAME_OPERATOR`. On accept, store the approver, move to `APPROVED`, and raise the revision by one.

`RELEASE` requires state `APPROVED` and the exact current revision. It locks both accounts, rejects with `ACCOUNT_FROZEN` when either account is frozen, rejects with `INSUFFICIENT_FUNDS` when the debit balance is less than the wire amount, then posts one debit ledger row and one credit ledger row, updates both balances by the wire amount, moves the wire to `RELEASED`, and raises the revision by one.

`CANCEL` requires state `INITIATED` or `APPROVED` and the exact current revision, then moves the wire to `CANCELLED` and raises the revision by one. Other transitions return `INVALID_STATE`. Every accepted transition raises the wire revision exactly once.

## Ledger twin posting

On accepted `RELEASE` exactly two ledger rows exist for the wire: one `DEBIT` against the debit account for `amount-cents` and one `CREDIT` against the credit account for `amount-cents`. The debit account balance decreases by that amount and the credit account balance increases by that amount in the same transaction. A failed freeze or funds check must leave every balance and ledger row unchanged.

## Atomicity, concurrency, and retries

The request record, wire or ledger change, and audit event form one PostgreSQL transaction. A failed validation, stale revision, SQL retry, process termination, or database error must not expose a partial state change.

Concurrent first use of the same request ID must converge on one recorded result. Deadlock and serialization failures are internal retry conditions, not business responses; retry the complete transaction a bounded number of times. Unrelated wires must remain independent.

Mutation transactions must run at `SERIALIZABLE` isolation and take a transaction-scoped advisory lock keyed as `REQUEST:` plus the request ID before request-identity handling.

## Request identity

For mutation commands the request fingerprint is the command name plus every parsed argument in public argument order. The first completed use of a request ID is permanent, including a business rejection. An identical retry returns the exact recorded response and performs no SQL state or audit change. Reuse with any different parsed argument returns `REQUEST_CONFLICT` and leaves the original record untouched. Simultaneous identical uses converge on one recorded result.

## Audit control

Every accepted mutation has one audit event in the same transaction. Audit sequences begin at 1, have no gaps among committed audit events, and reflect the order in which the audit counter was reserved inside committed transactions. Rejected requests and rolled-back attempts consume no audit sequence. Replays create no audit event.

## Rejection precedence

After request-identity handling, use this public precedence where several failures apply: `UNKNOWN_WIRE`, `STALE_REVISION`, `INVALID_STATE`, `UNKNOWN_ACCOUNT`, `UNKNOWN_OPERATOR`, `SAME_OPERATOR`, `INVALID_ACCOUNTS`, `ACCOUNT_FROZEN`, then `INSUFFICIENT_FUNDS`. `INITIATE` reports `WIRE_EXISTS` for an existing wire before account and operator checks. Malformed command arguments are usage errors rather than recorded business requests.
