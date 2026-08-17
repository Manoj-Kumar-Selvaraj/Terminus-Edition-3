"""Typed records shared across gate, moves, and publish."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class VisitRecord:
    visit_id: str
    scac: str
    trailer_number: str
    visit_type: str
    equipment: str
    state: str
    spot_id: Optional[str]
    door_id: Optional[str]
    appointment_id: Optional[str]
    gate_in: Optional[str]
    gate_out: Optional[str]
    seal: Optional[str]
    on_ground: int
    chassis_id: Optional[str]
    clock_start: Optional[str]

    @classmethod
    def from_row(cls, row: Any) -> "VisitRecord":
        mapping = dict(row)
        return cls(
            visit_id=str(mapping["visit_id"]),
            scac=str(mapping["scac"]),
            trailer_number=str(mapping["trailer_number"]),
            visit_type=str(mapping["visit_type"]),
            equipment=str(mapping["equipment"]),
            state=str(mapping["state"]),
            spot_id=mapping.get("spot_id"),
            door_id=mapping.get("door_id"),
            appointment_id=mapping.get("appointment_id"),
            gate_in=mapping.get("gate_in"),
            gate_out=mapping.get("gate_out"),
            seal=mapping.get("seal"),
            on_ground=int(mapping.get("on_ground") or 0),
            chassis_id=mapping.get("chassis_id"),
            clock_start=mapping.get("clock_start"),
        )

    def as_snapshot(self) -> dict[str, Any]:
        return {
            "visit_id": self.visit_id,
            "scac": self.scac,
            "trailer_number": self.trailer_number,
            "visit_type": self.visit_type,
            "equipment": self.equipment,
            "state": self.state,
            "spot_id": self.spot_id,
            "door_id": self.door_id,
            "gate_in": self.gate_in,
            "appointment_id": self.appointment_id,
            "seal": self.seal,
        }


@dataclass
class MoveRecord:
    move_id: str
    visit_id: str
    state: str
    origin_spot_id: Optional[str]
    dest_spot_id: Optional[str]
    seq: int

    @classmethod
    def from_row(cls, row: Any) -> "MoveRecord":
        mapping = dict(row)
        return cls(
            move_id=str(mapping["move_id"]),
            visit_id=str(mapping["visit_id"]),
            state=str(mapping["state"]),
            origin_spot_id=mapping.get("origin_spot_id"),
            dest_spot_id=mapping.get("dest_spot_id"),
            seq=int(mapping.get("seq") or 0),
        )


@dataclass
class HoldRecord:
    visit_id: str
    hold_code: str
    placed_at: str
    released_at: Optional[str]
    active: int

    @classmethod
    def from_row(cls, row: Any) -> "HoldRecord":
        mapping = dict(row)
        return cls(
            visit_id=str(mapping["visit_id"]),
            hold_code=str(mapping["hold_code"]),
            placed_at=str(mapping["placed_at"]),
            released_at=mapping.get("released_at"),
            active=int(mapping.get("active") or 0),
        )


@dataclass
class OccupancyLine:
    spot_id: str
    zone: str
    visit_id: Optional[str] = None
    reserved_move_id: Optional[str] = None
    extras: dict[str, Any] = field(default_factory=dict)
