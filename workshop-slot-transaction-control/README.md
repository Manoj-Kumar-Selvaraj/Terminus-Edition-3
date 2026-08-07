# workshop-slot-transaction-control

Human notes only. Agents never see this file.

## What the task is

A real GnuCOBOL + Open COBOL ESQL + PostgreSQL maintenance-workshop terminal.
Operators book bays and technicians for transport / generator / radio /
medical equipment. The military framing is administrative scheduling only —
no weapons, targeting, intel, combat, readiness or deployment decisions.

Five COPY books under `src/copybooks/` ship broken (transaction begin, request
identity, resource lock, overlap check, move). Sequential happy-path bookings
can look fine; concurrent retries, competing claims, failed moves and audit
numbering fail the contract. Goals live in `instruction.md`. Protocol,
state machine, policy and response schemas live in
`environment/docs/terminal-contract.md`.

## Why it bites

Bugs interact under concurrency: request-identity handling, resource locking,
half-open overlap checks and move rollback all have to agree. A fix that works
for a single `workshopctl` call still fails the parallel suites. Audit
sequences must stay gap-free among committed events only — rejects and
rollbacks must not burn numbers.

## Difficulty

Advanced. Real ESQL against PostgreSQL, compose multi-container agent env,
separate verifier that rebuilds submitted sources and drives concurrent
terminals.

## Oracle

`solution/solve.sh` installs the five fixed COPY books from `solution/fixed/`
and runs `/app/workshop/bin/build-workshop`.

## Verification

Separate verifier starts a clean local PostgreSQL, rebuilds `/app/workshop`
from the agent's sources, and runs pytest (`protocol`, `transactions`,
`concurrency`, `policy`). Hand-written SQL side paths cannot satisfy the
native-binary requirement in the contract.

## Base images / network

Agent is a two-service Compose app (`main` + `database`). Debian
bookworm-slim is the canonical base — Terminus has no dedicated GnuCOBOL
image. GnuCOBOL, libpq, OCESQL (pinned upstream commit
`14591d82…` with checksum), tmux and asciinema are installed at build time.
Verifier image also builds OCESQL and hosts PostgreSQL for the grade.
`network_mode = "public"` because the OCESQL tarball is fetched during image
build; trial runtime does not need the network for the grade itself.
