# StoneVault

StoneVault is a native embedded transactional key/value engine with a Rust command/session layer and a C++20 storage core. The two layers communicate through a stable C ABI and persist database state in a directory containing the writer lock, append-only WAL, and optional checkpoint snapshot.

## Architecture

The Rust layer owns command parsing, hexadecimal protocol validation, configuration resolution, line-oriented I/O, session dispatch, and operator-facing response formatting. The C++ storage layer owns transaction state, MVCC version history, WAL append/recovery, snapshot publication, checkpoint lifecycle, writer fencing, integrity auditing, and durable-state statistics.

Build the executable with `make` from `/app/stonevault`; the resulting binary is `/app/stonevault/bin/stonevault`. The documented command, C ABI, WAL, and snapshot formats are in `docs/storage-format.md`.

## Reliability scope

The storage engine is designed around a single writable process per database directory, transaction-lifetime snapshot visibility, first-committer-wins conflict handling, durable commit sequencing, fail-closed recovery of complete corruption, atomic checkpoint publication, and restart-safe preservation of committed state. `STATS` and `HEALTH` expose durable and live engine state through the same runtime catalog, transaction, WAL, and snapshot paths used by normal operation.

## Validation

Validation should exercise fresh and restarted database directories, concurrent writer attempts, transaction interleavings, WAL and snapshot damage boundaries, checkpoint maintenance, binary keys/values, inclusive protocol limits, malformed input recovery, operator status, and compatibility of the documented native interfaces and disk layouts.
