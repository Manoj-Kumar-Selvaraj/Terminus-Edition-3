# Sovereign RDS Control Plane Architecture

On-lab stand-in for AWS RDS management APIs. Runtime code lives under `/app/rds`.

## Processes

| Binary | Role |
|--------|------|
| `rdsd` | HTTP :8080 — instances, parameter groups, snapshots, event subscriptions; tenant-scoped describe/list |
| `rds-worker` | WAL continuity, replica lag, failover leases, outbox dispatch |
| `rdsctl` | Operator CLI and report generation |
| `generate-estate` | Seeds the fixed lab estate into PostgreSQL 16 |

Protocol detail (PITR windows, parameter apply modes, promotion/failover fencing) is in the sibling contracts in this directory.
