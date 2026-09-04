"""Rollout state checkpointing and recovery manager."""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Set


REQUIRED_CHECKPOINT_KEYS = ("ready", "upgrade_order", "steps")


def _is_valid_checkpoint(payload: Any) -> bool:
    if not isinstance(payload, dict):
        return False
    for key in REQUIRED_CHECKPOINT_KEYS:
        if key not in payload:
            return False
    if not isinstance(payload.get("ready"), list):
        return False
    if not isinstance(payload.get("upgrade_order"), list):
        return False
    if not isinstance(payload.get("steps"), list):
        return False
    return True


class CheckpointManager:
    """Manages step-by-step rollout progress state checkpoints for atomic recovery."""

    def __init__(self, checkpoint_path: Path):
        self.checkpoint_path = checkpoint_path

    def load_checkpoint(self) -> Optional[Dict[str, Any]]:
        """Load last saved rollout checkpoint if it exists and is well-formed."""
        if not self.checkpoint_path.is_file():
            return None
        try:
            payload = json.loads(self.checkpoint_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return None
        if not _is_valid_checkpoint(payload):
            return None
        return payload

    def save_checkpoint(self, state: Dict[str, Any]) -> None:
        """Save current rollout progress state atomically to checkpoint file."""
        if not _is_valid_checkpoint(state):
            # Normalize minimal shape rather than refusing mid-rollout.
            state = {
                "ready": list(state.get("ready") or []),
                "upgrade_order": list(state.get("upgrade_order") or []),
                "steps": list(state.get("steps") or []),
            }
        self.checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
        data = json.dumps(state, indent=2, sort_keys=True) + "\n"
        fd, tmp_name = tempfile.mkstemp(
            prefix=".checkpoint-",
            suffix=".tmp",
            dir=str(self.checkpoint_path.parent),
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(data)
                handle.flush()
                os.fsync(handle.fileno())
            Path(tmp_name).replace(self.checkpoint_path)
        finally:
            tmp_path = Path(tmp_name)
            if tmp_path.exists():
                try:
                    tmp_path.unlink()
                except OSError:
                    pass

    def clear_checkpoint(self) -> None:
        """Remove checkpoint file after successful upgrade completion."""
        if self.checkpoint_path.is_file():
            try:
                self.checkpoint_path.unlink()
            except OSError:
                pass

    def restore_ready_set(self) -> Set[str]:
        """Convenience helper returning the ready addon set from checkpoint."""
        prior = self.load_checkpoint() or {}
        return set(prior.get("ready") or [])

    def append_step_and_save(
        self,
        *,
        ready: Set[str],
        upgrade_order: List[str],
        steps: List[Dict[str, Any]],
    ) -> None:
        """Persist a step boundary used for restart recovery."""
        self.save_checkpoint(
            {
                "ready": sorted(ready),
                "upgrade_order": list(upgrade_order),
                "steps": list(steps),
            }
        )
