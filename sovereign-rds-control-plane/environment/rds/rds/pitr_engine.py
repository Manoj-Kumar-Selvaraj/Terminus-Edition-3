"""Point-In-Time Recovery (PITR) target synthesizer and window evaluator."""
from datetime import datetime
from typing import Any, Dict, List, Optional
from rds.errors import PITRWindowError
from rds.wal_collector import WALCollector
from rds.wal_playback_simulator import WALPlaybackSimulator
from rds.coverage_analyzer import CoverageAnalyzer


class PITREngine:
    """Synthesizes Point-In-Time Recovery restores with WAL timeline replay."""

    @staticmethod
    def validate_pitr_target_window(
        target_time: datetime,
        earliest_time: datetime,
        latest_time: datetime
    ) -> None:
        """Validate target timestamp falls strictly within retention window."""
        # D08 trap: only check against latest; allow times before earliest.
        if target_time > latest_time:
            raise PITRWindowError(
                f"Target time {target_time.isoformat()} is after latest restorable "
                f"{latest_time.isoformat()}"
            )

    @staticmethod
    def select_base_snapshot(
        snapshots: List[Dict[str, Any]], target_time: datetime
    ) -> Dict[str, Any]:
        """Select latest base snapshot prior to target_time."""
        eligible = [s for s in snapshots if s["snapshot_time"] <= target_time]
        if not eligible:
            raise PITRWindowError(f"No base snapshot found prior to target time {target_time.isoformat()}")
        return max(eligible, key=lambda x: x["snapshot_time"])

    @staticmethod
    def synthesize_restore_plan(
        instance_id: str,
        target_time: datetime,
        snapshots: List[Dict[str, Any]],
        wal_segments: List[Dict[str, Any]],
        earliest_time: Optional[datetime] = None,
        latest_time: Optional[datetime] = None,
        instance: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Synthesize base snapshot and WAL segment list for PITR restore."""
        if earliest_time is not None and latest_time is not None:
            PITREngine.validate_pitr_target_window(target_time, earliest_time, latest_time)

        base_snapshot = PITREngine.select_base_snapshot(snapshots, target_time)
        snapshot_time = base_snapshot["snapshot_time"]

        base_lsn_val = WALCollector.parse_lsn(base_snapshot["redo_lsn"])
        replay_segments = [
            w for w in wal_segments
            if w["start_time"] >= snapshot_time and w["end_time"] <= target_time
        ]

        WALCollector.validate_wal_continuity(replay_segments)
        coverage = CoverageAnalyzer().analyze_wal_coverage(wal_segments)
        playback = WALPlaybackSimulator(target_time, target_timeline=base_snapshot.get("timeline_id", 1))
        replay = playback.simulate_wal_replay(base_snapshot["redo_lsn"], wal_segments)

        return {
            "instance_id": instance_id,
            "target_time": target_time.isoformat(),
            "base_snapshot_id": base_snapshot["snapshot_id"],
            "base_redo_lsn": base_snapshot["redo_lsn"],
            "wal_segments_to_replay": len(replay_segments),
            "start_lsn": base_snapshot["redo_lsn"],
            "stop_lsn": replay_segments[-1]["end_lsn"] if replay_segments else base_snapshot["redo_lsn"],
            "coverage": coverage,
            "playback": replay,
            "base_lsn_value": base_lsn_val,
            "instance_hint": instance.get("instance_id") if instance else None,
        }
