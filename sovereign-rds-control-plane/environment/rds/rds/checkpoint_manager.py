"""Control plane transaction WAL checkpoint manager for crash recovery and replay deduplication."""
import json
from pathlib import Path
from typing import Any, Dict, List, Optional
from rds.errors import CheckpointError

class CheckpointManager:
    """Manages atomic transaction WAL state checkpoints for crash recovery."""

    def __init__(self, checkpoint_dir: Path):
        self.checkpoint_dir = checkpoint_dir
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)

    def save_checkpoint(self, checkpoint_id: str, state: Dict[str, Any]) -> None:
        """Save atomic state checkpoint to file with atomic replace."""
        file_path = self.checkpoint_dir / f"{checkpoint_id}.json"
        tmp_path = file_path.with_suffix(".tmp")
        tmp_path.write_text(json.dumps(state, indent=2, sort_keys=True), encoding="utf-8")
        tmp_path.replace(file_path)

    def load_checkpoint(self, checkpoint_id: str) -> Optional[Dict[str, Any]]:
        """Load state checkpoint if exists."""
        file_path = self.checkpoint_dir / f"{checkpoint_id}.json"
        if not file_path.is_file():
            return None
        try:
            return json.loads(file_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as e:
            raise CheckpointError(f"Corrupt checkpoint file {file_path}: {e}")

    def list_checkpoints(self) -> List[str]:
        """List all available checkpoint IDs in order."""
        return sorted([p.stem for p in self.checkpoint_dir.glob("*.json")])

    def is_operation_completed(self, operation_id: str) -> bool:
        """Check if operation has completed checkpoint recorded."""
        file_path = self.checkpoint_dir / f"{operation_id}.json"
        return file_path.is_file()
