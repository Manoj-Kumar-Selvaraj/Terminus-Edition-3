"""Self-contained offline bundle validation and case-scoped intake."""
from __future__ import annotations
import hashlib
import hmac
import json
from pathlib import Path
from typing import Any
from .canonical import digest_json, normalize_case_id, normalize_endpoint_id, normalize_source_id
from .errors import Forbidden, IntegrityFailure, InvalidRequest, NotFound
from .events import EventInboxService
from .models import ActorContext
from .authz import AuthorizationService
from .source_catalog import SourceCatalog

MAX_BUNDLE_BYTES = 16 * 1024 * 1024
MAX_EVENTS_PER_BUNDLE = 5000


class OfflineIntake:
    def __init__(self, authorization: AuthorizationService, events: EventInboxService,
                 catalog: SourceCatalog | None = None):
        self.authz = authorization
        self.events = events
        self.catalog = catalog or SourceCatalog()

    def inspect(self, path: Path) -> dict[str, Any]:
        if not path.is_file():
            raise NotFound("offline bundle is not available")
        size = path.stat().st_size
        if size <= 0 or size > MAX_BUNDLE_BYTES:
            raise InvalidRequest("offline bundle size is outside supported bounds")
        try:
            bundle = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise InvalidRequest("offline bundle is not valid UTF-8 JSON") from exc
        if not isinstance(bundle, dict):
            raise InvalidRequest("offline bundle must be one JSON object")
        required = {"schema_version", "delivery_id", "tenant_id", "case_id", "endpoint_id", "source_id", "plan_id", "item_id", "attempt", "events", "manifest_digest"}
        if set(bundle) != required:
            raise InvalidRequest("offline bundle fields do not match the published envelope")
        if bundle["schema_version"] != "offline-bundle-v1":
            raise InvalidRequest("offline bundle version is unsupported")
        events = bundle["events"]
        if not isinstance(events, list) or not events or len(events) > MAX_EVENTS_PER_BUNDLE:
            raise InvalidRequest("offline bundle event count is invalid")
        body = {key: value for key, value in bundle.items() if key != "manifest_digest"}
        actual = digest_json(body)
        if not hmac.compare_digest(actual, str(bundle["manifest_digest"])):
            raise IntegrityFailure("offline bundle manifest digest does not match its payload")
        return bundle

    def ingest(self, context: ActorContext, path: Path, *, signature: str) -> dict[str, Any]:
        bundle = self.inspect(path)
        self.authz.require(context, "case:collect", normalize_case_id(bundle["case_id"]))
        if context.tenant_id != bundle["tenant_id"]:
            raise Forbidden("offline bundle tenant does not match actor tenant")
        endpoint_id = normalize_endpoint_id(bundle["endpoint_id"])
        source_id = normalize_source_id(bundle["source_id"])
        digest = bundle["manifest_digest"]
        signed = f"{bundle['delivery_id']}:{digest}".encode()
        expected = "sha256=" + hmac.new(self.events.secret, signed, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected, signature):
            raise Forbidden("offline bundle signature is invalid")
        accepted = 0
        for ordinal, payload in enumerate(bundle["events"]):
            envelope = {
                "event_type": "collection.completed" if payload.get("status") in {"complete", "partial"} else "collection.failed",
                "delivery_id": f"{bundle['delivery_id']}:{ordinal}",
                "tenant_id": context.tenant_id,
                "case_id": bundle["case_id"],
                "endpoint_id": endpoint_id,
                "source_id": source_id,
                "plan_id": bundle["plan_id"],
                "collection_item_id": bundle["item_id"],
                "attempt": bundle["attempt"],
                "status": payload.get("status", "partial"),
                "occurred_at": payload.get("occurred_at"),
                "payload_digest": digest_json(payload),
                "evidence": payload.get("evidence", []),
            }
            raw = json.dumps(envelope, sort_keys=True, separators=(",", ":")).encode()
            accepted += int(self.events.ingest(raw, EventInboxService.sign(self.events.secret.decode(), raw), envelope["event_type"])["accepted"])
        return {"delivery_id": bundle["delivery_id"], "accepted_events": accepted, "bundle_digest": digest}
