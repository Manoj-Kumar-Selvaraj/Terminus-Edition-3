"""Forensic timeline normalization while preserving source-time authority."""
from __future__ import annotations
from datetime import datetime, timezone
from typing import Any, Iterable
from psycopg.types.json import Jsonb
from .canonical import parse_utc
from .database import Database
from .errors import InvalidRequest
from .models import ActorContext
from .authz import AuthorizationService


class TimelineProjector:
    def __init__(self, database: Database, authorization: AuthorizationService):
        self.db = database
        self.authz = authorization

    def observe(self, *, tenant_id: str, case_id: str, item_id: str, attempt: int,
                source_id: str, event_time: str, offset_ms: int, uncertainty_ms: int,
                trait: str, payload: dict[str, Any], accepted: bool) -> str:
        source_time = parse_utc(event_time)
        normalized = source_time.timestamp() + offset_ms / 1000
        normalized_time = datetime.fromtimestamp(normalized, tz=timezone.utc)
        observation_id = f"obs_{item_id}_{attempt}_{source_id}_{int(source_time.timestamp() * 1000000)}"
        from .canonical import digest_json
        self.db.execute(
            "INSERT INTO event_observations(observation_id,tenant_id,case_id,item_id,attempt,source_id,source_time,normalized_time,time_uncertainty_ms,trait,event_payload,payload_digest,accepted,created_at) "
            "VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT(observation_id) DO NOTHING",
            (observation_id, tenant_id, case_id, item_id, attempt, source_id, source_time, normalized_time,
             max(0, int(uncertainty_ms)), trait, Jsonb(payload), digest_json(payload), bool(accepted), datetime.now(timezone.utc)),
        )
        return observation_id

    def case_timeline(self, context: ActorContext, case_id: str, *, limit: int = 1000,
                      include_unaccepted: bool = False) -> list[dict[str, Any]]:
        self.authz.require(context, "case:inspect", case_id)
        bounded = max(1, min(int(limit), 5000))
        accepted_filter = "" if include_unaccepted else "AND o.accepted=true"
        return self.db.query(
            "SELECT o.observation_id,o.item_id,o.attempt,o.source_id,o.source_time,o.normalized_time,o.time_uncertainty_ms,o.trait,o.event_payload "
            "FROM event_observations o WHERE o.tenant_id=%s AND o.case_id=%s " + accepted_filter +
            " ORDER BY o.normalized_time NULLS LAST,o.source_id,o.observation_id LIMIT %s",
            (context.tenant_id, case_id, bounded),
        )

    @staticmethod
    def merge_observations(observations: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
        """Stable-order mixed-source observations without discarding source timestamps."""
        rows = list(observations)
        for row in rows:
            if row.get("source_time") is not None and row.get("normalized_time") is None:
                raise InvalidRequest("normalized timeline time is required when source time exists")
        rows.sort(key=lambda row: (
            row.get("normalized_time") or datetime.max.replace(tzinfo=timezone.utc),
            str(row.get("source_id", "")),
            str(row.get("observation_id", "")),
        ))
        return rows
