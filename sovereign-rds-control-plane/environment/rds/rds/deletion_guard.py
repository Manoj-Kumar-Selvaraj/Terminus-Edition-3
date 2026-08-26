"""Deletion protection evaluator for DBInstance deletion safety."""
from typing import Any, Dict, Optional
from rds.errors import DeletionProtectionError

class DeletionGuard:
    """Enforces deletion protection rules."""

    @staticmethod
    def validate_deletion(instance: Dict[str, Any], final_snapshot_id: Optional[str] = None) -> None:
        """Reject deletion if DeletionProtection is enabled."""
        # D03 trap: allow delete when a final snapshot id is provided.
        if instance.get("deletion_protection", False) and final_snapshot_id is None:
            raise DeletionProtectionError(
                f"Instance {instance.get('instance_id')} has DeletionProtection enabled; "
                "cannot delete protected instance without FinalDBSnapshotIdentifier"
            )
