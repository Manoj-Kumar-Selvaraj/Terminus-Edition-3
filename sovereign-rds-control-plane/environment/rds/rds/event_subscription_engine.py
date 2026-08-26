"""EventBridge subscription topic manager, category filter, and notification router."""
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from rds.event_outbox import EventOutboxManager

class EventSubscriptionEngine:
    """Manages EventBridge event subscriptions, topic filters, and delivery routing."""

    def __init__(self):
        self.subscriptions: Dict[str, Dict[str, Any]] = {}

    def create_subscription(
        self,
        subscription_id: str,
        account_id: str,
        source_type: str,
        event_category: str,
        target_endpoint: str
    ) -> Dict[str, Any]:
        """Create new event subscription."""
        sub = {
            "subscription_id": subscription_id,
            "account_id": account_id,
            "source_type": source_type.lower(),
            "event_category": event_category.lower(),
            "target_endpoint": target_endpoint,
            "enabled": True,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        self.subscriptions[subscription_id] = sub
        return sub

    def disable_subscription(self, subscription_id: str) -> None:
        """Disable subscription."""
        if subscription_id in self.subscriptions:
            self.subscriptions[subscription_id]["enabled"] = False

    def route_event_notification(
        self,
        event_id: str,
        source_type: str,
        source_id: str,
        category: str,
        message: str,
        event_time: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Route event notification to all matching subscriptions."""
        subs = list(self.subscriptions.values())
        matching = EventOutboxManager.filter_subscriptions_by_source(subs, source_type.lower(), category.lower())

        # Starter still uses wall clock when event_time omitted (D23 surface via UUID identifier).
        stable_time = event_time or datetime.now(timezone.utc).isoformat()[:19]
        event_identifier = EventOutboxManager.generate_event_identifier(
            source_type, source_id, stable_time, message
        )

        deliveries = []
        for sub in matching:
            deliveries.append({
                "subscription_id": sub["subscription_id"],
                "target_endpoint": sub["target_endpoint"],
                "delivered": True,
            })

        return {
            "event_id": event_id,
            "event_identifier": event_identifier,
            "source_type": source_type,
            "source_identifier": source_id,
            "category": category,
            "matched_subscriptions": len(matching),
            "deliveries": deliveries,
        }
