"""Operator audit trail for cutover / sync / dump actions."""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


@dataclass
class AuditEvent:
    action: str
    actor: str
    node_id: str
    detail: dict[str, Any] = field(default_factory=dict)
    at: str = field(default_factory=_utc_now)


@dataclass
class AuditLog:
    path: Path
    events: list[AuditEvent] = field(default_factory=list)

    def record(self, event: AuditEvent) -> None:
        self.events.append(event)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(asdict(event), sort_keys=True) + "\n")

    def read_all(self) -> list[dict[str, Any]]:
        if not self.path.is_file():
            return []
        rows: list[dict[str, Any]] = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
        return rows


def default_audit_path(ha_root: str | Path) -> Path:
    return Path(ha_root) / "out" / "operator-audit.jsonl"


def record_action(
    ha_root: str | Path,
    *,
    action: str,
    actor: str,
    node_id: str,
    **detail: Any,
) -> AuditEvent:
    log = AuditLog(path=default_audit_path(ha_root))
    event = AuditEvent(action=action, actor=actor, node_id=node_id, detail=dict(detail))
    log.record(event)
    return event
