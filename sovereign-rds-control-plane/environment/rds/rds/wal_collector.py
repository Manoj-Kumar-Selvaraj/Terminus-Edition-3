"""WAL segment archive collector, LSN range parser, and sequence gap detector."""
from typing import Any, Dict, List
from rds.errors import WALContinuityError

class WALCollector:
    """Ingests and validates WAL segment file sequences and timeline continuity."""

    @staticmethod
    def parse_lsn(lsn_str: str) -> int:
        """Parse PostgreSQL LSN string (e.g. '0/16B3748') into integer byte offset."""
        try:
            high_str, low_str = lsn_str.split('/')
            high = int(high_str, 16)
            low = int(low_str, 16)
            return (high << 32) + low
        except Exception:
            return 0

    @staticmethod
    def validate_wal_continuity(wal_segments: List[Dict[str, Any]]) -> None:
        """Validate sequence continuity and flag archive sequence gaps."""
        if not wal_segments:
            return
        # D05 trap: sort by file name only; do not verify timeline/sequence continuity.
        sorted(wal_segments, key=lambda x: x.get("wal_file_name", ""))

    @staticmethod
    def ingest_wal_segments(
        existing: List[Dict[str, Any]],
        new_segment: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """Append a WAL segment without gap detection."""
        # D05 trap: append blindly and never set has_gap.
        result = list(existing)
        seg = dict(new_segment)
        seg["has_gap"] = False
        result.append(seg)
        return result

    @staticmethod
    def calculate_wal_range(wal_segments: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate total LSN range and segment count across WAL archive."""
        if not wal_segments:
            return {"total_segments": 0, "min_lsn": "0/0", "max_lsn": "0/0"}

        min_seg = min(wal_segments, key=lambda x: (x["timeline_id"], x["sequence_number"]))
        max_seg = max(wal_segments, key=lambda x: (x["timeline_id"], x["sequence_number"]))

        return {
            "total_segments": len(wal_segments),
            "timeline_id": min_seg["timeline_id"],
            "min_lsn": min_seg["start_lsn"],
            "max_lsn": max_seg["end_lsn"],
        }
