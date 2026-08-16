"""Place/pay pipeline stage bookkeeping (does not replace router/fencing defects)."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class StageName(str, Enum):
    VALIDATE = "validate"
    RESERVE = "reserve"
    WRITE_ORDER = "write_order"
    AUTHORIZE = "authorize"
    CAPTURE = "capture"
    PIN = "pin"
    CONFIRM = "confirm"
    EFFECT = "effect"


@dataclass
class StageResult:
    name: StageName
    ok: bool
    detail: dict[str, Any] = field(default_factory=dict)


@dataclass
class PipelineTrace:
    attempt_id: str
    stages: list[StageResult] = field(default_factory=list)

    def add(self, name: StageName, ok: bool, **detail: Any) -> StageResult:
        result = StageResult(name=name, ok=ok, detail=dict(detail))
        self.stages.append(result)
        return result

    def failed(self) -> StageResult | None:
        for stage in self.stages:
            if not stage.ok:
                return stage
        return None

    def as_list(self) -> list[dict[str, Any]]:
        return [
            {"name": s.name.value, "ok": s.ok, "detail": s.detail} for s in self.stages
        ]


def place_stage_order() -> tuple[StageName, ...]:
    return (
        StageName.VALIDATE,
        StageName.RESERVE,
        StageName.WRITE_ORDER,
        StageName.AUTHORIZE,
        StageName.EFFECT,
        StageName.PIN,
    )


def pay_stage_order() -> tuple[StageName, ...]:
    return (
        StageName.VALIDATE,
        StageName.CAPTURE,
        StageName.EFFECT,
        StageName.PIN,
    )


def confirm_stage_order() -> tuple[StageName, ...]:
    return (StageName.CONFIRM,)
