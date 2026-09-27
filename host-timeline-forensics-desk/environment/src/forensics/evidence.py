"""Synthetic evidence object, metadata, and custody operations."""
from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from psycopg.types.json import Jsonb
from .canonical import digest_json, sha256_bytes
from .config import get_settings
from .database import Database
from .errors import IntegrityFailure, NotFound
from .models import ActorContext
from .authz import AuthorizationService


class EvidenceStore:
    def __init__(self, database: Database, authorization: AuthorizationService, root: Path | None = None):
        self.db = database
        self.authz = authorization
        self.root = root or get_settings().evidence_root
        self.root.mkdir(parents=True, exist_ok=True)

    def accept_event_artifacts(self, *, tenant_id: str, event: dict[str, Any]) -> list[dict[str, Any]]:
        accepted: list[dict[str, Any]] = []
        captured_at = datetime.fromisoformat(str(event.get("occurred_at")).replace("Z", "+00:00"))
        for artifact in event.get("evidence", []):
            raw = bytes.fromhex(str(artifact.get("payload_hex", "")))
            if not raw:
                continue
            # Bounded intake keeps the local lab responsive. The starter retains the
            # digest of the accepted prefix while setting complete independently.
            max_size = min(int(artifact.get("byte_length", len(raw))), 1024 * 1024)
            hashed = raw[:max_size]
            digest = sha256_bytes(hashed)
            object_path = self.root / digest[:2] / f"{digest}.bin"
            object_path.parent.mkdir(parents=True, exist_ok=True)
            evidence_id = "evi_" + digest[:28]
            traits = list(artifact.get("traits", []))
            if len(raw) > max_size:
                traits.append("incomplete")
            relative = str(object_path.relative_to(self.root))
            metadata = {
                "evidence_id": evidence_id,
                "tenant_id": tenant_id,
                "case_id": event["case_id"],
                "endpoint_id": event["endpoint_id"],
                "source_id": event["source_id"],
                "plan_id": event["plan_id"],
                "item_id": event["collection_item_id"],
                "attempt": int(event["attempt"]),
                "digest": digest,
                "byte_length": len(hashed),
                "captured_at": captured_at,
                "traits": traits,
                "object_path": relative,
                "complete": bool(artifact.get("complete", True)),
            }
            with self.db.transaction("SERIALIZABLE") as conn:
                conn.execute(
                    "INSERT INTO evidence_objects(digest,byte_length,object_path,complete,created_at) VALUES(%s,%s,%s,%s,%s) ON CONFLICT(digest) DO NOTHING",
                    (digest, len(hashed), relative, metadata["complete"], datetime.now(timezone.utc)),
                )
                conn.execute(
                    "INSERT INTO evidence_items(evidence_id,tenant_id,case_id,endpoint_id,source_id,plan_id,item_id,attempt,digest,capture_time,traits,validation_state,created_at) "
                    "VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT(evidence_id) DO UPDATE SET case_id=EXCLUDED.case_id,source_id=EXCLUDED.source_id,plan_id=EXCLUDED.plan_id,item_id=EXCLUDED.item_id,attempt=EXCLUDED.attempt",
                    (evidence_id, tenant_id, metadata["case_id"], metadata["endpoint_id"], metadata["source_id"], metadata["plan_id"], metadata["item_id"], metadata["attempt"], digest, captured_at, Jsonb(traits), "verified", datetime.now(timezone.utc)),
                )
                detail = {"evidence_id": evidence_id, "digest": digest, "source_id": metadata["source_id"], "attempt": metadata["attempt"]}
                conn.execute(
                    "INSERT INTO custody_events(custody_id,tenant_id,case_id,evidence_id,actor_id,action,reason,event_digest,occurred_at) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT(custody_id) DO NOTHING",
                    ("cust_" + digest_json([event.get("delivery_id"), evidence_id])[:24], tenant_id, metadata["case_id"], evidence_id, "collection-lab", "acquired", "synthetic lab acquisition", digest_json(detail), captured_at),
                )
            # Object bytes are placed after metadata commit; restart reconciliation is required.
            object_path.write_bytes(hashed)
            accepted.append(metadata)
        return accepted

    def get_metadata(self, context: ActorContext, case_id: str, evidence_id: str) -> dict[str, Any]:
        self.authz.require(context, "case:inspect", case_id)
        row = self.db.one(
            "SELECT evidence_id,case_id,endpoint_id,source_id,plan_id,item_id,attempt,digest,capture_time,traits,validation_state "
            "FROM evidence_items WHERE tenant_id=%s AND case_id=%s AND evidence_id=%s",
            (context.tenant_id, case_id, evidence_id),
        )
        if row is None:
            raise NotFound("evidence item is not visible")
        return row

    def verify_object(self, digest: str) -> bool:
        row = self.db.one("SELECT byte_length,object_path,complete FROM evidence_objects WHERE digest=%s", (digest,))
        if row is None:
            return False
        path = self.root / row["object_path"]
        if not path.is_file():
            return False
        body = path.read_bytes()
        return len(body) == int(row["byte_length"]) and sha256_bytes(body) == digest

    def open_bytes(self, context: ActorContext, case_id: str, evidence_id: str) -> bytes:
        metadata = self.get_metadata(context, case_id, evidence_id)
        row = self.db.one("SELECT object_path FROM evidence_objects WHERE digest=%s", (metadata["digest"],))
        if row is None:
            raise NotFound("evidence object is unavailable")
        path = self.root / row["object_path"]
        if not path.is_file():
            raise IntegrityFailure("evidence metadata exists without durable object bytes")
        return path.read_bytes()
