# Workshop terminal operations contract

This document describes the operator protocol and transaction rules for the maintenance-workshop terminal. It is a protocol reference, not a guide to the implementation. The system schedules administrative maintenance for transport vehicles, generators, radio replacement units, and medical equipment.

## Connection and build

`/app/workshop/bin/build-workshop` must rebuild the application from the submitted COBOL sources without downloading anything. `/app/workshop/bin/workshopctl` runs one terminal transaction against the PostgreSQL connection named by `WORKSHOP_DB`, `WORKSHOP_DB_USER`, and `WORKSHOP_DB_PASSWORD`.

This is a native COBOL database application, not a batch file exercise. The command path must execute the GnuCOBOL binary and its embedded OCESQL statements rather than delegate the behavior to another language.

Commands and responses use ASCII. Command names and enumerated values are uppercase. Identifiers are case-sensitive and contain only uppercase letters, digits, and hyphens. Request IDs are 3-24 characters, work-order IDs 3-16, bay IDs 3-8, and technician IDs 3-8. Ticks and revisions are unsigned decimal arguments without signs or padding.

## Commands

| Command | Arguments after command |
|---|---|
| `HEALTH` | none |
| `OPEN` | `request-id work-order-id equipment-class priority` |
| `RESERVE` | `request-id work-order-id expected-revision bay-id technician-id start-tick end-tick` |
| `MOVE` | `request-id work-order-id expected-revision bay-id technician-id start-tick end-tick` |
| `START` | `request-id work-order-id expected-revision` |
| `COMPLETE` | `request-id work-order-id expected-revision` |
| `CANCEL` | `request-id work-order-id expected-revision` |
| `STATUS` | `work-order-id` |
| `AUDIT` | `work-order-id` |

Equipment classes are `TRANSPORT`, `GENERATOR`, `RADIO`, and `MEDICAL`. Priorities are 1 through 9. Time ticks are 0 through 999999 and a window requires `start-tick < end-tick`.

Ticks are workshop minutes. Scheduling uses the compiled alternating-roster policy: roster A applies when `floor(start-tick / 10080)` is even and roster B when it is odd. Priorities 1-3 may start in any hour. Priorities 4-6 may start from hour 04 through 21 in roster A and 05 through 22 in roster B. Priorities 7-9 may start from hour 06 through 17 in roster A and 07 through 18 in roster B. The hour is `floor((start-tick mod 1440) / 60)`.

Maximum duration is the class base plus 30 minutes for every step below priority 1: bases are 720 for `TRANSPORT`, 480 for `GENERATOR`, 360 for `RADIO`, and 240 for `MEDICAL`, so `max-duration = base + ((priority - 1) * 30)`. The booking row records the selected policy ID, day/night shift, supervision level, and capacity percentage from the same decision. Day shift covers hours 06 through 17. Supervision is 3 for priorities 1-2, 2 for 3-6, and 1 for 7-9; capacity is 100, 85, and 70 for those same three bands. A disallowed start hour or excessive duration is `INVALID_WINDOW`.

## Response lines

Every invocation writes only its response to stdout and ends each line with LF. Mutation success is one line in this exact field order:

`OK|request=<id>|command=<name>|order=<id>|booking=<id-or-NONE>|revision=<six digits>|state=<state>|audit=<ten digits>`

Business rejection is one line:

`ERR|request=<id-or-NONE>|command=<name>|code=<reason>`

`HEALTH` returns `HEALTH|database=READY|schema=1`. `STATUS` returns one line:

`STATUS|order=<id>|class=<class>|priority=<one digit>|revision=<six digits>|state=<state>|booking=<id-or-NONE>|bay=<id-or-NONE>|technician=<id-or-NONE>|start=<six digits>|end=<six digits>`

`AUDIT` returns zero or more lines ordered by audit sequence:

`AUDIT|sequence=<ten digits>|request=<id>|order=<id>|action=<command>|from=<state>|to=<state>|revision=<six digits>`

Usage or malformed argument errors return exit 2 and an `ERR` line on stderr. Database or build failures return a nonzero exit and an `ERR` line on stderr. Business rejections return exit 1. Successful mutations, replays, health, status, and audit return exit 0.

## State and resource rules

`OPEN` creates revision 1 in state `OPEN`. Work-order IDs are unique. A class-specific bay or technician serves only that class; a `UNIVERSAL` resource serves every class. Inactive resources are unavailable.

`RESERVE` requires current state `OPEN` and the exact current revision. It claims both resources for the half-open interval `[start-tick,end-tick)`, creates one active booking, changes the order to `RESERVED`, and increases the revision by one. Two active bookings conflict when their half-open intervals overlap and they use the same bay or the same technician. Adjacent intervals do not overlap.

`MOVE` requires `RESERVED` and its exact revision. It changes the existing active booking to the replacement bay, technician, and interval, then increases both booking and order revision by one. The existing booking must remain unchanged if any replacement check fails. Its own current interval is excluded from conflict checks.

`START` changes `RESERVED` to `STARTED`; `COMPLETE` changes `STARTED` to `COMPLETED`; and `CANCEL` changes `OPEN` or `RESERVED` to `CANCELLED`. Completion or cancellation also changes an active booking to the same terminal state. Other transitions return `INVALID_STATE`. Every accepted transition raises the work-order revision exactly once.

## Atomicity, concurrency, and retries

The request record, work-order or booking change, and audit event form one PostgreSQL transaction. A failed validation, resource conflict, stale revision, SQL retry, process termination, or database error must not expose a partial state change.

Concurrent claims for the same resource and overlapping interval must leave at most one accepted booking. The losing request returns `RESOURCE_BUSY` after observing the committed winner. Deadlock and serialization failures are internal retry conditions, not business responses; retry the complete transaction a bounded number of times. Unrelated resource claims must remain independent.

## Request identity

For mutation commands the request fingerprint is the command name plus every parsed argument in public argument order. The first completed use of a request ID is permanent, including a business rejection. An identical retry returns the exact recorded response and performs no SQL state or audit change. Reuse with any different parsed argument returns `REQUEST_CONFLICT` and leaves the original record untouched. Simultaneous identical uses converge on one recorded result.

## Audit control

Every accepted mutation has one audit event in the same transaction. Audit sequences begin at 1, have no gaps among committed audit events, and reflect the order in which the audit counter was reserved inside committed transactions. Rejected requests and rolled-back attempts consume no audit sequence. Replays create no audit event.

## Rejection precedence

After request-identity handling, use this public precedence where several failures apply: `UNKNOWN_ORDER`, `STALE_REVISION`, `INVALID_STATE`, `UNKNOWN_RESOURCE`, `INCOMPATIBLE_RESOURCE`, `INVALID_WINDOW`, then `RESOURCE_BUSY`. `OPEN` reports `ORDER_EXISTS` for an existing order. Malformed command arguments are usage errors rather than recorded business requests.
