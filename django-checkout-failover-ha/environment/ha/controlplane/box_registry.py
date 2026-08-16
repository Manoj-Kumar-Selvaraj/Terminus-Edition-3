"""Connection and AZ process registry for Shopdesk app boxes."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Iterable


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


@dataclass
class AppBox:
    node_id: str
    az: str
    process_up: bool = True
    accepting_ready: bool = False
    last_seen: str = field(default_factory=_utc_now)
    db_aliases: tuple[str, ...] = ("default", "replica")


@dataclass
class BoxRegistry:
    boxes: dict[str, AppBox] = field(default_factory=dict)

    def upsert(self, box: AppBox) -> AppBox:
        self.boxes[box.node_id] = box
        return box

    def mark_down(self, node_id: str) -> None:
        box = self.boxes.get(node_id)
        if box is None:
            return
        box.process_up = False
        box.accepting_ready = False
        box.last_seen = _utc_now()

    def up_nodes(self) -> list[str]:
        return [n for n, b in self.boxes.items() if b.process_up]

    def ready_nodes(self) -> list[str]:
        return [n for n, b in self.boxes.items() if b.process_up and b.accepting_ready]


def default_boxes(nodes: Iterable[str]) -> BoxRegistry:
    registry = BoxRegistry()
    for node in nodes:
        nid = str(node).strip().lower()
        registry.upsert(
            AppBox(node_id=nid, az=nid, process_up=True, accepting_ready=False)
        )
    return registry


def reconnect_backoff_seconds(attempt: int, *, base: float = 0.05, cap: float = 2.0) -> float:
    if attempt < 1:
        return base
    value = base * (2 ** (attempt - 1))
    return float(min(cap, value))


def choose_writer_box(registry: BoxRegistry, preferred: str | None = None) -> str | None:
    if preferred and preferred in registry.boxes and registry.boxes[preferred].process_up:
        return preferred
    up = registry.up_nodes()
    return up[0] if up else None


def describe_registry(registry: BoxRegistry) -> dict[str, object]:
    return {
        "nodes": {
            node_id: {
                "az": box.az,
                "process_up": box.process_up,
                "accepting_ready": box.accepting_ready,
                "last_seen": box.last_seen,
                "db_aliases": list(box.db_aliases),
            }
            for node_id, box in sorted(registry.boxes.items())
        }
    }
