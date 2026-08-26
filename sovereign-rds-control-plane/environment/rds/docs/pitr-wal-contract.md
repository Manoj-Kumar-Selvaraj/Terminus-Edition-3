# WAL-Backed Point-In-Time Recovery (PITR) Technical Contract

The control plane maintains continuous WAL archiving and base backup manifests for database instance restoration.

## WAL Continuity & PITR Rules

1. **WAL Ingestion**:
   - Every WAL segment file (e.g. `000000010000000000000001`) is cataloged with timeline ID, sequence number, start LSN, and end LSN.
   - Sequence continuity is verified: any missing sequence number triggers `has_gap = true` and halts automated PITR until resolved.

2. **Base Backup Binding**:
   - Base backup manifests record `snapshot_id`, `redo_lsn`, and `timeline_id`.
   - Restoring a base backup verifies LSN alignment with the target WAL timeline.

3. **Target Timestamp Synthesis**:
   - `RestoreDBInstanceToPointInTime` specifies `TargetRestorableTime`.
   - The restore engine identifies the latest base backup before `TargetRestorableTime` and replays WAL segments up to the exact transaction timestamp.
   - Target timestamps outside `[EarliestRestorableTime, LatestRestorableTime]` are rejected.
