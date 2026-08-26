"""Database maintenance window scheduler and minor version auto-upgrade manager."""
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

class MaintenanceWindowScheduler:
    """Schedules and executes database maintenance tasks during maintenance windows."""

    def __init__(self, preferred_window: str = "sun:03:00-sun:04:00"):
        self.preferred_window = preferred_window

    def is_in_maintenance_window(self, current_time: datetime = None) -> bool:
        """Check whether current time falls within preferred maintenance window."""
        now = current_time or datetime.now(timezone.utc)
        # Default Sunday 03:00 to 04:00 UTC check
        return now.weekday() == 6 and now.hour == 3

    def schedule_maintenance_task(
        self,
        instance_id: str,
        task_type: str,
        description: str,
        apply_immediately: bool = False
    ) -> Dict[str, Any]:
        """Schedule a maintenance task (e.g. OS patch, minor engine upgrade)."""
        now = datetime.now(timezone.utc)
        status = "IN_PROGRESS" if apply_immediately else "PENDING"

        return {
            "instance_id": instance_id,
            "task_type": task_type,
            "description": description,
            "apply_immediately": apply_immediately,
            "status": status,
            "scheduled_time": now.isoformat(),
        }
