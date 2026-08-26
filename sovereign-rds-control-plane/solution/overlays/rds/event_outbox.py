"""EventBridge outbox notification manager with subscription category filtering and audit logging."""
import hashlib
from typing import Any, Dict, List
from rds.errors import EventOutboxError


class EventOutboxManager:
    """Manages event notification outbox dispatch, filtering, and audit logging."""

    @staticmethod
    def generate_event_identifier(source_type: str, source_id: str, event_time_iso: str, message: str) -> str:
        """Generate deterministic SHA-256 event identifier hash for deduplication."""
        raw = f"{source_type}:{source_id}:{event_time_iso}:{message}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    @staticmethod
    def filter_subscriptions_by_source(
        subscriptions: List[Dict[str, Any]],
        event_source_type: str,
        event_category: str
    ) -> List[Dict[str, Any]]:
        """Filter subscriptions matching exact SourceType and category."""
        matching = []
        for sub in subscriptions:
            if not sub.get("enabled", True):
                continue
            if sub.get("source_type") == event_source_type and sub.get("event_category") in (event_category, "all"):
                matching.append(sub)
        return matching

    @staticmethod
    def format_outbox_payload(
        event_id: str,
        event_identifier: str,
        source_type: str,
        source_id: str,
        category: str,
        message: str,
        event_time_iso: str
    ) -> Dict[str, Any]:
        """Format standardized EventBridge notification payload."""
        return {
            "version": "0",
            "id": event_id,
            "event_identifier": event_identifier,
            "detail_type": f"RDS DB {category.title()} Event",
            "source": f"aws.rds.{source_type}",
            "time": event_time_iso,
            "resources": [f"arn:aws:rds:us-east-1:100000000000:{source_type}:{source_id}"],
            "detail": {
                "EventCategories": [category],
                "SourceType": source_type.upper(),
                "SourceIdentifier": source_id,
                "Message": message,
            }
        }
