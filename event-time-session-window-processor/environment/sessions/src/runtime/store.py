from __future__ import annotations

from src.keys.partition import partition_id
from src.keys.session_key import session_key
from src.records import Event, OpenSession


class SessionStore:
    """Partitioned in-memory map of open sessions keyed by session_key()."""

    def __init__(self, buckets: int = 32) -> None:
        self.buckets = int(buckets)
        self._parts: list[dict[tuple[str, str], OpenSession]] = [
            {} for _ in range(self.buckets)
        ]

    def _part(self, tenant_id: str, user_id: str) -> dict[tuple[str, str], OpenSession]:
        idx = partition_id(tenant_id, user_id, self.buckets)
        return self._parts[idx]

    def lookup(self, tenant_id: str, user_id: str) -> OpenSession | None:
        key = session_key(tenant_id, user_id)
        return self._part(tenant_id, user_id).get(key)

    def put(self, session: OpenSession) -> None:
        key = session_key(session.tenant_id, session.user_id)
        self._part(session.tenant_id, session.user_id)[key] = session

    def pop(self, tenant_id: str, user_id: str) -> OpenSession | None:
        key = session_key(tenant_id, user_id)
        return self._part(tenant_id, user_id).pop(key, None)

    def pop_key(self, key: tuple[str, str]) -> OpenSession | None:
        tenant_id, user_id = key
        if tenant_id == "*":
            for part in self._parts:
                if key in part:
                    return part.pop(key)
            return None
        return self.pop(tenant_id, user_id)

    def items(self) -> list[tuple[tuple[str, str], OpenSession]]:
        out: list[tuple[tuple[str, str], OpenSession]] = []
        for part in self._parts:
            out.extend(part.items())
        return out

    def as_dict(self) -> dict[tuple[str, str], OpenSession]:
        merged: dict[tuple[str, str], OpenSession] = {}
        for part in self._parts:
            merged.update(part)
        return merged

    def load_from(self, sessions: dict[tuple[str, str], OpenSession]) -> None:
        for sess in sessions.values():
            self.put(sess)

    def replace_state_map(self) -> dict[tuple[str, str], OpenSession]:
        return self.as_dict()

    def open_for_event(self, event: Event) -> OpenSession | None:
        return self.lookup(event.tenant_id, event.user_id)
