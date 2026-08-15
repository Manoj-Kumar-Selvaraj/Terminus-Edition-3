from __future__ import annotations
from dataclasses import dataclass, field, asdict
from decimal import Decimal
from enum import Enum
from typing import Iterable, Mapping

class MovementType(str, Enum):
    RECEIPT = "RECEIPT"
    ISSUE = "ISSUE"
    TRANSFER = "TRANSFER"
    ADJUSTMENT = "ADJUSTMENT"

class MovementStatus(str, Enum):
    NEW = "NEW"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    HELD = "HELD"

class RunState(str, Enum):
    CREATED = "CREATED"
    PROCESSING = "PROCESSING"
    RECONCILING = "RECONCILING"
    READY = "READY"
    HELD = "HELD"
    PUBLISHED = "PUBLISHED"

@dataclass(frozen=True)
class Money:
    value: Decimal
    currency: str = "USD"
    def quantized(self) -> "Money":
        return Money(self.value.quantize(Decimal("0.01")), self.currency)
    def __add__(self, other: "Money") -> "Money":
        self._same(other); return Money(self.value + other.value, self.currency).quantized()
    def __sub__(self, other: "Money") -> "Money":
        self._same(other); return Money(self.value - other.value, self.currency).quantized()
    def _same(self, other: "Money") -> None:
        if self.currency != other.currency: raise ValueError("currency mismatch")
    def is_non_negative(self) -> bool: return self.value >= 0

@dataclass(frozen=True)
class Movement:
    movement_id: str
    sequence: int
    movement_type: MovementType
    item_id: str
    source_warehouse: str | None
    destination_warehouse: str | None
    quantity: Decimal
    unit_cost: Decimal
    effective_date: str
    reason_code: str
    generation_id: str
    raw_offset: int = 0
    raw_length: int = 0
    def total_value(self) -> Decimal:
        return (self.quantity * self.unit_cost).quantize(Decimal("0.01"))
    def warehouses(self) -> tuple[str, ...]:
        values=[]
        if self.source_warehouse: values.append(self.source_warehouse)
        if self.destination_warehouse and self.destination_warehouse not in values: values.append(self.destination_warehouse)
        return tuple(values)
    def requires_source(self) -> bool:
        return self.movement_type in {MovementType.ISSUE, MovementType.TRANSFER, MovementType.ADJUSTMENT}
    def requires_destination(self) -> bool:
        return self.movement_type in {MovementType.RECEIPT, MovementType.TRANSFER}

@dataclass(frozen=True)
class InventoryEffect:
    movement_id: str
    warehouse_id: str
    item_id: str
    quantity_delta: Decimal
    value_delta: Decimal
    effect_kind: str
    sequence: int
    def signed_unit_cost(self) -> Decimal:
        if self.quantity_delta == 0: return Decimal("0")
        return (self.value_delta / self.quantity_delta).quantize(Decimal("0.0001"))

@dataclass(frozen=True)
class InventoryPosition:
    warehouse_id: str
    item_id: str
    quantity: Decimal
    value: Decimal
    version: int = 0
    def unit_cost(self) -> Decimal:
        if self.quantity == 0: return Decimal("0")
        return (self.value / self.quantity).quantize(Decimal("0.0001"))
    def apply(self, effect: InventoryEffect) -> "InventoryPosition":
        if (self.warehouse_id,self.item_id)!=(effect.warehouse_id,effect.item_id): raise ValueError("position/effect mismatch")
        return InventoryPosition(self.warehouse_id,self.item_id,self.quantity+effect.quantity_delta,self.value+effect.value_delta,self.version+1)

@dataclass(frozen=True)
class Checkpoint:
    generation_id: str
    last_sequence: int
    byte_offset: int
    source_fingerprint: str
    updated_at: str

@dataclass(frozen=True)
class GenerationIdentity:
    generation_id: str
    source_name: str
    source_size: int
    source_sha256: str
    layout_sha256: str
    business_date: str
    def fingerprint(self) -> str:
        return f"{self.source_sha256}:{self.layout_sha256}:{self.business_date}"

@dataclass(frozen=True)
class ReconciliationControl:
    name: str
    expected: Decimal
    actual: Decimal
    tolerance: Decimal = Decimal("0")
    @property
    def difference(self) -> Decimal: return self.actual-self.expected
    @property
    def passed(self) -> bool: return abs(self.difference)<=self.tolerance

@dataclass
class ReconciliationResult:
    generation_id: str
    controls: list[ReconciliationControl] = field(default_factory=list)
    @property
    def passed(self) -> bool: return bool(self.controls) and all(c.passed for c in self.controls)
    def failed(self) -> list[ReconciliationControl]: return [c for c in self.controls if not c.passed]
    def as_dict(self) -> dict: return {"generation_id":self.generation_id,"passed":self.passed,"controls":[asdict(c)|{"passed":c.passed,"difference":str(c.difference)} for c in self.controls]}

@dataclass(frozen=True)
class Reject:
    generation_id: str
    sequence: int
    movement_id: str
    code: str
    message: str
    byte_offset: int
    byte_length: int

@dataclass
class RunSummary:
    generation_id: str
    state: RunState
    processed: int = 0
    accepted: int = 0
    rejected: int = 0
    held: int = 0
    quantity_delta: Decimal = Decimal("0")
    value_delta: Decimal = Decimal("0")
    output_paths: dict[str,str] = field(default_factory=dict)
    def record_accept(self, effects: Iterable[InventoryEffect]) -> None:
        self.processed+=1; self.accepted+=1
        for e in effects: self.quantity_delta+=e.quantity_delta; self.value_delta+=e.value_delta
    def record_reject(self) -> None: self.processed+=1; self.rejected+=1
    def record_hold(self) -> None: self.processed+=1; self.held+=1
    def as_dict(self) -> dict:
        return {"generation_id":self.generation_id,"state":self.state.value,"processed":self.processed,"accepted":self.accepted,"rejected":self.rejected,"held":self.held,"quantity_delta":str(self.quantity_delta),"value_delta":str(self.value_delta),"output_paths":dict(self.output_paths)}

def decimal_text(value: Decimal) -> str:
    return format(value.quantize(Decimal("0.01")),"f")

def movement_from_mapping(data: Mapping[str, object]) -> Movement:
    return Movement(str(data["movement_id"]),int(data["sequence"]),MovementType(str(data["movement_type"])),str(data["item_id"]),None if data.get("source_warehouse") in (None,"") else str(data["source_warehouse"]),None if data.get("destination_warehouse") in (None,"") else str(data["destination_warehouse"]),Decimal(str(data["quantity"])),Decimal(str(data["unit_cost"])),str(data["effective_date"]),str(data.get("reason_code","")),str(data["generation_id"]),int(data.get("raw_offset",0)),int(data.get("raw_length",0)))
