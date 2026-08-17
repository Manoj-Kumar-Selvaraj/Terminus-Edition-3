from __future__ import annotations
from dataclasses import dataclass
from decimal import Decimal
from .models import Movement,MovementType

@dataclass(frozen=True)
class LegacyMovement:
    id_text:str
    seq_text:str
    type_code:str
    sku:str
    from_wh:str
    to_wh:str
    quantity_text:str
    cost_text:str
    date_text:str
    reason_text:str
TYPE_FROM={'R':MovementType.RECEIPT,'I':MovementType.ISSUE,'T':MovementType.TRANSFER,'A':MovementType.ADJUSTMENT}
TYPE_TO={v:k for k,v in TYPE_FROM.items()}
def to_domain(row:LegacyMovement,generation_id:str,offset:int=0,length:int=0)->Movement:
    if row.type_code not in TYPE_FROM:raise ValueError(f'unknown legacy movement code {row.type_code}')
    return Movement(row.id_text.strip(),int(row.seq_text),TYPE_FROM[row.type_code],row.sku.strip(),row.from_wh.strip() or None,row.to_wh.strip() or None,Decimal(row.quantity_text),Decimal(row.cost_text),row.date_text.strip(),row.reason_text.strip(),generation_id,offset,length)
def from_domain(m:Movement)->LegacyMovement:
    return LegacyMovement(m.movement_id,str(m.sequence),TYPE_TO[m.movement_type],m.item_id,m.source_warehouse or '',m.destination_warehouse or '',format(m.quantity,'f'),format(m.unit_cost,'f'),m.effective_date,m.reason_code)
def canonical_business_key(row:LegacyMovement)->tuple[str,...]:return (row.id_text.strip(),row.sku.strip(),row.type_code,row.from_wh.strip(),row.to_wh.strip(),row.date_text.strip())
def commercially_equivalent(a:LegacyMovement,b:LegacyMovement)->bool:return canonical_business_key(a)==canonical_business_key(b) and Decimal(a.quantity_text)==Decimal(b.quantity_text) and Decimal(a.cost_text)==Decimal(b.cost_text)
def exact_source_equivalent(a:LegacyMovement,b:LegacyMovement)->bool:return a==b
def normalize(row:LegacyMovement)->LegacyMovement:return LegacyMovement(row.id_text.strip(),str(int(row.seq_text)),row.type_code.strip().upper(),row.sku.strip().upper(),row.from_wh.strip().upper(),row.to_wh.strip().upper(),format(Decimal(row.quantity_text),'f'),format(Decimal(row.cost_text),'f'),row.date_text.strip(),row.reason_text.strip().upper())
