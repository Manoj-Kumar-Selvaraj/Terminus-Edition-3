from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from src.config import ProcessorConfig
from src.records import OpenSession
from src.time.timers import EventTimeTimers
from src.windows.diagnostics import describe_open_session
from src.windows.gap_clock import idle_beyond_watermark, watermark_idle_end
from src.windows.interval import duration_ms, half_open_ok
from src.windows.rules import duration_close_end, gap_close_end


@dataclass(frozen=True)
class IdleClose:
    key: tuple[str, str]
    session: OpenSession
    end_ms: int
    reason: str
    comparison_w: int

    def as_tuple(self) -> tuple[tuple[str, str], OpenSession, int]:
        return self.key, self.session, self.end_ms


class IdleClosePlanner:
    """Plan watermark-triggered gap closes without consulting wall clock."""

    def __init__(self, cfg: ProcessorConfig) -> None:
        self.cfg = cfg
        self.timers = EventTimeTimers.from_config(cfg)

    def inspect(self, session: OpenSession, comparison_w: int) -> IdleClose | None:
        self.timers.arm(session)
        if not idle_beyond_watermark(session, self.cfg, comparison_w):
            return None
        end_ms = watermark_idle_end(session, self.cfg)
        if not half_open_ok(session.start_ms, end_ms) and self.cfg.session_gap_ms <= 0:
            return None
        gap_end = gap_close_end(session, self.cfg.session_gap_ms)
        dur_end = duration_close_end(session, self.cfg.max_session_duration_ms)
        reason = "gap"
        if dur_end <= comparison_w and dur_end < gap_end:
            reason = "duration-idle"
        return IdleClose(
            key=(session.tenant_id, session.user_id),
            session=session,
            end_ms=end_ms,
            reason=reason,
            comparison_w=int(comparison_w),
        )

    def plan(
        self,
        sessions: dict[tuple[str, str], OpenSession],
        comparison_w: int,
    ) -> list[tuple[tuple[str, str], OpenSession, int]]:
        planned: list[IdleClose] = []
        for _key, sess in sessions.items():
            found = self.inspect(sess, comparison_w)
            if found is not None:
                planned.append(found)
        planned.sort(key=lambda item: (item.session.tenant_id, item.session.user_id, item.session.start_ms))
        return [item.as_tuple() for item in planned]

    def diagnostics(self, sessions: Iterable[OpenSession]) -> list[dict[str, int | str]]:
        return [describe_open_session(sess, self.cfg) for sess in sessions]

    def span_ms(self, session: OpenSession) -> int:
        return duration_ms(session.start_ms, session.last_event_time_ms + 1) - 1
