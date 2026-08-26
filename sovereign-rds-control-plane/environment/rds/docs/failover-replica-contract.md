# Read Replica Promotion & Multi-AZ Failover Fencing Contract

High availability and read scaling rely on strict fencing rules during replica promotion and Multi-AZ failover.

## Read Replica Promotion

1. **Replication Lag Gate**:
   - `PromoteReadReplica` verifies `replication_lag_bytes <= MaximumAllowedLagBytes` (10 MB).
   - If replication lag exceeds threshold or status is unknown, promotion is rejected.

2. **WAL LSN Catch-Up**:
   - The replica must catch up LSN flush (`flush_lsn >= primary_write_lsn`) before assuming primary role.

3. **Write Lease Revocation**:
   - The former primary instance's write lease (`write_lease_owner`) is revoked before replica promotion to prevent dual-primary writes.

## Multi-AZ Failover Fencing

1. **Lease Acquisition**:
   - Failover workers must acquire an exclusive leader lease (`failover_leases`) with TTL (15s).

2. **Health Probe Isolation**:
   - Instance health probes connect directly to the database TCP port (5432) rather than testing control plane database connection pool state.

3. **VIP Routing Migration**:
   - Floating VIP addresses migrate to the new primary host, flushing route tables and issuing gratuitous ARP announcements.
