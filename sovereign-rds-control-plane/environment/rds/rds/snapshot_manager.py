"""Database snapshot creation, cross-region copy, and retention policy engine."""
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from rds.digest import compute_stable_digest

class SnapshotManager:
    """Manages DBInstance snapshots, retention policies, and cross-region copies."""

    def __init__(self, default_retention_days: int = 7):
        self.default_retention_days = default_retention_days

    def create_snapshot(
        self,
        instance: Dict[str, Any],
        snapshot_id: str,
        snapshot_type: str = "manual"
    ) -> Dict[str, Any]:
        """Create a new DBSnapshot manifest record."""
        return {
            "snapshot_id": snapshot_id,
            "instance_id": instance["instance_id"],
            "snapshot_type": snapshot_type,
            "status": "COMPLETED",
            "allocated_storage_gb": instance.get("allocated_storage_gb", 100),
            "redo_lsn": "0/01000000",
            "timeline_id": 1,
            "snapshot_time": datetime.now(timezone.utc).isoformat(),
        }

    def copy_snapshot(
        self,
        source_snapshot: Dict[str, Any],
        target_snapshot_id: str,
        target_region: str,
        kms_key_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Copy snapshot across regions or KMS encryption keys."""
        copied = dict(source_snapshot)
        copied["snapshot_id"] = target_snapshot_id
        copied["region"] = target_region
        copied["encrypted"] = True
        copied["kms_key_id"] = kms_key_id or "arn:aws:kms:us-east-1:100000000000:key/default"
        copied["copied_from_snapshot_id"] = source_snapshot["snapshot_id"]
        copied["snapshot_time"] = datetime.now(timezone.utc).isoformat()
        return copied

    def evaluate_retention_policy(
        self,
        snapshots: List[Dict[str, Any]],
        retention_days: int = 7
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Classify snapshots into retained vs expired candidates for cleanup."""
        retained = []
        expired = []
        now = datetime.now(timezone.utc)

        for snap in snapshots:
            if snap.get("snapshot_type") == "manual":
                retained.append(snap)
                continue

            snap_time = snap.get("snapshot_time")
            if isinstance(snap_time, str):
                snap_time = datetime.fromisoformat(snap_time)
            if snap_time.tzinfo is None:
                snap_time = snap_time.replace(tzinfo=timezone.utc)

            age_days = (now - snap_time).total_seconds() / 86400.0
            if age_days > retention_days:
                expired.append(snap)
            else:
                retained.append(snap)

        return retained, expired

    def export_snapshot_to_s3_manifest(
        self,
        snapshot: Dict[str, Any],
        s3_bucket: str,
        s3_prefix: str
    ) -> Dict[str, Any]:
        """Generate S3 export manifest for snapshot data export."""
        export_task_id = f"export-{snapshot['snapshot_id']}"
        manifest_payload = {
            "export_task_id": export_task_id,
            "snapshot_id": snapshot["snapshot_id"],
            "source_instance_id": snapshot["instance_id"],
            "s3_bucket": s3_bucket,
            "s3_prefix": s3_prefix,
            "allocated_storage_gb": snapshot.get("allocated_storage_gb", 100),
            "status": "COMPLETED",
        }
        manifest_payload["manifest_digest"] = compute_stable_digest(manifest_payload)
        return manifest_payload
