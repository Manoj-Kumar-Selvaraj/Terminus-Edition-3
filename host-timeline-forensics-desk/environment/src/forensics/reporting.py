"""Authorized deterministic evidence snapshot publication."""
from __future__ import annotations
from pathlib import Path
from typing import Any
from .authz import AuthorizationService
from .canonical import canonical_json, sha256_bytes
from .config import get_settings
from .database import Database
from .metrics import metrics
from .models import ActorContext
from .readiness import ReadinessService


class EvidencePublisher:
    OUTPUTS = ("case-snapshot.json", "cases.jsonl", "coverage.jsonl", "evidence.jsonl", "custody.jsonl", "audit.jsonl", "health.json", "manifest.json")

    def __init__(self, database: Database, authz: AuthorizationService, readiness: ReadinessService,
                 output_dir: Path | None = None):
        self.db = database
        self.authz = authz
        self.readiness = readiness
        self.output_dir = output_dir or get_settings().output_dir

    def publish(self, context: ActorContext) -> dict[str, Any]:
        self.authz.require(context, "case:export")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        projection = self.authz.projection(context, alias="c")
        with self.db.transaction("REPEATABLE READ") as conn:
            conn.execute("SET TRANSACTION READ ONLY")
            cases = conn.execute(
                f"SELECT c.case_id,c.title,c.state,c.revision,c.opened_at,c.updated_at FROM cases c WHERE {projection[0]} ORDER BY c.case_id",
                projection[1],
            ).fetchall()
            case_ids = [row["case_id"] for row in cases]
            if case_ids:
                coverage = conn.execute(
                    "SELECT case_id,disposition,count(*)::int AS count FROM source_dispositions WHERE tenant_id=%s AND case_id=ANY(%s) GROUP BY case_id,disposition ORDER BY case_id,disposition",
                    (context.tenant_id, case_ids),
                ).fetchall()
                evidence = conn.execute(
                    "SELECT evidence_id,case_id,endpoint_id,source_id,item_id,attempt,digest,capture_time,traits FROM evidence_items WHERE tenant_id=%s AND case_id=ANY(%s) ORDER BY case_id,capture_time,source_id,evidence_id",
                    (context.tenant_id, case_ids),
                ).fetchall()
                custody = conn.execute(
                    "SELECT custody_sequence,custody_id,case_id,evidence_id,actor_id,action,event_digest,occurred_at FROM custody_events WHERE tenant_id=%s AND case_id=ANY(%s) ORDER BY case_id,custody_sequence",
                    (context.tenant_id, case_ids),
                ).fetchall()
                audit = conn.execute(
                    "SELECT audit_sequence,case_id,actor_id,action,decision,detail_digest,occurred_at FROM audit_events WHERE tenant_id=%s AND case_id=ANY(%s) ORDER BY audit_sequence",
                    (context.tenant_id, case_ids),
                ).fetchall()
            else:
                coverage = evidence = custody = audit = []
            health = self.readiness.snapshot()
        now = self.readiness.snapshot()["observed_at"]
        snapshot = {"schema_version": "snapshot-v1", "tenant_id": context.tenant_id, "generated_at": now,
                    "case_count": len(cases), "evidence_count": len(evidence), "health": health}
        tables = {
            "case-snapshot.json": canonical_json(snapshot) + "\n",
            "cases.jsonl": self._jsonl(cases),
            "coverage.jsonl": self._jsonl(coverage),
            "evidence.jsonl": self._jsonl(evidence),
            "custody.jsonl": self._jsonl(custody),
            "audit.jsonl": self._jsonl(audit),
            "health.json": canonical_json(health) + "\n",
        }
        files = []
        for name, content in tables.items():
            target = self.output_dir / name
            target.write_text(content, encoding="utf-8")
            files.append({"path": name, "sha256": sha256_bytes(content.encode()), "bytes": len(content.encode())})
        files.sort(key=lambda row: row["path"])
        manifest = {"version": 1, "tenant_id": context.tenant_id, "files": files}
        manifest_text = canonical_json(manifest) + "\n"
        (self.output_dir / "manifest.json").write_text(manifest_text, encoding="utf-8")
        metrics.inc("export_published", component="reporting")
        return manifest

    @staticmethod
    def _jsonl(rows) -> str:
        return "".join(canonical_json(dict(row)) + "\n" for row in rows)
