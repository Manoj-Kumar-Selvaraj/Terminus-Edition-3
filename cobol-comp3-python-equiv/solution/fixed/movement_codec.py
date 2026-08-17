from __future__ import annotations
from decimal import Decimal
from .comp3 import pack,display_encode
from .layout import Layout,Field,active_occurs
from .models import Movement

def encode_element(field:Field,value:object)->bytes:
    if field.picture.startswith('X('):
        size=field.elementary_length();raw=str(value).encode('ascii');
        if len(raw)>size:raise OverflowError(f'{field.name} text overflow')
        return raw.ljust(size,b' ')
    digits,scale,signed=field.digits_scale_signed();number=Decimal(str(value))
    if field.usage=='COMP-3':
        from .layout import packed_spec
        return pack(number,packed_spec(field))
    return display_encode(number,digits,scale,signed)
def encode_values(layout:Layout,values:dict[str,object])->bytes:
    layout.validate();out=bytearray();storage={}
    for field in layout.fields:
        count=active_occurs(field,values) if field.depending_on else field.occurs
        if field.redefines:continue
        value=values[field.name]
        if count==1:chunk=encode_element(field,value)
        else:
            seq=list(value)
            if len(seq)!=count:raise ValueError(f'{field.name} requires {count} active occurrences')
            chunk=b''.join(encode_element(field,v) for v in seq)
        storage[field.name]=(len(out),len(chunk));out.extend(chunk)
    return bytes(out)
def movement_values(m:Movement,attr_values:list[str]|None=None)->dict[str,object]:
    attrs=attr_values or []
    return {'MOVEMENT-ID':m.movement_id,'SEQUENCE':Decimal(m.sequence),'MOVE-TYPE':{'RECEIPT':'R','ISSUE':'I','TRANSFER':'T','ADJUSTMENT':'A'}[m.movement_type.value],'ITEM-ID':m.item_id,'SOURCE-WH':m.source_warehouse or '','DEST-WH':m.destination_warehouse or '','QUANTITY':m.quantity,'UNIT-COST':m.unit_cost,'EFFECTIVE-DATE':m.effective_date,'REASON':m.reason_code,'ATTR-COUNT':Decimal(len(attrs)),'ATTR-VALUE':attrs,'ALT-ITEM':m.item_id}
def encode_movement(layout:Layout,m:Movement,attr_values:list[str]|None=None)->bytes:return encode_values(layout,movement_values(m,attr_values))
def encode_tape(layout:Layout,movements:list[Movement])->bytes:return b''.join(encode_movement(layout,m) for m in movements)
def validate_encoded_length(layout:Layout,values:dict[str,object],payload:bytes)->bool:
    from .layout import record_length
    return len(payload)==record_length(layout,values)
