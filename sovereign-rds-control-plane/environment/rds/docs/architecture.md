# Sovereign RDS Control Plane Architecture

The sovereign RDS control plane replaces AWS RDS management APIs for on-premise or cloud-sovereign environments.

## Component Architecture

1. **API Server Daemon (`rdsd`)**:
   - Listens on HTTP port 8080.
   - Provides REST endpoints for DBInstances, DBParameterGroups, DBSnapshots, and EventSubscriptions.
   - Enforces multi-tenant account and region isolation.

2. **Worker Daemon (`rds-worker`)**:
   - Runs background tasks: WAL segment sequence validation, replication lag monitoring, Multi-AZ failover lease coordination, and EventBridge outbox notification dispatch.

3. **CLI Tool (`rdsctl`)**:
   - Operator CLI interface for managing DB instances, snapshots, parameter groups, and generating state reports.

4. **Estate Generator (`generate-estate`)**:
   - Populates control plane database with 14,800+ primary records (DB instances, parameter groups, WAL manifests, snapshots, event subscriptions, telemetry).
