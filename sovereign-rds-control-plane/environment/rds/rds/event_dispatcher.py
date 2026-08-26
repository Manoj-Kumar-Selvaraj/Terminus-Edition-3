"""EventBridge delivery worker with subscription matching and retry handling."""
from typing import Any, Dict, List
from rds.event_outbox import EventOutboxManager

class EventDispatcher:
    """Dispatches pending outbox events to subscribed notification endpoints."""

    def __init__(self, max_retries: int = 5):
        self.max_retries = max_retries

    def process_event_dispatch(
        self,
        event: Dict[str, Any],
        subscriptions: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Match subscriptions and build delivery payload."""
        source_type = event.get("source_type", "db-instance")
        category = event.get("category", "notification")

        matching_subs = EventOutboxManager.filter_subscriptions_by_source(
            subscriptions, source_type, category
        )

        event_identifier = event.get(
            "event_identifier",
            EventOutboxManager.generate_event_identifier(
                source_type,
                event.get("source_identifier", ""),
                str(event.get("event_time", "")),
                event.get("message", "")
            )
        )

        payload = EventOutboxManager.format_outbox_payload(
            event.get("event_id", ""),
            event_identifier,
            source_type,
            event.get("source_identifier", ""),
            category,
            event.get("message", ""),
            str(event.get("event_time", ""))
        )

        return {
            "event_id": event.get("event_id"),
            "event_identifier": event_identifier,
            "matched_subscriptions": len(matching_subs),
            "payload": payload,
            "delivered": len(matching_subs) > 0,
        }
