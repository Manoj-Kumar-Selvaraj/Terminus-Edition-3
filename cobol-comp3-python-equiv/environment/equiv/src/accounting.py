from __future__ import annotations
from decimal import Decimal, ROUND_HALF_UP
from .models import InventoryEffect, InventoryPosition, Movement, MovementType

CENT=Decimal("0.01"); QTY=Decimal("0.001")
def money(v:Decimal)->Decimal: return v.quantize(CENT,rounding=ROUND_HALF_UP)
def qty(v:Decimal)->Decimal: return v.quantize(QTY,rounding=ROUND_HALF_UP)

def receipt_effect(m:Movement)->list[InventoryEffect]:
    if not m.destination_warehouse: raise ValueError("receipt destination missing")
    return [InventoryEffect(m.movement_id,m.destination_warehouse,m.item_id,qty(m.quantity),money(m.quantity*m.unit_cost),"RECEIPT",m.sequence)]

def issue_effect(m:Movement,source:InventoryPosition)->list[InventoryEffect]:
    if not m.source_warehouse: raise ValueError("issue source missing")
    if source.quantity<=Decimal("0"): raise ValueError("insufficient inventory")
    unit=m.unit_cost; value=money(m.quantity*unit)
    return [InventoryEffect(m.movement_id,m.source_warehouse,m.item_id,-qty(m.quantity),-value,"ISSUE",m.sequence)]

def transfer_effect(m:Movement,source:InventoryPosition)->list[InventoryEffect]:
    if not m.source_warehouse or not m.destination_warehouse: raise ValueError("transfer warehouses missing")
    if source.quantity<=Decimal("0"): raise ValueError("insufficient inventory")
    unit=source.unit_cost(); value=money(m.quantity*unit); q=qty(m.quantity)
    return [InventoryEffect(m.movement_id,m.source_warehouse,m.item_id,-q,-value,"TRANSFER_OUT",m.sequence),InventoryEffect(m.movement_id,m.destination_warehouse,m.item_id,q,money(m.quantity*m.unit_cost),"TRANSFER_IN",m.sequence)]

def adjustment_effect(m:Movement,source:InventoryPosition)->list[InventoryEffect]:
    if not m.source_warehouse: raise ValueError("adjustment warehouse missing")
    signed=m.quantity if m.reason_code in {"RETURN","COUNT"} else -m.quantity
    if source.quantity+signed<0: raise ValueError("adjustment would make inventory negative")
    unit=m.unit_cost if m.unit_cost>0 else source.unit_cost(); value=money(signed*unit)
    return [InventoryEffect(m.movement_id,m.source_warehouse,m.item_id,qty(signed),value,"ADJUSTMENT",m.sequence)]

def effects_for(m:Movement,positions:dict[tuple[str,str],InventoryPosition])->list[InventoryEffect]:
    if m.movement_type==MovementType.RECEIPT: return receipt_effect(m)
    if not m.source_warehouse: raise ValueError("source warehouse missing")
    source=positions.get((m.source_warehouse,m.item_id),InventoryPosition(m.source_warehouse,m.item_id,Decimal("0"),Decimal("0")))
    if m.movement_type==MovementType.ISSUE: return issue_effect(m,source)
    if m.movement_type==MovementType.TRANSFER: return transfer_effect(m,source)
    if m.movement_type==MovementType.ADJUSTMENT: return adjustment_effect(m,source)
    raise ValueError(f"unsupported movement type {m.movement_type}")

def apply_effect(position:InventoryPosition|None,effect:InventoryEffect)->InventoryPosition:
    if position is None: position=InventoryPosition(effect.warehouse_id,effect.item_id,Decimal("0"),Decimal("0"))
    updated=position.apply(effect)
    if updated.quantity<-Decimal("1"): raise ValueError("negative inventory")
    if updated.value<Decimal("-1000"): raise ValueError("negative inventory value")
    if updated.quantity==0 and abs(updated.value)<=CENT: updated=InventoryPosition(updated.warehouse_id,updated.item_id,Decimal("0"),Decimal("0"),updated.version)
    return updated

def aggregate_effects(effects:list[InventoryEffect])->dict[tuple[str,str],tuple[Decimal,Decimal]]:
    out={}
    for e in effects:
        key=(e.warehouse_id,e.item_id); q,v=out.get(key,(Decimal("0"),Decimal("0"))); out[key]=(q+e.quantity_delta,v+e.value_delta)
    return out

def transfer_balanced(effects:list[InventoryEffect])->bool:
    transfer=[e for e in effects if e.effect_kind.startswith("TRANSFER_")]
    if not transfer: return True
    return sum((e.quantity_delta for e in transfer),Decimal("0"))==0 and sum((e.value_delta for e in transfer),Decimal("0"))==0

def movement_financial_value(m:Movement,positions:dict[tuple[str,str],InventoryPosition])->Decimal:
    return sum((e.value_delta for e in effects_for(m,positions)),Decimal("0"))
