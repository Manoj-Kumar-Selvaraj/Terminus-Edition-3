"""Instance state machine, transition validator, and lock coordinator."""
from typing import Any, Dict, Set
from rds.errors import InvalidInstanceStateError

class InstanceStateMachine:
    """Enforces valid DBInstance status transitions."""

    VALID_TRANSITIONS: Dict[str, Set[str]] = {
        "CREATING": {"AVAILABLE", "FAILED"},
        "AVAILABLE": {"MODIFYING", "REBOOTING", "BACKING_UP", "STOPPING", "FAILOVER", "DELETING", "READ_ONLY"},
        "MODIFYING": {"AVAILABLE", "FAILED"},
        "REBOOTING": {"AVAILABLE", "FAILED"},
        "BACKING_UP": {"AVAILABLE", "FAILED"},
        "STOPPING": {"STOPPED", "FAILED"},
        "STOPPED": {"STARTING", "DELETING"},
        "STARTING": {"AVAILABLE", "FAILED"},
        "FAILOVER": {"AVAILABLE", "FAILED"},
        "READ_ONLY": {"AVAILABLE", "DELETING"},
        "DELETING": {"DELETED", "FAILED"},
        "DELETED": set(),
        "FAILED": {"REBOOTING", "DELETING"},
    }

    @classmethod
    def validate_transition(cls, current_status: str, target_status: str) -> None:
        """Validate whether status transition is permitted."""
        allowed = cls.VALID_TRANSITIONS.get(current_status, set())
        if target_status not in allowed:
            raise InvalidInstanceStateError(
                f"Invalid DBInstance status transition from '{current_status}' to '{target_status}'. "
                f"Allowed target statuses: {sorted(list(allowed))}"
            )

    @classmethod
    def can_transition(cls, current_status: str, target_status: str) -> bool:
        """Check whether status transition is permitted."""
        allowed = cls.VALID_TRANSITIONS.get(current_status, set())
        return target_status in allowed
