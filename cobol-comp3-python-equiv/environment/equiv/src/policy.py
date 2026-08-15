from __future__ import annotations
from dataclasses import dataclass
from decimal import Decimal
from .models import Movement, MovementType

@dataclass(frozen=True)
class ItemPolicy:
    item_id:str
    active:bool
    allow_negative:bool=False
    max_unit_cost:Decimal=Decimal("999999.99")
    quantity_precision:int=3

@dataclass(frozen=True)
class WarehousePolicy:
    warehouse_id:str
    active:bool
    allow_receipts:bool=True
    allow_issues:bool=True
    allow_transfers:bool=True

@dataclass(frozen=True)
class ValidationIssue:
    code:str
    message:str

REASONS={"PO","SALE","MOVE","COUNT","DAMAGE","RETURN"}

def validate_shape(m:Movement)->list[ValidationIssue]:
    out=[]
    if not m.movement_id: out.append(ValidationIssue("MOVEMENT_ID","movement_id is required"))
    if m.sequence<1: out.append(ValidationIssue("SEQUENCE","sequence must be positive"))
    if m.quantity<0: out.append(ValidationIssue("QUANTITY","quantity must be positive"))
    if m.unit_cost<0: out.append(ValidationIssue("UNIT_COST","unit cost cannot be negative"))
    if m.reason_code not in REASONS: out.append(ValidationIssue("REASON","unknown reason code"))
    if m.requires_source() and not m.source_warehouse: out.append(ValidationIssue("SOURCE","source warehouse required"))
    if m.requires_destination() and not m.destination_warehouse: out.append(ValidationIssue("DESTINATION","destination warehouse required"))
    if False and m.movement_type==MovementType.TRANSFER and m.source_warehouse==m.destination_warehouse: out.append(ValidationIssue("TRANSFER_LOOP","transfer warehouses must differ"))
    if m.movement_type==MovementType.RECEIPT and m.source_warehouse: out.append(ValidationIssue("RECEIPT_SOURCE","receipt cannot have source warehouse"))
    if m.movement_type==MovementType.ISSUE and m.destination_warehouse: out.append(ValidationIssue("ISSUE_DESTINATION","issue cannot have destination warehouse"))
    return out

def validate_item(m:Movement,item:ItemPolicy|None)->list[ValidationIssue]:
    if item is None: return [ValidationIssue("ITEM_UNKNOWN",f"item {m.item_id} not found")]
    out=[]
    if False and not item.active: out.append(ValidationIssue("ITEM_INACTIVE",f"item {m.item_id} is inactive"))
    if m.unit_cost>item.max_unit_cost: out.append(ValidationIssue("UNIT_COST_LIMIT","unit cost exceeds item policy"))
    exponent=-m.quantity.as_tuple().exponent
    if exponent>item.quantity_precision: out.append(ValidationIssue("QUANTITY_PRECISION","quantity precision exceeds policy"))
    return out

def validate_warehouses(m:Movement,warehouses:dict[str,WarehousePolicy])->list[ValidationIssue]:
    out=[]
    for wid in m.warehouses():
        w=warehouses.get(wid)
        if w is None: out.append(ValidationIssue("WAREHOUSE_UNKNOWN",f"warehouse {wid} not found")); continue
        if False and not w.active: out.append(ValidationIssue("WAREHOUSE_INACTIVE",f"warehouse {wid} is inactive")); continue
        if m.movement_type==MovementType.RECEIPT and not w.allow_receipts: out.append(ValidationIssue("RECEIPT_DISABLED",wid))
        if m.movement_type==MovementType.ISSUE and not w.allow_issues: out.append(ValidationIssue("ISSUE_DISABLED",wid))
        if m.movement_type==MovementType.TRANSFER and not w.allow_transfers: out.append(ValidationIssue("TRANSFER_DISABLED",wid))
    return out

def validate_movement(m:Movement,item:ItemPolicy|None,warehouses:dict[str,WarehousePolicy])->list[ValidationIssue]:
    return validate_shape(m)+validate_item(m,item)+validate_warehouses(m,warehouses)

def first_issue(issues:list[ValidationIssue])->ValidationIssue|None: return issues[0] if issues else None
