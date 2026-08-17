# Crash-safe embedded storage hardening

StoneVault is a cross-language embedded storage engine with a Rust command/control plane and a C++20 durable core. The core separates transaction lifecycle, MVCC catalog, WAL, recovery, snapshots, locking, integrity checks, and maintenance so each responsibility can be reasoned about independently while still participating in one restart-safe state machine.

## Reliability scope

The reliability work preserves the public line protocol, C ABI, and on-disk formats while strengthening writer fencing, snapshot visibility, atomic conflict handling, transactional recovery, corruption classification, checkpoint lifecycle, and operator observability. Restart and maintenance behavior are exercised through the compiled executable and durable files rather than through internal implementation hooks.

## Validation

Validation covers live multi-transaction behavior, crash/restart recovery, torn and corrupted WAL records, snapshot integrity, checkpoint/restart cycles, binary key/value boundaries, data-directory selection, STATS/HEALTH reporting, and public ABI preservation. The important interactions are cross-component: recovery affects visible sequence state, checkpoint changes WAL/restart behavior, transaction visibility affects scans and conflict arbitration, and writer/health behavior depends on actual resource ownership.
