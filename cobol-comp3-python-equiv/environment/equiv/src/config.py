from __future__ import annotations
from dataclasses import dataclass,asdict
from decimal import Decimal
import json
from pathlib import Path

@dataclass(frozen=True)
class Paths:
    source:Path
    layout:Path
    database:Path
    schema:Path
    seed:Path
    legacy_controls:Path
    reports:Path
    publications:Path
    audit:Path
    quarantine:Path
    registry:Path
    def input_paths(self)->tuple[Path,...]:return (self.source,self.layout,self.schema,self.seed,self.legacy_controls)
    def output_dirs(self)->tuple[Path,...]:return (self.reports,self.publications,self.audit.parent,self.quarantine.parent,self.registry.parent)
@dataclass(frozen=True)
class Limits:
    max_record_bytes:int=4096
    max_attributes:int=3
    max_quantity:Decimal=Decimal('9999999.999')
    max_unit_cost:Decimal=Decimal('9999999.99')
    checkpoint_interval:int=1
    max_reject_rate:Decimal=Decimal('0.10')
    lock_ttl_seconds:int=900
    def validate(self)->None:
        if self.max_record_bytes<64:raise ValueError('max_record_bytes too small')
        if self.max_attributes<0:raise ValueError('max_attributes cannot be negative')
        if self.max_quantity<=0:raise ValueError('max_quantity must be positive')
        if self.max_unit_cost<0:raise ValueError('max_unit_cost cannot be negative')
        if self.checkpoint_interval<1:raise ValueError('checkpoint_interval must be positive')
        if self.max_reject_rate<0 or self.max_reject_rate>1:raise ValueError('max_reject_rate must be between 0 and 1')
        if self.lock_ttl_seconds<30:raise ValueError('lock_ttl_seconds too small')
@dataclass(frozen=True)
class CutoverConfig:
    business_date:str
    producer:str
    batch_id:str
    owner:str
    environment:str
    paths:Paths
    limits:Limits=Limits()
    strict_reconciliation:bool=True
    require_operator_ack:bool=True
    publish_on_success:bool=True
    def validate(self)->None:
        if len(self.business_date)!=8 or not self.business_date.isdigit():raise ValueError('business_date must be YYYYMMDD')
        if not self.producer.strip():raise ValueError('producer required')
        if not self.batch_id.strip():raise ValueError('batch_id required')
        if not self.owner.strip():raise ValueError('owner required')
        if self.environment not in {'dev','test','stage','prod'}:raise ValueError('environment must be dev/test/stage/prod')
        self.limits.validate()
        missing=[str(p) for p in self.paths.input_paths() if not p.exists()]
        if missing:raise ValueError('missing cutover input path(s): '+', '.join(missing))
    def prepare_outputs(self)->None:
        for p in self.paths.output_dirs():p.mkdir(parents=True,exist_ok=True)
    def as_json(self)->dict[str,object]:
        return {'business_date':self.business_date,'producer':self.producer,'batch_id':self.batch_id,'owner':self.owner,'environment':self.environment,'paths':{k:str(v) for k,v in asdict(self.paths).items()},'limits':{k:str(v) if isinstance(v,Decimal) else v for k,v in asdict(self.limits).items()},'strict_reconciliation':self.strict_reconciliation,'require_operator_ack':self.require_operator_ack,'publish_on_success':self.publish_on_success}
def from_dict(data:dict[str,object])->CutoverConfig:
    raw_paths=dict(data['paths']);paths=Paths(**{k:Path(v) for k,v in raw_paths.items()});raw_limits=dict(data.get('limits',{}))
    for key in ('max_quantity','max_unit_cost','max_reject_rate'):
        if key in raw_limits:raw_limits[key]=Decimal(str(raw_limits[key]))
    limits=Limits(**raw_limits)
    cfg=CutoverConfig(str(data['business_date']),str(data['producer']),str(data['batch_id']),str(data['owner']),str(data.get('environment','prod')),paths,limits,bool(data.get('strict_reconciliation',True)),bool(data.get('require_operator_ack',True)),bool(data.get('publish_on_success',True)))
    return cfg
def load(path:str|Path)->CutoverConfig:
    cfg=from_dict(json.loads(Path(path).read_text(encoding='utf-8')));cfg.validate();return cfg
def save(config:CutoverConfig,path:str|Path)->None:
    config.validate();Path(path).write_text(json.dumps(config.as_json(),indent=2,sort_keys=True)+'\n',encoding='utf-8')
def default_paths(root:str|Path)->Paths:
    root=Path(root)
    return Paths(root/'samples/movements.dat',root/'config/movement.layout.json',root/'state/equiv.db',root/'sql/schema.sql',root/'sql/seed.sql',root/'config/legacy.controls',root/'out/reports',root/'out/published',root/'out/audit/events.jsonl',root/'out/quarantine/records.jsonl',root/'out/publication-registry.jsonl')
def default(root:str|Path,business_date:str)->CutoverConfig:return CutoverConfig(business_date,'legacy-wms','daily-inventory-cutover','warehouse-operations','prod',default_paths(root))
def changed(a:CutoverConfig,b:CutoverConfig)->list[str]:
    out=[]
    if a.business_date!=b.business_date:out.append('business_date')
    if a.producer!=b.producer:out.append('producer')
    if a.batch_id!=b.batch_id:out.append('batch_id')
    if a.owner!=b.owner:out.append('owner')
    if a.environment!=b.environment:out.append('environment')
    if a.paths!=b.paths:out.append('paths')
    if a.limits!=b.limits:out.append('limits')
    if a.strict_reconciliation!=b.strict_reconciliation:out.append('strict_reconciliation')
    if a.require_operator_ack!=b.require_operator_ack:out.append('require_operator_ack')
    if a.publish_on_success!=b.publish_on_success:out.append('publish_on_success')
    return out
def validate_output_separation(config:CutoverConfig)->None:
    inputs={p.resolve() for p in config.paths.input_paths() if p.exists()}
    for directory in config.paths.output_dirs():
        resolved=directory.resolve()
        if resolved in inputs:
            raise ValueError(f'output directory overlaps an input path: {resolved}')

def require_production_defaults(config:CutoverConfig)->None:
    if config.environment!='prod':
        return
    if not config.strict_reconciliation:
        raise ValueError('production cutover requires strict reconciliation')
    if not config.require_operator_ack:
        raise ValueError('production cutover requires operator acknowledgement')
    if not config.publish_on_success:
        raise ValueError('production cutover must publish successful reconciliations')
    if config.limits.checkpoint_interval!=1:
        raise ValueError('production cutover checkpoints every durable movement')

def validate_all(config:CutoverConfig)->None:
    config.validate()
    validate_output_separation(config)
    require_production_defaults(config)
