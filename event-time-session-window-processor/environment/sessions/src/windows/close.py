from __future__ import annotations

from src.config import ProcessorConfig
from src.records import OpenSession
from src.tenancy.directory import TenantDirectory
from src.tenancy.policy import bind_config
from src.windows.gap_clock import idle_beyond_watermark, watermark_idle_end
from src.windows.operator import IdleClosePlanner


def config_for_session(
    cfg: ProcessorConfig,
    session: OpenSession,
    directory: TenantDirectory | None,
) -> ProcessorConfig:
    if directory is None:
        return cfg
    return bind_config(cfg, directory, session.tenant_id)


def session_idle_close_end(
    session: OpenSession,
    cfg: ProcessorConfig,
    directory: TenantDirectory | None = None,
) -> int:
    return watermark_idle_end(session, config_for_session(cfg, session, directory))


def session_idle_due(
    session: OpenSession,
    cfg: ProcessorConfig,
    comparison_w: int,
    directory: TenantDirectory | None = None,
) -> bool:
    return idle_beyond_watermark(session, config_for_session(cfg, session, directory), comparison_w)


def watermark_close_candidates(
    sessions: dict[tuple[str, str], OpenSession],
    cfg: ProcessorConfig,
    comparison_w: int,
    directory: TenantDirectory | None = None,
) -> list[tuple[tuple[str, str], OpenSession, int]]:
    planned: list[tuple[tuple[str, str], OpenSession, int]] = []
    for _key, sess in sessions.items():
        sess_cfg = config_for_session(cfg, sess, directory)
        found = IdleClosePlanner(sess_cfg).inspect(sess, comparison_w)
        if found is None:
            continue
        if not session_idle_due(sess, cfg, comparison_w, directory):
            continue
        planned.append(found.as_tuple())
    planned.sort(key=lambda item: (item[1].tenant_id, item[1].user_id, item[1].start_ms))
    return planned
