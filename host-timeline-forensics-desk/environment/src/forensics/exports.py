"""Deterministic case export and retention operations."""
from __future__ import annotations
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any
from .authz import AuthorizationService
from .canonical import digest_json
from .config import get_settings
from .database import Database
from .errors import Forbidden, NotFound
from .models import ActorContext


class ExportService:
    def __init__(self, database: Database, authorization: AuthorizationService, output_dir: Path | None = None):
        self.db = database
        self.authz = authorization
        self.output_dir = output_dir or get_settings().output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def create(self, context: ActorContext, case_id: str, *, include_timeline: bool = True) -> dict[str, Any]:
        self.authz.require(context, "case:export", case_id)
        now = datetime.now(timezone.utc)
        case = self.db.one(
            "SELECT case_id,state,revision FROM cases WHERE tenant_id=%s AND case_id=%s",
            (context.tenant_id, case_id),
        )
        if case is None:
            raise NotFound("case is not visible")
        if case["state"] == "hold":
            raise Forbidden("case hold blocks export")
        export_id = "exp_" + digest_json([context.tenant_id, case_id, case["revision"], context.actor_id, now.isoformat()])[:24]
        rows = self.db.query(
            "SELECT evidence_id,endpoint_id,source_id,item_id,attempt,digest,capture_time,traits "
            "FROM evidence_items WHERE tenant_id=%s AND case_id=%s ORDER BY capture_time,source_id,evidence_id",
            (context.tenant_id, case_id),
        )
        dispositions = self.db.query(
            "SELECT item_id,endpoint_id,source_id,disposition,accepted_bytes,expected_bytes,terminal_reason "
            "FROM source_dispositions WHERE tenant_id=%s AND case_id=%s ORDER BY item_id",
            (context.tenant_id, case_id),
        )
        custody = self.db.query(
            "SELECT custody_id,evidence_id,actor_id,action,reason,event_digest,occurred_at "
            "FROM custody_events WHERE tenant_id=%s AND case_id=%s ORDER BY custody_sequence",
            (context.tenant_id, case_id),
        )
        body = {
            "schema_version": "manifest-v1",
            "export_id": export_id,
            "tenant_id": context.tenant_id,
            "case_id": case_id,
            "case_revision": case["revision"],
            "generated_at": now.isoformat(),
            "evidence": rows if include_timeline else [],
            "source_dispositions": dispositions,
            "custody": custody,
        }
        serialized = json.dumps(body, ensure_ascii=False, indent=2)
        digest = digest_json(body)
        target = self.output_dir / f"{export_id}.json"
        with self.db.transaction("SERIALIZABLE") as conn:
            conn.execute(
                "INSERT INTO export_jobs(export_id,tenant_id,case_id,requested_by,state,manifest_digest,object_path,item_count,created_at,published_at) "
                "VALUES(%s,%s,%s,%s,'published',%s,%s,%s,%s,%s)",
                (export_id, context.tenant_id, case_id, context.actor_id, digest, str(target), len(rows), now, now),
            )
            for ordinal, row in enumerate(rows):
                conn.execute(
                    "INSERT INTO export_artifacts(export_id,evidence_id,digest,byte_length,ordinal) "
                    "SELECT %s,e.evidence_id,e.digest,o.byte_length,%s FROM evidence_items e JOIN evidence_objects o USING(digest) WHERE e.evidence_id=%s",
                    (export_id, ordinal, row["evidence_id"]),
                )
        target.write_text(serialized, encoding="utf-8")
        return {"export_id": export_id, "case_id": case_id, "state": "published", "manifest_digest": digest, "item_count": len(rows), "path": str(target)}

    def get(self, context: ActorContext, case_id: str, export_id: str) -> dict[str, Any]:
        self.authz.require(context, "case:export", case_id)
        row = self.db.one(
            "SELECT export_id,state,manifest_digest,object_path,item_count,created_at,published_at "
            "FROM export_jobs WHERE tenant_id=%s AND case_id=%s AND export_id=%s",
            (context.tenant_id, case_id, export_id),
        )
        if row is None:
            raise NotFound("export is not visible")
        return row


class RetentionService:
    def __init__(self, database: Database):
        self.db = database

    def candidates(self, before: datetime, *, limit: int = 500) -> list[dict[str, Any]]:
        return self.db.query(
            "SELECT o.digest,o.object_path,o.created_at FROM evidence_objects o "
            "WHERE o.created_at<%s AND NOT EXISTS (SELECT 1 FROM evidence_items e JOIN case_holds h ON h.case_id=e.case_id AND h.tenant_id=e.tenant_id AND h.state='active' WHERE e.digest=o.digest) "
            "ORDER BY o.created_at LIMIT %s",
            (before, max(1, min(int(limit), 2000))),
        )

    def delete_unreferenced(self, digest: str) -> bool:
        with self.db.transaction("SERIALIZABLE") as conn:
            refs = conn.execute(
                "SELECT count(*) AS n FROM retention_references WHERE evidence_id IN (SELECT evidence_id FROM evidence_items WHERE digest=%s) AND (retain_until IS NULL OR retain_until>clock_timestamp())",
                (digest,),
            ).fetchone()["n"]
            if int(refs) > 0:
                return False
            held = conn.execute(
                "SELECT count(*) AS n FROM evidence_items e JOIN case_holds h USING(tenant_id,case_id) WHERE e.digest=%s AND h.state='active'",
                (digest,),
            ).fetchone()["n"]
            if int(held) > 0:
                return False
            conn.execute("DELETE FROM evidence_items WHERE digest=%s", (digest,))
            conn.execute("DELETE FROM evidence_objects WHERE digest=%s", (digest,))
            return True
