"""Startup recovery and reconciliation of durable work/evidence boundaries."""
from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from .database import Database
from .errors import IntegrityFailure
from .queueing import QueueService
from .readiness import ReadinessService


class RecoveryManager:
    def __init__(self, database: Database, queue: QueueService, readiness: ReadinessService,
                 evidence_root: Path):
        self.db = database
        self.queue = queue
        self.readiness = readiness
        self.evidence_root = evidence_root

    def recover(self) -> dict[str, Any]:
        migrations = self.db.migrate()
        expired = self.queue.recover_expired_claims()
        missing_objects = self._find_missing_objects()
        orphan_objects = self._find_orphan_objects()
        inbox = self.db.one("SELECT count(*) AS n FROM event_inbox WHERE state='received'") or {"n": 0}
        health = self.readiness.snapshot()
        return {
            "migrations_applied": migrations,
            "expired_claims_recovered": expired,
            "missing_evidence_objects": missing_objects,
            "orphan_evidence_objects": orphan_objects,
            "inbox_pending": int(inbox["n"]),
            "readiness": health,
            "recovered_at": datetime.now(timezone.utc).isoformat(),
        }

    def _find_missing_objects(self) -> list[str]:
        rows = self.db.query("SELECT digest,object_path FROM evidence_objects ORDER BY digest")
        return [row["digest"] for row in rows if not (self.evidence_root / row["object_path"]).is_file()]

    def _find_orphan_objects(self) -> list[str]:
        known = {row["object_path"] for row in self.db.query("SELECT object_path FROM evidence_objects")}
        found: list[str] = []
        if not self.evidence_root.exists():
            return found
        for path in self.evidence_root.glob("*/*.bin"):
            try:
                relative = str(path.relative_to(self.evidence_root))
            except ValueError as exc:
                raise IntegrityFailure("evidence path escaped object root") from exc
            if relative not in known:
                found.append(relative)
        return sorted(found)
