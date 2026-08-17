from __future__ import annotations

from dataclasses import dataclass, field

from src.config import ProcessorConfig
from src.records import OpenSession
from src.windows.diagnostics import eligible_for_watermark_close, watermark_close_end


@dataclass
class EventTimeTimers:
    """Event-time gap timers keyed by session identity. Wall clock is not consulted."""

    gap_ms: int
    pending: dict[tuple[str, str], int] = field(default_factory=dict)

    @classmethod
    def from_config(cls, cfg: ProcessorConfig) -> "EventTimeTimers":
        return cls(gap_ms=int(cfg.session_gap_ms))

    def arm(self, session: OpenSession) -> None:
        key = (session.tenant_id, session.user_id)
        self.pending[key] = int(session.last_event_time_ms) + int(self.gap_ms)

    def clear(self, tenant_id: str, user_id: str) -> None:
        self.pending.pop((tenant_id, user_id), None)

    def due(self, comparison_w: int) -> list[tuple[str, str, int]]:
        out: list[tuple[str, str, int]] = []
        for key, fire_ms in list(self.pending.items()):
            if fire_ms <= int(comparison_w):
                out.append((key[0], key[1], fire_ms))
        out.sort()
        return out

    def sync_from_store(
        self, sessions: dict[tuple[str, str], OpenSession], cfg: ProcessorConfig, comparison_w: int
    ) -> list[tuple[tuple[str, str], OpenSession, int]]:
        armed: list[tuple[tuple[str, str], OpenSession, int]] = []
        for key, sess in sessions.items():
            self.arm(sess)
            if eligible_for_watermark_close(sess, cfg, comparison_w):
                armed.append((key, sess, watermark_close_end(sess, cfg)))
        armed.sort(key=lambda item: (item[1].tenant_id, item[1].user_id, item[1].start_ms))
        return armed
