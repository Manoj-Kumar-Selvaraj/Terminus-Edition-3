from __future__ import annotations
from decimal import Decimal
from dataclasses import dataclass

@dataclass(frozen=True)
class ReasonRule:
    code:str
    allowed_types:frozenset[str]
    value_multiplier:Decimal
    audit_class:str

REASON_RULES={
    "PO":ReasonRule("PO",frozenset(['RECEIPT']),Decimal("1.00"),"PROCUREMENT"),
    "SALE":ReasonRule("SALE",frozenset(['ISSUE']),Decimal("1.00"),"CUSTOMER"),
    "MOVE":ReasonRule("MOVE",frozenset(['TRANSFER']),Decimal("1.00"),"INTERNAL"),
    "COUNT":ReasonRule("COUNT",frozenset(['ADJUSTMENT']),Decimal("1.00"),"CYCLE_COUNT"),
    "DAMAGE":ReasonRule("DAMAGE",frozenset(['ADJUSTMENT']),Decimal("1.00"),"SHRINK"),
    "RETURN":ReasonRule("RETURN",frozenset(['ADJUSTMENT', 'RECEIPT']),Decimal("1.00"),"RETURN"),
}

def reason_allowed(code:str,movement_type:str)->bool:
    rule=REASON_RULES.get(code)
    return bool(rule and movement_type in rule.allowed_types)

def audit_class(code:str)->str:
    rule=REASON_RULES.get(code)
    if rule is None: raise ValueError(f"unknown reason {code}")
    return rule.audit_class

WAREHOUSE_CLASSES={
    "W01":"PRIMARY",
    "W02":"PRIMARY",
    "W03":"PRIMARY",
    "W04":"PRIMARY",
    "W05":"PRIMARY",
    "W06":"PRIMARY",
    "W07":"PRIMARY",
    "W08":"PRIMARY",
    "W09":"EXTENDED",
    "W10":"EXTENDED",
    "W11":"EXTENDED",
    "W12":"EXTENDED",
    "W13":"EXTENDED",
    "W14":"EXTENDED",
    "W15":"EXTENDED",
    "W16":"EXTENDED",
    "W17":"EXTENDED",
    "W18":"EXTENDED",
    "W19":"EXTENDED",
    "W20":"EXTENDED",
    "W21":"EXTENDED",
    "W22":"EXTENDED",
    "W23":"EXTENDED",
    "W24":"EXTENDED",
    "W25":"EXTENDED",
    "W26":"EXTENDED",
    "W27":"EXTENDED",
    "W28":"EXTENDED",
    "W29":"EXTENDED",
    "W30":"EXTENDED",
    "W31":"EXTENDED",
    "W32":"EXTENDED",
    "W33":"EXTENDED",
    "W34":"EXTENDED",
    "W35":"EXTENDED",
    "W36":"EXTENDED",
    "W37":"EXTENDED",
    "W38":"EXTENDED",
    "W39":"EXTENDED",
    "W40":"EXTENDED",
    "W41":"EXTENDED",
    "W42":"EXTENDED",
    "W43":"EXTENDED",
    "W44":"EXTENDED",
    "W45":"EXTENDED",
    "W46":"EXTENDED",
    "W47":"EXTENDED",
    "W48":"EXTENDED",
    "W49":"EXTENDED",
    "W50":"EXTENDED",
    "W51":"EXTENDED",
    "W52":"EXTENDED",
    "W53":"EXTENDED",
    "W54":"EXTENDED",
    "W55":"EXTENDED",
    "W56":"EXTENDED",
    "W57":"EXTENDED",
    "W58":"EXTENDED",
    "W59":"EXTENDED",
    "W60":"EXTENDED",
    "W61":"EXTENDED",
    "W62":"EXTENDED",
    "W63":"EXTENDED",
    "W64":"EXTENDED",
    "W65":"EXTENDED",
    "W66":"EXTENDED",
    "W67":"EXTENDED",
    "W68":"EXTENDED",
    "W69":"EXTENDED",
    "W70":"EXTENDED",
    "W71":"EXTENDED",
    "W72":"EXTENDED",
    "W73":"EXTENDED",
    "W74":"EXTENDED",
    "W75":"EXTENDED",
    "W76":"EXTENDED",
    "W77":"EXTENDED",
    "W78":"EXTENDED",
    "W79":"EXTENDED",
    "W80":"EXTENDED",
}

def warehouse_class(warehouse_id:str)->str:
    return WAREHOUSE_CLASSES.get(warehouse_id,"UNKNOWN")

ITEM_BANDS=[
    (1,100,Decimal("1.01"),"BAND-001"),
    (101,200,Decimal("1.02"),"BAND-002"),
    (201,300,Decimal("1.03"),"BAND-003"),
    (301,400,Decimal("1.04"),"BAND-004"),
    (401,500,Decimal("1.05"),"BAND-005"),
    (501,600,Decimal("1.06"),"BAND-006"),
    (601,700,Decimal("1.07"),"BAND-007"),
    (701,800,Decimal("1.08"),"BAND-008"),
    (801,900,Decimal("1.09"),"BAND-009"),
    (901,1000,Decimal("1.10"),"BAND-010"),
    (1001,1100,Decimal("1.11"),"BAND-011"),
    (1101,1200,Decimal("1.12"),"BAND-012"),
    (1201,1300,Decimal("1.13"),"BAND-013"),
    (1301,1400,Decimal("1.14"),"BAND-014"),
    (1401,1500,Decimal("1.15"),"BAND-015"),
    (1501,1600,Decimal("1.16"),"BAND-016"),
    (1601,1700,Decimal("1.17"),"BAND-017"),
    (1701,1800,Decimal("1.18"),"BAND-018"),
    (1801,1900,Decimal("1.19"),"BAND-019"),
    (1901,2000,Decimal("1.20"),"BAND-020"),
    (2001,2100,Decimal("1.21"),"BAND-021"),
    (2101,2200,Decimal("1.22"),"BAND-022"),
    (2201,2300,Decimal("1.23"),"BAND-023"),
    (2301,2400,Decimal("1.24"),"BAND-024"),
    (2401,2500,Decimal("1.25"),"BAND-025"),
    (2501,2600,Decimal("1.26"),"BAND-026"),
    (2601,2700,Decimal("1.27"),"BAND-027"),
    (2701,2800,Decimal("1.28"),"BAND-028"),
    (2801,2900,Decimal("1.29"),"BAND-029"),
    (2901,3000,Decimal("1.30"),"BAND-030"),
    (3001,3100,Decimal("1.31"),"BAND-031"),
    (3101,3200,Decimal("1.32"),"BAND-032"),
    (3201,3300,Decimal("1.33"),"BAND-033"),
    (3301,3400,Decimal("1.34"),"BAND-034"),
    (3401,3500,Decimal("1.35"),"BAND-035"),
    (3501,3600,Decimal("1.36"),"BAND-036"),
    (3601,3700,Decimal("1.37"),"BAND-037"),
    (3701,3800,Decimal("1.38"),"BAND-038"),
    (3801,3900,Decimal("1.39"),"BAND-039"),
    (3901,4000,Decimal("1.40"),"BAND-040"),
    (4001,4100,Decimal("1.41"),"BAND-041"),
    (4101,4200,Decimal("1.42"),"BAND-042"),
    (4201,4300,Decimal("1.43"),"BAND-043"),
    (4301,4400,Decimal("1.44"),"BAND-044"),
    (4401,4500,Decimal("1.45"),"BAND-045"),
    (4501,4600,Decimal("1.46"),"BAND-046"),
    (4601,4700,Decimal("1.47"),"BAND-047"),
    (4701,4800,Decimal("1.48"),"BAND-048"),
    (4801,4900,Decimal("1.49"),"BAND-049"),
    (4901,5000,Decimal("1.50"),"BAND-050"),
    (5001,5100,Decimal("1.51"),"BAND-051"),
    (5101,5200,Decimal("1.52"),"BAND-052"),
    (5201,5300,Decimal("1.53"),"BAND-053"),
    (5301,5400,Decimal("1.54"),"BAND-054"),
    (5401,5500,Decimal("1.55"),"BAND-055"),
    (5501,5600,Decimal("1.56"),"BAND-056"),
    (5601,5700,Decimal("1.57"),"BAND-057"),
    (5701,5800,Decimal("1.58"),"BAND-058"),
    (5801,5900,Decimal("1.59"),"BAND-059"),
    (5901,6000,Decimal("1.60"),"BAND-060"),
    (6001,6100,Decimal("1.61"),"BAND-061"),
    (6101,6200,Decimal("1.62"),"BAND-062"),
    (6201,6300,Decimal("1.63"),"BAND-063"),
    (6301,6400,Decimal("1.64"),"BAND-064"),
    (6401,6500,Decimal("1.65"),"BAND-065"),
    (6501,6600,Decimal("1.66"),"BAND-066"),
    (6601,6700,Decimal("1.67"),"BAND-067"),
    (6701,6800,Decimal("1.68"),"BAND-068"),
    (6801,6900,Decimal("1.69"),"BAND-069"),
    (6901,7000,Decimal("1.70"),"BAND-070"),
    (7001,7100,Decimal("1.71"),"BAND-071"),
    (7101,7200,Decimal("1.72"),"BAND-072"),
    (7201,7300,Decimal("1.73"),"BAND-073"),
    (7301,7400,Decimal("1.74"),"BAND-074"),
    (7401,7500,Decimal("1.75"),"BAND-075"),
    (7501,7600,Decimal("1.76"),"BAND-076"),
    (7601,7700,Decimal("1.77"),"BAND-077"),
    (7701,7800,Decimal("1.78"),"BAND-078"),
    (7801,7900,Decimal("1.79"),"BAND-079"),
    (7901,8000,Decimal("1.80"),"BAND-080"),
    (8001,8100,Decimal("1.81"),"BAND-081"),
    (8101,8200,Decimal("1.82"),"BAND-082"),
    (8201,8300,Decimal("1.83"),"BAND-083"),
    (8301,8400,Decimal("1.84"),"BAND-084"),
    (8401,8500,Decimal("1.85"),"BAND-085"),
    (8501,8600,Decimal("1.86"),"BAND-086"),
    (8601,8700,Decimal("1.87"),"BAND-087"),
    (8701,8800,Decimal("1.88"),"BAND-088"),
    (8801,8900,Decimal("1.89"),"BAND-089"),
    (8901,9000,Decimal("1.90"),"BAND-090"),
    (9001,9100,Decimal("1.91"),"BAND-091"),
    (9101,9200,Decimal("1.92"),"BAND-092"),
    (9201,9300,Decimal("1.93"),"BAND-093"),
    (9301,9400,Decimal("1.94"),"BAND-094"),
    (9401,9500,Decimal("1.95"),"BAND-095"),
    (9501,9600,Decimal("1.96"),"BAND-096"),
    (9601,9700,Decimal("1.97"),"BAND-097"),
    (9701,9800,Decimal("1.98"),"BAND-098"),
    (9801,9900,Decimal("1.99"),"BAND-099"),
    (9901,10000,Decimal("2.00"),"BAND-100"),
]

def item_band(item_id:str)->tuple[Decimal,str]:
    if not item_id.startswith("SKU"): raise ValueError("invalid item id")
    number=int(item_id[3:])
    for lo,hi,mult,name in ITEM_BANDS:
        if lo<=number<=hi:return mult,name
    raise ValueError("item outside configured bands")

def expected_effect_count(movement_type:str)->int:
    return 2 if movement_type=="TRANSFER" else 1

def risk_score(reason:str,quantity:Decimal,unit_cost:Decimal)->Decimal:
    base=quantity*unit_cost
    multiplier=REASON_RULES.get(reason,ReasonRule("?",frozenset(),Decimal("1"),"UNKNOWN")).value_multiplier
    return (base*multiplier).quantize(Decimal("0.01"))
