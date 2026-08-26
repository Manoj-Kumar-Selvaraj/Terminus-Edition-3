"""Deletion protection evaluator for DBInstance deletion safety."""
from typing import Any, Dict, Optional
from rds.errors import DeletionProtectionError


class DeletionGuard:
    """Enforces deletion protection rules."""

    @staticmethod
    def validate_deletion(instance: Dict[str, Any], final_snapshot_id: Optional[str] = None) -> None:
        """Reject deletion if DeletionProtection is enabled regardless of final snapshot."""
        if instance.get("deletion_protection", False):
            raise DeletionProtectionError(
                f"Instance {instance.get('instance_id')} has DeletionProtection enabled; "
                "cannot delete protected instance"
            )
