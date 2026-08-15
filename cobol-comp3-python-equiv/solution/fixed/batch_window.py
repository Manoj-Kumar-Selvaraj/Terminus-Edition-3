from __future__ import annotations
from dataclasses import dataclass
from datetime import date,datetime,time,timedelta,timezone
from zoneinfo import ZoneInfo

@dataclass(frozen=True)
class BatchWindow:
    business_date:date
    timezone_name:str
    opens_at:time
    closes_at:time
    grace_minutes:int=30
    def zone(self)->ZoneInfo:return ZoneInfo(self.timezone_name)
    def open_datetime(self)->datetime:return datetime.combine(self.business_date,self.opens_at,self.zone())
    def close_datetime(self)->datetime:return datetime.combine(self.business_date,self.closes_at,self.zone())
    def hard_close(self)->datetime:return self.close_datetime()+timedelta(minutes=self.grace_minutes)
    def contains(self,instant:datetime)->bool:
        local=instant.astimezone(self.zone());return self.open_datetime()<=local<=self.hard_close()
    def phase(self,instant:datetime)->str:
        local=instant.astimezone(self.zone())
        if local<self.open_datetime():return 'BEFORE'
        if local<=self.close_datetime():return 'OPEN'
        if local<=self.hard_close():return 'GRACE'
        return 'CLOSED'
def parse_business_date(value:str)->date:
    if len(value)!=8 or not value.isdigit():raise ValueError('business date must be YYYYMMDD')
    return date(int(value[:4]),int(value[4:6]),int(value[6:8]))
def default_window(value:str)->BatchWindow:return BatchWindow(parse_business_date(value),'UTC',time(0,0),time(23,30),30)
def now_utc()->datetime:return datetime.now(timezone.utc)
def require_open(window:BatchWindow,instant:datetime|None=None)->None:
    instant=instant or now_utc()
    if not window.contains(instant):raise ValueError(f'batch window is {window.phase(instant)}')
def publication_deadline(window:BatchWindow)->datetime:return window.hard_close()
def seconds_remaining(window:BatchWindow,instant:datetime|None=None)->int:
    instant=instant or now_utc();return max(0,int((window.hard_close().astimezone(timezone.utc)-instant.astimezone(timezone.utc)).total_seconds()))
