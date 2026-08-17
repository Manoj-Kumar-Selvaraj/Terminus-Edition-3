from __future__ import annotations
from dataclasses import dataclass
from decimal import Decimal
import sqlite3
from .policy import ItemPolicy,WarehousePolicy

@dataclass(frozen=True)
class ItemRecord:
    item_id:str
    active:bool
    max_unit_cost:Decimal
    quantity_precision:int
    category:str
    velocity_class:str
    lot_controlled:bool

@dataclass(frozen=True)
class WarehouseRecord:
    warehouse_id:str
    active:bool
    region:str
    timezone:str
    financial_entity:str

class Catalog:
    def __init__(self,db:sqlite3.Connection): self.db=db
    def item(self,item_id:str)->ItemRecord|None:
        row=self.db.execute("SELECT item_id,active,max_unit_cost,quantity_precision FROM items WHERE item_id=?",(item_id,)).fetchone()
        if row is None:return None
        n=int(item_id[3:]) if item_id.startswith('SKU') and item_id[3:].isdigit() else 0
        return ItemRecord(row[0],bool(row[1]),Decimal(row[2]),int(row[3]),self._category(n),self._velocity(n),n%17==0)
    def warehouse(self,warehouse_id:str)->WarehouseRecord|None:
        row=self.db.execute("SELECT warehouse_id,active FROM warehouses WHERE warehouse_id=?",(warehouse_id,)).fetchone()
        if row is None:return None
        n=int(warehouse_id[1:]) if warehouse_id.startswith('W') and warehouse_id[1:].isdigit() else 0
        return WarehouseRecord(row[0],bool(row[1]),self._region(n),self._timezone(n),f"ENT-{1+(n%3):02d}")
    def item_policy(self,item_id:str)->ItemPolicy|None:
        record=self.item(item_id)
        return None if record is None else ItemPolicy(record.item_id,record.active,False,record.max_unit_cost,record.quantity_precision)
    def warehouse_policy(self,warehouse_id:str)->WarehousePolicy|None:
        record=self.warehouse(warehouse_id)
        return None if record is None else WarehousePolicy(record.warehouse_id,record.active,True,True,True)
    def all_warehouse_policies(self)->dict[str,WarehousePolicy]:
        out={}
        for row in self.db.execute("SELECT warehouse_id FROM warehouses ORDER BY warehouse_id"):
            policy=self.warehouse_policy(row[0])
            if policy:out[row[0]]=policy
        return out
    def active_item_count(self)->int:
        return int(self.db.execute("SELECT COUNT(*) FROM items WHERE active=1").fetchone()[0])
    def active_warehouse_count(self)->int:
        return int(self.db.execute("SELECT COUNT(*) FROM warehouses WHERE active=1").fetchone()[0])
    def item_ids(self,active_only:bool=True)->list[str]:
        sql="SELECT item_id FROM items"+(" WHERE active=1" if active_only else "")+" ORDER BY item_id"
        return [r[0] for r in self.db.execute(sql)]
    def warehouse_ids(self,active_only:bool=True)->list[str]:
        sql="SELECT warehouse_id FROM warehouses"+(" WHERE active=1" if active_only else "")+" ORDER BY warehouse_id"
        return [r[0] for r in self.db.execute(sql)]
    def require_item(self,item_id:str)->ItemRecord:
        result=self.item(item_id)
        if result is None:raise KeyError(f"unknown item {item_id}")
        return result
    def require_warehouse(self,warehouse_id:str)->WarehouseRecord:
        result=self.warehouse(warehouse_id)
        if result is None:raise KeyError(f"unknown warehouse {warehouse_id}")
        return result
    def _category(self,n:int)->str:
        categories=("CONSUMABLE","ELECTRONICS","APPAREL","HARDWARE","SERVICE_PART","CHEMICAL","PACKAGING","OTHER")
        return categories[n%len(categories)]
    def _velocity(self,n:int)->str:
        if n%10 in (0,1):return "A"
        if n%10 in (2,3,4):return "B"
        return "C"
    def _region(self,n:int)->str:
        regions=("NA-EAST","NA-WEST","EU-CENTRAL","AP-SOUTH")
        return regions[n%len(regions)]
    def _timezone(self,n:int)->str:
        zones=("America/New_York","America/Los_Angeles","Europe/Berlin","Asia/Kolkata")
        return zones[n%len(zones)]
    def snapshot(self)->dict[str,object]:
        return {"active_items":self.active_item_count(),"active_warehouses":self.active_warehouse_count(),"items":len(self.item_ids(False)),"warehouses":len(self.warehouse_ids(False))}
