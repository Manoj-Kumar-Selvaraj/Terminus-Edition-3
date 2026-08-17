from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Event:
    event_id: str
    tenant_id: str
    user_id: str
    event_time_ms: int
    payload: str
    line_no: int

    @property
    def key(self) -> tuple[str, str]:
        return (self.tenant_id, self.user_id)


@dataclass
class OpenSession:
    tenant_id: str
    user_id: str
    start_ms: int
    last_event_time_ms: int
    event_ids: list[str] = field(default_factory=list)

    def key(self) -> tuple[str, str]:
        return (self.tenant_id, self.user_id)

    def to_dict(self) -> dict[str, Any]:
        return {
            "tenant_id": self.tenant_id,
            "user_id": self.user_id,
            "start_ms": int(self.start_ms),
            "last_event_time_ms": int(self.last_event_time_ms),
            "event_ids": list(self.event_ids),
        }

    @staticmethod
    def from_dict(raw: dict[str, Any]) -> "OpenSession":
        ids = raw.get("event_ids") or []
        return OpenSession(
            tenant_id=str(raw["tenant_id"]),
            user_id=str(raw["user_id"]),
            start_ms=int(raw["start_ms"]),
            last_event_time_ms=int(raw["last_event_time_ms"]),
            event_ids=[str(x) for x in ids],
        )

    def accept(self, event_id: str, event_time_ms: int) -> None:
        self.event_ids.append(event_id)
        if event_time_ms > self.last_event_time_ms:
            self.last_event_time_ms = event_time_ms
