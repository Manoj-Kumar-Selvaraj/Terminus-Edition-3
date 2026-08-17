# Storage and wire format

The executable is `/app/stonevault/bin/stonevault`. The Rust process owns argument parsing and the ASCII line protocol; the C++20 library behind `storage/engine.hpp` owns transactions, durability, recovery, checkpointing, and integrity checks.

## Startup

`stonevault [--data-dir PATH]` selects a writable database directory. The explicit flag has highest precedence, followed by `STONEVAULT_DATA`, then `/app/stonevault/data`. On success the first stdout line is `READY <commit-sequence>`. Open failures are written to stderr and return non-zero. A `LOCK` file in the data directory is exclusively locked for the lifetime of a writable process.

## Commands

Each command is one ASCII line. Hex operands encode arbitrary bytes, accept upper/lowercase input, and are emitted in lowercase. Keys and scan prefixes are at most 4096 decoded bytes; values are at most 1048576 decoded bytes.

- `BEGIN` -> `OK BEGIN <tx-id>`
- `PUT <tx-id> <key-hex> <value-hex>` -> `OK`
- `DEL <tx-id> <key-hex>` -> `OK`
- `GET <tx-id> <key-hex>` -> `VALUE <value-hex>` or `NOT_FOUND`
- `SCAN <tx-id> <prefix-hex>` -> `ROWS <count>` or `ROWS <count> <key>=<value>,...`
- `COMMIT <tx-id>` -> `OK COMMIT <commit-sequence>` or `ERR CONFLICT`
- `ROLLBACK <tx-id>` -> `OK`
- `CHECKPOINT` -> `OK CHECKPOINT <commit-sequence>` or `ERR BUSY`
- `STATS` -> `STATS commit_seq=<n> keys=<n> wal_bytes=<n>`
- `HEALTH` -> `HEALTH status=ok commit_seq=<n> keys=<n> active_tx=<n> wal_bytes=<n> snapshot=present|absent`
- `QUIT` -> `BYE`

Malformed commands return an `ERR` line without terminating the process.

## Transactions

`BEGIN` captures the current committed sequence. Reads and prefix scans use that snapshot for the transaction lifetime and overlay that transaction's own later writes/deletes. Scan order is unsigned bytewise key order. A successful commit is atomic and receives the next contiguous sequence. If any written key has a committed version newer than the transaction snapshot, commit returns `ERR CONFLICT`, publishes none of its writes, does not advance the sequence, and ends the transaction. Rollback ends a transaction without publishing its mutations.

## WAL

`wal.log` is append-only between checkpoints. Integers are little-endian. Every record has:

```
u32 magic = 0x31575653
u32 payload_length
u32 crc32_ieee(payload)
bytes payload
```

Payloads are:

```
PUT:    u8 1, u64 tx, u32 key_len, u32 value_len, key, value
DELETE: u8 2, u64 tx, u32 key_len, key
COMMIT: u8 3, u64 tx, u64 commit_sequence
```

Mutation records become recoverable only through a valid matching COMMIT. A short final header or payload is a torn tail and is truncated from the beginning of the incomplete record. Bad magic, impossible complete record length, checksum mismatch, malformed complete payload, unknown type, or non-contiguous committed sequence is corruption and opening fails with `WAL corruption`. A successful `COMMIT` returns only after its commit record is synced.

## Snapshot

`snapshot.dat` is:

```
8 bytes "SVSNAP1\0"
u64 checkpoint_sequence
u64 row_count
repeat row_count times:
  u32 key_len
  u32 value_len
  key
  value
  u32 crc32_ieee(serialized key_len || value_len || key || value)
```

Rows are strictly increasing in unsigned bytewise key order. Bad magic, truncation, invalid sizes, checksum failure, duplicate/out-of-order keys, impossible row count, or trailing bytes is fatal snapshot corruption. Checkpoint writes `snapshot.tmp`, syncs it, atomically renames it to `snapshot.dat`, syncs the directory, then truncates/syncs the WAL. A stale `snapshot.tmp` from an interrupted prior attempt is discarded during open.
