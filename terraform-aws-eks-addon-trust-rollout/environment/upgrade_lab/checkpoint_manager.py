"""Rollout state checkpointing and recovery manager."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional


class CheckpointManager:
    """Manages step-by-step rollout progress state checkpoints for atomic recovery."""

    def __init__(self, checkpoint_path: Path):
        self.checkpoint_path = checkpoint_path

    def load_checkpoint(self) -> Optional[Dict[str, Any]]:
        """Load last saved rollout checkpoint if it exists."""
        if not self.checkpoint_path.is_file():
            return None
        try:
            return json.loads(self.checkpoint_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return None

    def save_checkpoint(self, state: Dict[str, Any]) -> None:
        """Save current rollout progress state atomically to checkpoint file."""
        self.checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = self.checkpoint_path.with_suffix(".tmp")
        tmp_path.write_text(json.dumps(state, indent=2), encoding="utf-8")
        tmp_path.replace(self.checkpoint_path)

    def clear_checkpoint(self) -> None:
        """Remove checkpoint file after successful upgrade completion."""
        if self.checkpoint_path.is_file():
            try:
                self.checkpoint_path.unlink()
            except OSError:
                pass
