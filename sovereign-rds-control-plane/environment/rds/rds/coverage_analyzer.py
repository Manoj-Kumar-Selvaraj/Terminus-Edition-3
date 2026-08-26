"""PITR WAL retention coverage analyzer, SLA verifier, and restoration gap reporter."""
from datetime import datetime, timezone
from typing import Any, Dict, List

class CoverageAnalyzer:
    """Analyzes WAL archive continuity, retention compliance, and restorable window bounds."""

    def __init__(self, retention_period_days: int = 7):
        self.retention_period_days = retention_period_days

    def analyze_wal_coverage(
        self,
        wal_segments: List[Dict[str, Any]],
        retention_days: int = 7
    ) -> Dict[str, Any]:
        """Analyze WAL archive continuity and compute restorable window bounds."""
        if not wal_segments:
            return {
                "has_coverage": False,
                "segment_count": 0,
                "earliest_restorable": None,
                "latest_restorable": None,
                "missing_gaps": [],
            }

        sorted_segs = sorted(wal_segments, key=lambda x: (x["timeline_id"], x["sequence_number"]))
        gaps = []

        for i in range(1, len(sorted_segs)):
            prev = sorted_segs[i - 1]
            curr = sorted_segs[i]
            if curr["timeline_id"] == prev["timeline_id"] and curr["sequence_number"] != prev["sequence_number"] + 1:
                gaps.append({
                    "timeline_id": curr["timeline_id"],
                    "missing_after": prev["sequence_number"],
                    "missing_before": curr["sequence_number"],
                    "gap_size_sequences": curr["sequence_number"] - prev["sequence_number"] - 1,
                })

        earliest = sorted_segs[0]["start_time"]
        latest = sorted_segs[-1]["end_time"]

        return {
            "has_coverage": len(gaps) == 0,
            "segment_count": len(sorted_segs),
            "earliest_restorable": earliest if isinstance(earliest, str) else earliest.isoformat(),
            "latest_restorable": latest if isinstance(latest, str) else latest.isoformat(),
            "total_gaps": len(gaps),
            "missing_gaps": gaps,
        }

    def calculate_retention_window_coverage(
        self,
        earliest_restorable_time: datetime,
        latest_restorable_time: datetime,
        required_retention_days: int = 7
    ) -> Dict[str, Any]:
        """Calculate total hours of continuous restorable coverage."""
        total_seconds = (latest_restorable_time - earliest_restorable_time).total_seconds()
        total_hours = round(total_seconds / 3600.0, 2)
        total_days = round(total_seconds / 86400.0, 2)

        meets_retention_sla = total_days >= float(required_retention_days)

        return {
            "earliest_restorable_time": earliest_restorable_time.isoformat(),
            "latest_restorable_time": latest_restorable_time.isoformat(),
            "coverage_hours": total_hours,
            "coverage_days": total_days,
            "required_retention_days": required_retention_days,
            "meets_retention_sla": meets_retention_sla,
        }

    def verify_backup_sla(
        self,
        snapshots: List[Dict[str, Any]],
        max_backup_age_hours: int = 24
    ) -> Dict[str, Any]:
        """Verify snapshot recency against backup SLA."""
        if not snapshots:
            return {"sla_met": False, "latest_snapshot_age_hours": None, "total_snapshots": 0}

        latest_snap = max(snapshots, key=lambda x: x["snapshot_time"])
        snap_time = latest_snap["snapshot_time"]
        if isinstance(snap_time, str):
            snap_time = datetime.fromisoformat(snap_time)

        now = datetime.now(timezone.utc)
        if snap_time.tzinfo is None:
            snap_time = snap_time.replace(tzinfo=timezone.utc)

        age_hours = (now - snap_time).total_seconds() / 3600.0
        sla_met = age_hours <= max_backup_age_hours

        return {
            "sla_met": sla_met,
            "latest_snapshot_id": latest_snap["snapshot_id"],
            "latest_snapshot_age_hours": round(age_hours, 2),
            "total_snapshots": len(snapshots),
        }
