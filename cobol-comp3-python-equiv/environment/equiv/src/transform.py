from __future__ import annotations
from decimal import Decimal
from .framing import DecodedRecord, require_decimal, require_text
from .models import Movement, MovementType

TYPE_CODES={"R":MovementType.RECEIPT,"I":MovementType.ISSUE,"T":MovementType.TRANSFER,"A":MovementType.ADJUSTMENT}

def movement_from_record(record:DecodedRecord,generation_id:str)->Movement:
    v=record.values; code=require_text(v,"MOVE-TYPE")
    if code not in TYPE_CODES: raise ValueError(f"unknown movement type code {code}")
    source=require_text(v,"SOURCE-WH") or None; dest=require_text(v,"DEST-WH") or None
    reason=require_text(v,"REASON")
    return Movement(require_text(v,"MOVEMENT-ID"),int(require_decimal(v,"SEQUENCE")),TYPE_CODES[code],require_text(v,"ITEM-ID"),source,dest,require_decimal(v,"QUANTITY"),require_decimal(v,"UNIT-COST"),require_text(v,"EFFECTIVE-DATE"),reason,generation_id,record.offset,record.length)

def normalize_item_id(value:str)->str: return value.strip().upper()
def normalize_warehouse(value:str|None)->str|None: return None if value is None else value.strip().upper()
def normalized(m:Movement)->Movement:
    return Movement(m.movement_id.strip(),m.sequence,m.movement_type,normalize_item_id(m.item_id),normalize_warehouse(m.source_warehouse),normalize_warehouse(m.destination_warehouse),m.quantity.quantize(Decimal("0.001")),m.unit_cost.quantize(Decimal("0.01")),m.effective_date.strip(),m.reason_code.strip().upper(),m.generation_id,m.raw_offset,m.raw_length)
