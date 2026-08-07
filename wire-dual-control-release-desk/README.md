# wire-dual-control-release-desk

Human notes only. Agents never see this file.

## What the task is

A real GnuCOBOL + Open COBOL ESQL + PostgreSQL dual-control wire /
funds-release terminal. Operators initiate wires between seeded accounts,
require a different approver, then release twin ledger postings that debit
one account and credit another.

Five COPY books under `src/copybooks/` ship broken (transaction begin,
request identity, dual-control check, twin post, freeze gate). Sequential
happy-path INITIATE→APPROVE→RELEASE can look fine; concurrent retries,
same-operator approvals, frozen accounts, one-sided postings, and audit
numbering fail the contract. Goals live in `instruction.md`. Protocol,
state machine, dual-control and response schemas live in
`environment/docs/terminal-contract.md`.

## Why it bites

Bugs interact under concurrency and money movement: request-identity
fingerprints, SERIALIZABLE request locks, dual-control identity checks,
freeze/funds gates, and twin-sided ledger updates all have to agree. A
fix that works for a single `wirectl` call still fails the parallel and
controls suites. Audit sequences must stay gap-free among committed events
only — rejects and rollbacks must not burn numbers.

## Difficulty

Advanced. Real ESQL against PostgreSQL, compose multi-container agent env,
separate verifier that rebuilds submitted sources and drives concurrent
terminals. Difficulty is provisional until measured.

## Oracle

`solution/solve.sh` installs the five fixed COPY books from `solution/fixed/`
and runs `/app/wire/bin/build-wire`.

## Verification

Separate verifier starts a clean local PostgreSQL, rebuilds `/app/wire`
from the agent's sources, and runs pytest (`protocol`, `transactions`,
`concurrency`, `controls`). Hand-written SQL side paths cannot satisfy the
native-binary requirement in the contract.

## Base images / network

Agent is a two-service Compose app (`main` + `database`). Debian
bookworm-slim is the canonical base — Terminus has no dedicated GnuCOBOL
image. GnuCOBOL, libpq, OCESQL (pinned upstream commit
`14591d82…` with checksum), tmux and asciinema are installed at build time.
Verifier image also builds OCESQL and hosts PostgreSQL for the grade.
`network_mode = "public"` because the OCESQL tarball is fetched during image
build; trial runtime does not need the network for the grade itself.
