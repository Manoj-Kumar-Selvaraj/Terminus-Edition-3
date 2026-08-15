from __future__ import annotations
from dataclasses import dataclass
from decimal import Decimal
from typing import Iterable

SIGNED_SIGNS={0xC:1,0xD:-1}
UNSIGNED_SIGNS={0xF:1}

@dataclass(frozen=True)
class PackedSpec:
    digits:int
    scale:int=0
    signed:bool=True
    @property
    def byte_length(self)->int: return (self.digits+2)//2
    def validate(self)->None:
        if self.digits<=0: raise ValueError("digits must be positive")
        if self.scale<0 or self.scale>self.digits: raise ValueError("invalid scale")

def _nibbles(data:bytes)->list[int]:
    out=[]
    for b in data: out.extend((b>>4,b&0x0F))
    return out

def unpack(data:bytes,spec:PackedSpec)->Decimal:
    spec.validate()
    if len(data)!=spec.byte_length: raise ValueError(f"packed length {len(data)} != {spec.byte_length}")
    nib=_nibbles(data); sign=nib[-1]; digits=nib[:-1]
    needed=spec.digits
    if len(digits)==needed+1:
        if digits[0]!=0: raise ValueError("non-zero storage padding nibble")
        digits=digits[1:]
    if len(digits)!=needed: raise ValueError("packed digit geometry mismatch")
    if any(d>9 for d in digits): raise ValueError("invalid packed decimal digit nibble")
    signs=SIGNED_SIGNS if spec.signed else UNSIGNED_SIGNS
    if sign not in signs: raise ValueError("invalid packed decimal sign nibble")
    integer=0
    for d in digits: integer=integer*10+d
    value=Decimal(integer).scaleb(-spec.scale)
    return value*signs[sign]

def pack(value:Decimal,spec:PackedSpec)->bytes:
    spec.validate(); quant=Decimal(1).scaleb(-spec.scale); value=value.quantize(quant)
    negative=value<0
    if negative and not spec.signed: raise ValueError("unsigned packed field cannot encode negative value")
    scaled=int(abs(value).scaleb(spec.scale))
    text=f"{scaled:0{spec.digits}d}"
    if len(text)>spec.digits: raise OverflowError("packed value exceeds PIC digits")
    digits=[int(ch) for ch in text]
    sign=0xD if negative else (0xC if spec.signed else 0xF)
    n=digits+[sign]
    if len(n)%2: n=[0]+n
    return bytes((n[i]<<4)|n[i+1] for i in range(0,len(n),2))

def display_decode(data:bytes,digits:int,scale:int=0,signed:bool=False)->Decimal:
    text=data.decode("ascii")
    sign=1
    if signed and text and text[0] in "+-":
        if text[0]=="-": sign=-1
        text=text[1:]
    if len(text)!=digits or not text.isdigit(): raise ValueError("invalid DISPLAY numeric")
    return Decimal(int(text)).scaleb(-scale)*sign

def display_encode(value:Decimal,digits:int,scale:int=0,signed:bool=False)->bytes:
    q=Decimal(1).scaleb(-scale); value=value.quantize(q); neg=value<0
    scaled=int(abs(value).scaleb(scale)); body=f"{scaled:0{digits}d}"
    if len(body)>digits: raise OverflowError("DISPLAY overflow")
    if signed: body=("-" if neg else "+")+body
    elif neg: raise ValueError("unsigned DISPLAY cannot encode negative")
    return body.encode("ascii")

def validate_roundtrip(values:Iterable[Decimal],spec:PackedSpec)->bool:
    return all(unpack(pack(v,spec),spec)==v.quantize(Decimal(1).scaleb(-spec.scale)) for v in values)

def packed_length(digits:int)->int:
    if digits<=0: raise ValueError("digits must be positive")
    return (digits+2)//2

def split_signed_zone(sign:int)->str:
    if sign==0xC: return "positive"
    if sign==0xD: return "negative"
    if sign==0xF: return "unsigned"
    return "invalid"

def decimal_digits(value:Decimal,scale:int)->str:
    q=value.copy_abs().quantize(Decimal(1).scaleb(-scale))
    return f"{int(q.scaleb(scale)):d}"

def normalize_currency(value:Decimal)->Decimal: return value.quantize(Decimal("0.01"))
def normalize_quantity(value:Decimal)->Decimal: return value.quantize(Decimal("0.001"))
def is_valid_digit_nibble(n:int)->bool: return 0<=n<=9
def is_signed_sign(n:int)->bool: return n in SIGNED_SIGNS
def is_unsigned_sign(n:int)->bool: return n in UNSIGNED_SIGNS
