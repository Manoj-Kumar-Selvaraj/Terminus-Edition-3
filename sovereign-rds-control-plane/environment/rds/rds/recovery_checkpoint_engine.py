"""Transaction WAL checkpoint recorder and crash recovery replay coordinator."""
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from rds.checkpoint_manager import CheckpointManager
from rds.errors import CheckpointError

class RecoveryCheckpointEngine:
    """Coordinates WAL transaction checkpoints and crash recovery replay deduplication."""

    def __init__(self, checkpoint_dir: Path):
        self.mgr = CheckpointManager(checkpoint_dir)

    def record_operation_start(self, operation_id: str, op_type: str, instance_id: str) -> str:
        """Record checkpoint prior to executing control plane mutation."""
        checkpoint_id = f"chk-{operation_id}"
        state = {
            "checkpoint_id": checkpoint_id,
            "operation_id": operation_id,
            "operation_type": op_type,
            "instance_id": instance_id,
            "status": "IN_PROGRESS",
        }
        self.mgr.save_checkpoint(checkpoint_id, state)
        return checkpoint_id

    def record_operation_commit(self, checkpoint_id: str, result_state: Dict[str, Any]) -> None:
        """Record atomic transaction commit checkpoint."""
        checkpoint = self.mgr.load_checkpoint(checkpoint_id) or {}
        checkpoint["status"] = "COMMITTED"
        checkpoint["result"] = result_state
        self.mgr.save_checkpoint(checkpoint_id, checkpoint)

    def verify_recovery_state(self, operation_id: str) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """Verify whether operation was already committed prior to crash restart."""
        checkpoint_id = f"chk-{operation_id}"
        chk = self.mgr.load_checkpoint(checkpoint_id)
        if not chk:
            return False, None
        is_committed = (chk.get("status") == "COMMITTED")
        return is_committed, chk.get("result")
