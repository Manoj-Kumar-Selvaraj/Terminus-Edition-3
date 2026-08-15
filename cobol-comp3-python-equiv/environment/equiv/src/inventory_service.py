from __future__ import annotations
from dataclasses import dataclass
from decimal import Decimal
import sqlite3
from .database import get_position,save_position
from .models import InventoryEffect,InventoryPosition
from .accounting import apply_effect

@dataclass(frozen=True)
class PositionChange:
    warehouse_id:str
    item_id:str
    before:InventoryPosition
    effect:InventoryEffect
    after:InventoryPosition
class InventoryService:
    def __init__(self,db:sqlite3.Connection):self.db=db
    def position(self,warehouse_id:str,item_id:str)->InventoryPosition:return get_position(self.db,warehouse_id,item_id)
    def apply(self,effect:InventoryEffect)->PositionChange:
        before=self.position(effect.warehouse_id,effect.item_id);after=apply_effect(before,effect);save_position(self.db,after);return PositionChange(effect.warehouse_id,effect.item_id,before,effect,after)
    def apply_many(self,effects:list[InventoryEffect])->list[PositionChange]:
        changes=[]
        for effect in effects:changes.append(self.apply(effect))
        return changes
    def total_quantity(self,warehouse_id:str|None=None)->Decimal:
        if warehouse_id is None:r=self.db.execute('SELECT COALESCE(SUM(CAST(quantity AS REAL)),0) FROM inventory_positions').fetchone()
        else:r=self.db.execute('SELECT COALESCE(SUM(CAST(quantity AS REAL)),0) FROM inventory_positions WHERE warehouse_id=?',(warehouse_id,)).fetchone()
        return Decimal(str(r[0]))
    def total_value(self,warehouse_id:str|None=None)->Decimal:
        if warehouse_id is None:r=self.db.execute('SELECT COALESCE(SUM(CAST(value AS REAL)),0) FROM inventory_positions').fetchone()
        else:r=self.db.execute('SELECT COALESCE(SUM(CAST(value AS REAL)),0) FROM inventory_positions WHERE warehouse_id=?',(warehouse_id,)).fetchone()
        return Decimal(str(r[0])).quantize(Decimal('0.01'))
    def negative_positions(self)->list[tuple[str,str]]:
        return [(r[0],r[1]) for r in self.db.execute('SELECT warehouse_id,item_id FROM inventory_positions WHERE CAST(quantity AS REAL)<0 OR CAST(value AS REAL)<-0.01')]
    def zero_quantity_nonzero_value(self)->list[tuple[str,str,Decimal]]:
        return [(r[0],r[1],Decimal(r[2])) for r in self.db.execute("SELECT warehouse_id,item_id,value FROM inventory_positions WHERE ABS(CAST(quantity AS REAL))<0.0001 AND ABS(CAST(value AS REAL))>0.01")]
    def assert_balanced_positions(self)->None:
        bad=self.negative_positions()+[(w,i) for w,i,_ in self.zero_quantity_nonzero_value()]
        if bad:raise ValueError(f'invalid inventory positions: {bad[:5]}')
    def warehouse_snapshot(self,warehouse_id:str)->dict[str,tuple[Decimal,Decimal]]:
        return {r[0]:(Decimal(r[1]),Decimal(r[2])) for r in self.db.execute('SELECT item_id,quantity,value FROM inventory_positions WHERE warehouse_id=? ORDER BY item_id',(warehouse_id,))}
