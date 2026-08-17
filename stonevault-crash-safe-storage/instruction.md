Complete the reliability hardening of the embedded database under `/app/stonevault` and rebuild `/app/stonevault/bin/stonevault`. Keep the product implementation in C++20 and Rust only; Python belongs only in the external verifier and Go must not be added. The existing command and disk layouts are documented in `/app/stonevault/docs/storage-format.md` and remain compatibility contracts.

- Only one writable process may hold a database directory at a time, and the writer exclusion must be released cleanly when that process exits.
- An explicit `--data-dir` must override `STONEVAULT_DATA`, which in turn overrides the documented default directory.
- Transactions must provide stable snapshot reads and prefix scans for their full lifetime while still exposing their own puts and deletes.
- Prefix scans must filter raw-byte prefixes and return keys in deterministic unsigned bytewise order.
- Concurrent writers must use first-committer-wins write/write conflict detection: a stale writer touching a newer committed key is rejected atomically, ends, and does not consume a commit sequence.
- Successful commits must be all-or-nothing, use contiguous increasing sequences, and return only after the commit record is durable.
- Rollback and a process killed with an open transaction must never make that transaction's WAL mutations visible after restart.
- Recovery must retain every valid committed transaction, discard only a short final WAL header/payload as a torn tail, and fail closed on corruption of any complete WAL record or committed-sequence history.
- Checkpoint must refuse while any transaction is active; otherwise it must atomically publish the current committed snapshot, durably preserve its sequence and rows, and reclaim `wal.log` to zero bytes.
- Opening must reject corrupt snapshots, including checksum, truncation, ordering, size, row-count, magic, and trailing-byte failures, while ignoring/removing only an abandoned `snapshot.tmp`.
- `STATS` must report the durable commit sequence, visible committed-key count, and actual WAL byte size.
- `HEALTH` must validate the reachable catalog/storage invariants and accurately report sequence, key count, active transaction count, WAL bytes, and whether a published snapshot exists.
- Keys/values remain arbitrary binary data represented as hexadecimal; input hex is case-insensitive and returned hex is lowercase.
- The documented 4096-byte key/prefix and 1048576-byte value limits are inclusive; oversized inputs must be rejected without killing the process.
- Malformed commands and unknown transaction IDs must return `ERR` and leave the process able to accept later valid commands.
- Preserve the documented C ABI, ASCII response shapes, WAL layout, snapshot layout, and existing data compatibility while making these guarantees hold across restart and maintenance cycles.
