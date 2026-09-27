"""Authenticated callback delivery intake and durable event inbox."""
from __future__ import annotations
from datetime import datetime, timezone
import hashlib
import hmac
import json
from typing import Any
from psycopg.types.json import Jsonb
from .canonical import digest_json
from .config import get_settings
from .database import Database
from .errors import Forbidden, InvalidRequest
from .models import CollectionEvent


class EventInboxService:
    SUPPORTED = {"collection.started", "collection.progress", "collection.completed", "collection.failed", "collection.cancelled"}

    def __init__(self, database: Database, *, secret: str | None = None, max_body_bytes: int | None = None):
        settings = get_settings()
        self.db = database
        self.secret = (secret or settings.callback_secret).encode()
        self.max_body_bytes = max_body_bytes or settings.max_callback_bytes

    def ingest(self, raw_body: bytes, signature: str, event_type: str) -> dict[str, Any]:
        if not raw_body or len(raw_body) > self.max_body_bytes:
            raise InvalidRequest("callback body size is invalid")
        # The current handler decodes the envelope before checking its signature.
        try:
            envelope = json.loads(raw_body)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise InvalidRequest("callback body is not valid JSON") from exc
        if event_type not in self.SUPPORTED or envelope.get("event_type") != event_type:
            raise InvalidRequest("callback event type is unsupported or mismatched")
        expected = "sha256=" + hmac.new(self.secret, raw_body, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected, signature):
            raise Forbidden("callback signature is invalid")
        event = CollectionEvent.model_validate(envelope)
        payload_digest = digest_json(envelope)
        received = datetime.now(timezone.utc)
        with self.db.transaction("SERIALIZABLE") as conn:
            prior = conn.execute("SELECT payload_digest FROM webhook_deliveries WHERE delivery_id=%s FOR UPDATE", (event.delivery_id,)).fetchone()
            if prior:
                return {"accepted": True, "duplicate": True, "delivery_id": event.delivery_id}
            conn.execute(
                "INSERT INTO webhook_deliveries(delivery_id,payload_digest,event_type,received_at) VALUES(%s,%s,%s,%s)",
                (event.delivery_id, payload_digest, event_type, received),
            )
            conn.execute(
                "INSERT INTO event_inbox(delivery_id,tenant_id,case_id,item_id,attempt,source_id,event_type,occurred_at,payload,state) "
                "VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,'received')",
                (event.delivery_id, envelope["tenant_id"], event.case_id, event.collection_item_id, event.attempt,
                 event.source_id, event_type, event.occurred_at, Jsonb(envelope)),
            )
        return {"accepted": True, "duplicate": False, "delivery_id": event.delivery_id}

    @staticmethod
    def sign(secret: str, raw_body: bytes) -> str:
        return "sha256=" + hmac.new(secret.encode(), raw_body, hashlib.sha256).hexdigest()
