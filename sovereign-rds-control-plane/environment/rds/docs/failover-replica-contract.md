# Read Replica Promotion & Multi-AZ Failover Fencing Contract

High availability and read scaling rely on strict fencing rules during replica promotion and Multi-AZ failover.

## Read Replica Promotion

1. **Replication Lag Gate**:
   - `PromoteReadReplica` verifies `replication_lag_bytes <= MaximumAllowedLagBytes` where `MaximumAllowedLagBytes = 10485760` (10 MiB).
   - If replication lag exceeds that threshold or replication status is `UNKNOWN`, promotion is rejected.

2. **WAL LSN Catch-Up**:
   - The replica must catch up LSN flush (`flush_lsn >= primary_write_lsn`) before assuming primary role.

3. **Write Lease Revocation**:
   - The former primary instance's write lease (`write_lease_owner`) is revoked before replica promotion to prevent dual-primary writes.
   - After revocation the former primary status is `READ_ONLY` until it is later returned to service or deleted.

4. **Endpoint Routing**:
   - Promotion atomically swaps writer/reader endpoint addresses for the promoted replica and demoted primary.
   - Floating VIP route flush and gratuitous ARP are **not** part of promotion; those belong to Multi-AZ failover VIP migration only. Successful promotion evidence must not set `route_table_flushed` / `gratuitous_arp_sent`.

## Multi-AZ Failover Fencing

1. **Lease Acquisition**:
   - Failover workers must acquire an exclusive leader lease (`failover_leases`) with TTL 15 seconds before promoting a standby.

2. **Health Probe Isolation**:
   - Instance health is decided from a direct TCP probe to database port 5432, not from control-plane connection-pool latency alone.
   - Decision matrix:
     - Direct port reachable → healthy (`ok=true`, reason `INSTANCE_HEALTHY`).
     - Direct port unreachable when the only observed fault is control-plane pool lag → do not treat as instance failure (`ok=true`, reason `CONTROL_PLANE_LAG_IGNORED`).
     - Direct port unreachable for other reasons → unhealthy (`ok=false`).

3. **VIP Routing Migration**:
   - Floating VIP migration to the new primary flushes route tables and issues gratuitous ARP.
   - Successful migration evidence includes `status=MIGRATED`, `route_table_flushed=true`, and `gratuitous_arp_sent=true`.
