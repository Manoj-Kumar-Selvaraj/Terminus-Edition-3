from __future__ import annotations

from src.records import Event, OpenSession
from src.runtime.keyed_state import SessionKeyedState


class SessionStore:
    """Partitioned in-memory map of open sessions keyed by session_key()."""

    def __init__(self, buckets: int = 32) -> None:
        self._state = SessionKeyedState(buckets=buckets)

    def lookup(self, tenant_id: str, user_id: str) -> OpenSession | None:
        return self._state.lookup(tenant_id, user_id)

    def put(self, session: OpenSession) -> None:
        self._state.put(session)

    def pop(self, tenant_id: str, user_id: str) -> OpenSession | None:
        return self._state.pop(tenant_id, user_id)

    def pop_key(self, key: tuple[str, str]) -> OpenSession | None:
        return self._state.pop_key(key)

    def items(self) -> list[tuple[tuple[str, str], OpenSession]]:
        return self._state.items()

    def as_dict(self) -> dict[tuple[str, str], OpenSession]:
        return self._state.as_dict()

    def load_from(self, sessions: dict[tuple[str, str], OpenSession]) -> None:
        self._state.load_from(sessions.values())

    def replace_state_map(self) -> dict[tuple[str, str], OpenSession]:
        return self.as_dict()

    def open_for_event(self, event: Event) -> OpenSession | None:
        return self.lookup(event.tenant_id, event.user_id)

    def stats(self) -> dict[str, int]:
        return self._state.stats()
