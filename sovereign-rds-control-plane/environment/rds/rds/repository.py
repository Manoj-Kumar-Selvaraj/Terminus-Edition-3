"""Data repository layer for Sovereign RDS Control Plane."""
from typing import Any, Dict, List, Optional, Tuple
from rds import database

class RDSRepository:
    """Repository for control plane database operations."""

    async def get_instance(self, instance_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve database instance by ID."""
        query = "SELECT * FROM db_instances WHERE instance_id = %s"
        return await database.execute_one(query, (instance_id,))

    async def list_instances(self, account_id: str, region: str) -> List[Dict[str, Any]]:
        """List instances for account and region."""
        query = "SELECT * FROM db_instances WHERE account_id = %s AND region = %s ORDER BY instance_id"
        return await database.execute_query(query, (account_id, region)) or []

    async def update_instance_status(self, instance_id: str, status: str) -> int:
        """Update instance status."""
        query = "UPDATE db_instances SET status = %s, updated_at = NOW() WHERE instance_id = %s"
        return await database.execute_modify(query, (status, instance_id))

    async def clear_pending_reboot(self, instance_id: str) -> int:
        """Clear pending reboot parameters flag."""
        query = "UPDATE db_instances SET pending_reboot_parameters = FALSE, updated_at = NOW() WHERE instance_id = %s"
        return await database.execute_modify(query, (instance_id,))

    async def create_instance_record(self, query: str, record: Dict[str, Any]) -> int:
        """Create database instance record."""
        return await database.execute_modify(query, record)

    async def delete_instance_record(self, instance_id: str) -> int:
        """Delete instance record."""
        query = "DELETE FROM db_instances WHERE instance_id = %s"
        return await database.execute_modify(query, (instance_id,))

    async def execute_sql(self, sql: str, params: tuple) -> int:
        """Execute raw SQL modification."""
        return await database.execute_modify(sql, params)

    async def execute_one(self, query: str, params: tuple = None) -> Optional[Dict[str, Any]]:
        """Execute query returning a single row."""
        return await database.execute_one(query, params)

    async def get_parameter_group(self, group_name: str) -> Optional[Dict[str, Any]]:
        """Retrieve parameter group by name."""
        query = "SELECT * FROM db_parameter_groups WHERE parameter_group_name = %s"
        return await database.execute_one(query, (group_name,))

    async def create_parameter_group(self, group_name: str, family: str, description: str, params_json: Dict[str, Any]) -> int:
        """Create parameter group record."""
        import json
        query = """
            INSERT INTO db_parameter_groups (parameter_group_name, family, description, parameters_json)
            VALUES (%s, %s, %s, %s::jsonb)
        """
        return await database.execute_modify(query, (group_name, family, description, json.dumps(params_json)))

    async def update_parameter_group(self, group_name: str, params_json: Dict[str, Any]) -> int:
        """Update parameter group parameters."""
        import json
        query = "UPDATE db_parameter_groups SET parameters_json = %s::jsonb WHERE parameter_group_name = %s"
        return await database.execute_modify(query, (json.dumps(params_json), group_name))

    async def create_snapshot_record(self, record: Dict[str, Any]) -> int:
        """Create snapshot record."""
        query = """
            INSERT INTO db_snapshots (
                snapshot_id, instance_id, snapshot_type, status, allocated_storage_gb, redo_lsn, timeline_id
            ) VALUES (
                %(snapshot_id)s, %(instance_id)s, %(snapshot_type)s, %(status)s, %(allocated_storage_gb)s, %(redo_lsn)s, %(timeline_id)s
            )
        """
        return await database.execute_modify(query, record)

    async def get_snapshots(self, instance_id: str) -> List[Dict[str, Any]]:
        """List snapshots for an instance."""
        query = "SELECT * FROM db_snapshots WHERE instance_id = %s ORDER BY snapshot_time DESC"
        return await database.execute_query(query, (instance_id,)) or []

    async def get_wal_archives(self, instance_id: str) -> List[Dict[str, Any]]:
        """List WAL archives for an instance."""
        query = "SELECT * FROM wal_archives WHERE instance_id = %s ORDER BY timeline_id, sequence_number"
        return await database.execute_query(query, (instance_id,)) or []

    async def create_wal_archive(self, record: Dict[str, Any]) -> int:
        """Create WAL archive record."""
        query = """
            INSERT INTO wal_archives (
                instance_id, timeline_id, sequence_number, wal_file_name, start_lsn, end_lsn, start_time, end_time, size_bytes
            ) VALUES (
                %(instance_id)s, %(timeline_id)s, %(sequence_number)s, %(wal_file_name)s, %(start_lsn)s, %(end_lsn)s, %(start_time)s, %(end_time)s, %(size_bytes)s
            )
        """
        return await database.execute_modify(query, record)

    async def get_pending_outbox_events(self) -> List[Dict[str, Any]]:
        """Get pending outbox notification events."""
        query = "SELECT * FROM event_outbox WHERE status = 'PENDING' ORDER BY created_at LIMIT 50"
        return await database.execute_query(query) or []

    async def create_outbox_event(self, record: Dict[str, Any]) -> int:
        """Create outbox event notification."""
        query = """
            INSERT INTO event_outbox (
                event_id, event_identifier, source_type, source_identifier, category, message, status
            ) VALUES (
                %(event_id)s, %(event_identifier)s, %(source_type)s, %(source_identifier)s, %(category)s, %(message)s, %(status)s
            )
        """
        return await database.execute_modify(query, record)

    async def get_event_subscriptions(self, account_id: str) -> List[Dict[str, Any]]:
        """Get subscriptions for an account."""
        query = "SELECT * FROM event_subscriptions WHERE account_id = %s AND enabled = TRUE"
        return await database.execute_query(query, (account_id,)) or []

    async def create_event_subscription(self, record: Dict[str, Any]) -> int:
        """Create event subscription record."""
        query = """
            INSERT INTO event_subscriptions (
                subscription_id, account_id, source_type, event_category, target_endpoint, enabled
            ) VALUES (
                %(subscription_id)s, %(account_id)s, %(source_type)s, %(event_category)s, %(target_endpoint)s, %(enabled)s
            )
        """
        return await database.execute_modify(query, record)

    async def record_delivery_audit(self, event_id: str, sub_id: str, status: str, err: str = None) -> int:
        """Record event delivery audit log."""
        query = """
            INSERT INTO event_delivery_audit (event_id, subscription_id, delivery_status, error_message)
            VALUES (%s, %s, %s, %s)
        """
        return await database.execute_modify(query, (event_id, sub_id, status, err))

