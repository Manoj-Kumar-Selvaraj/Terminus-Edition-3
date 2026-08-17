from __future__ import annotations
from dataclasses import dataclass
from decimal import Decimal,ROUND_HALF_UP
from .models import InventoryPosition,Movement

MONEY=Decimal('0.01');UNIT=Decimal('0.0001')
@dataclass(frozen=True)
class Valuation:
    quantity_before:Decimal
    value_before:Decimal
    quantity_delta:Decimal
    value_delta:Decimal
    quantity_after:Decimal
    value_after:Decimal
    unit_cost_before:Decimal
    unit_cost_after:Decimal

def unit_cost(quantity:Decimal,value:Decimal)->Decimal:
    if quantity==0:return Decimal('0')
    return (value/quantity).quantize(UNIT,rounding=ROUND_HALF_UP)
def receipt(position:InventoryPosition,quantity:Decimal,cost:Decimal)->Valuation:
    delta=(quantity*cost).quantize(MONEY,rounding=ROUND_HALF_UP);qa=position.quantity+quantity;va=position.value+delta
    return Valuation(position.quantity,position.value,quantity,delta,qa,va,unit_cost(position.quantity,position.value),unit_cost(qa,va))
def issue(position:InventoryPosition,quantity:Decimal)->Valuation:
    if quantity>position.quantity:raise ValueError('insufficient quantity')
    before=unit_cost(position.quantity,position.value);delta=-(quantity*before).quantize(MONEY,rounding=ROUND_HALF_UP);qa=position.quantity-quantity;va=position.value+delta
    if qa==0 and abs(va)<=MONEY:va=Decimal('0')
    return Valuation(position.quantity,position.value,-quantity,delta,qa,va,before,unit_cost(qa,va))
def transfer(source:InventoryPosition,destination:InventoryPosition,quantity:Decimal)->tuple[Valuation,Valuation]:
    out=issue(source,quantity);cost=out.unit_cost_before;incoming=receipt(destination,quantity,cost)
    if out.value_delta+incoming.value_delta!=0:raise ValueError('transfer value not balanced')
    return out,incoming
def adjustment(position:InventoryPosition,quantity_delta:Decimal,unit_price:Decimal|None=None)->Valuation:
    price=unit_price if unit_price is not None else unit_cost(position.quantity,position.value);delta=(quantity_delta*price).quantize(MONEY,rounding=ROUND_HALF_UP);qa=position.quantity+quantity_delta
    if qa<0:raise ValueError('adjustment makes position negative')
    va=position.value+delta
    if qa==0 and abs(va)<=MONEY:va=Decimal('0')
    return Valuation(position.quantity,position.value,quantity_delta,delta,qa,va,unit_cost(position.quantity,position.value),unit_cost(qa,va))
def drift(position:InventoryPosition,expected_unit_cost:Decimal)->Decimal:
    return (unit_cost(position.quantity,position.value)-expected_unit_cost).quantize(UNIT)
def materially_different(a:Valuation,b:Valuation,tolerance:Decimal=Decimal('0.01'))->bool:
    return abs(a.quantity_after-b.quantity_after)>Decimal('0.001') or abs(a.value_after-b.value_after)>tolerance
