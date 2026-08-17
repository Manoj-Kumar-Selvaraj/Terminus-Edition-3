# Storage contract

The executable is `/app/stonevault/bin/stonevault`. Its Rust command layer owns argument parsing, command validation, and the line protocol. The durable storage implementation is C++20 behind the existing C ABI in `/app/stonevault/storage/engine.hpp`.

## Startup and data directory

`stonevault [--data-dir PATH]` opens one writable database directory. If the flag is absent, `STONEVAULT_DATA` is used, then `/app/stonevault/data` as the final default. A successful open writes `READY <commit-sequence>` to stdout. An open failure exits non-zero and explains the storage error on stderr.

Only one process may hold a database directory open for writing. The lock is represented by `LOCK` in that directory and is held for the lifetime of the engine. A second writer must fail rather than run concurrently.

## Command protocol

Input is one ASCII command per line. Keys, values, and scan prefixes are even-length hexadecimal strings representing arbitrary bytes. Hex digits are case-insensitive on input; returned data is lowercase. Keys are at most 4096 bytes and values at most 1048576 bytes.

- `BEGIN` -> `OK BEGIN <tx-id>`
- `PUT <tx-id> <key-hex> <value-hex>` -> `OK`
- `DEL <tx-id> <key-hex>` -> `OK`
- `GET <tx-id> <key-hex>` -> `VALUE <value-hex>` or `NOT_FOUND`
- `SCAN <tx-id> <prefix-hex>` -> `ROWS <count>` or `ROWS <count> <key>=<value>,...`
- `COMMIT <tx-id>` -> `OK COMMIT <commit-sequence>` or `ERR CONFLICT`
- `ROLLBACK <tx-id>` -> `OK`
- `CHECKPOINT` -> `OK CHECKPOINT <commit-sequence>` or `ERR BUSY`
- `STATS` -> `STATS commit_seq=<n> keys=<n> wal_bytes=<n>`
- `QUIT` -> `BYE`

Other malformed commands return an `ERR` line without terminating the process.

## Transaction semantics

`BEGIN` captures the current committed sequence. Reads and scans use that snapshot for their lifetime, with the transaction's own later writes overlaid on top. Scans include only keys with the requested raw-byte prefix and order rows by unsigned bytewise key order. Deletes suppress rows in the local overlay.

A commit is atomic. If any key written by a transaction was committed by another transaction after its snapshot, the commit returns `ERR CONFLICT`, publishes none of that transaction's writes, and ends the transaction. Successful commits receive contiguous increasing sequences. Rollback ends the transaction without publishing its writes.

## WAL and recovery

`wal.log` is append-only between checkpoints. Multi-byte integers are little-endian.

Each WAL record is:

```
u32 magic = 0x31575653
u32 payload_length
u32 crc32_ieee(payload)
bytes payload
```

Payloads are one of:

```
PUT:    u8 1, u64 tx, u32 key_len, u32 value_len, key, value
DELETE: u8 2, u64 tx, u32 key_len, key
COMMIT: u8 3, u64 tx, u64 commit_sequence
```

Mutation records are not visible after restart unless a valid matching `COMMIT` is recovered. A short final WAL header or payload is a torn tail: discard bytes from the start of that incomplete record and continue opening. A bad magic, impossible complete record, checksum mismatch, malformed complete payload, or broken commit sequence is corruption: opening must fail and report `WAL corruption` instead of silently discarding earlier valid history.

Successful `COMMIT` does not return until its commit record is durable.

## Snapshot and checkpoint

`snapshot.dat` contains the latest checkpointed committed state. Its format is:

```
8 bytes  "SVSNAP1\0"
u64 checkpoint_sequence
u64 row_count
repeated rows:
  u32 key_len
  u32 value_len
  key
  value
  u32 crc32_ieee(key_len || value_len || key || value)
```

A checkpoint is allowed only with no active transactions. It durably writes and atomically publishes the snapshot, then reclaims the WAL so `wal.log` is empty. Restart after checkpoint must reproduce the same keys and commit sequence. Snapshot format or checksum errors are fatal storage corruption.

`STATS` reports the current durable commit sequence, the number of currently visible committed keys, and the current WAL file size in bytes.
