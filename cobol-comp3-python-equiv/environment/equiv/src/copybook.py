from __future__ import annotations
from dataclasses import dataclass
import re
from .layout import Field,Layout

LINE=re.compile(r'^\s*(\d{2})\s+([A-Z0-9-]+)(?:\s+REDEFINES\s+([A-Z0-9-]+))?(?:\s+PIC\s+([^ .]+))?(?:\s+(COMP-3))?(?:\s+OCCURS\s+(\d+)\s+TIMES(?:\s+DEPENDING\s+ON\s+([A-Z0-9-]+))?)?\.?\s*$',re.I)
@dataclass(frozen=True)
class CopybookEntry:
    level:int
    name:str
    picture:str|None
    usage:str|None
    occurs:int
    depending_on:str|None
    redefines:str|None

def parse_line(line:str)->CopybookEntry|None:
    stripped=line.strip()
    if not stripped or stripped.startswith('*'):return None
    m=LINE.match(line)
    if not m:raise ValueError(f'unsupported copybook line: {line.rstrip()}')
    level=int(m.group(1));name=m.group(2).upper();redefines=m.group(3).upper() if m.group(3) else None;picture=m.group(4).upper() if m.group(4) else None;usage=m.group(5).upper() if m.group(5) else None;occurs=int(m.group(6) or 1);depending=m.group(7).upper() if m.group(7) else None
    return CopybookEntry(level,name,picture,usage,occurs,depending,redefines)
def parse_copybook(text:str,layout_id:str='COPYBOOK')->Layout:
    entries=[e for line in text.splitlines() if (e:=parse_line(line)) is not None]
    fields=[]
    for e in entries:
        if e.picture is None:continue
        fields.append(Field(e.name,e.picture,e.usage or 'DISPLAY',e.occurs,e.depending_on,e.redefines))
    layout=Layout(layout_id,fields);layout.validate();return layout
def compare_copybook_to_layout(text:str,layout:Layout)->list[str]:
    parsed=parse_copybook(text,layout.layout_id);problems=[]
    if len(parsed.fields)!=len(layout.fields):problems.append(f'field count {len(parsed.fields)} != {len(layout.fields)}')
    for i,(a,b) in enumerate(zip(parsed.fields,layout.fields)):
        if a.name!=b.name:problems.append(f'field {i} name {a.name} != {b.name}')
        if a.picture!=b.picture:problems.append(f'{a.name} picture {a.picture} != {b.picture}')
        if a.usage!=b.usage:problems.append(f'{a.name} usage {a.usage} != {b.usage}')
        if a.occurs!=b.occurs:problems.append(f'{a.name} occurs {a.occurs} != {b.occurs}')
        if a.depending_on!=b.depending_on:problems.append(f'{a.name} ODO {a.depending_on} != {b.depending_on}')
        if a.redefines!=b.redefines:problems.append(f'{a.name} redefines {a.redefines} != {b.redefines}')
    return problems
def render(layout:Layout)->str:
    lines=['01 '+layout.layout_id+'.']
    for f in layout.fields:
        line=f'  05 {f.name}'
        if f.redefines:line+=f' REDEFINES {f.redefines}'
        line+=f' PIC {f.picture}'
        if f.usage!='DISPLAY':line+=f' {f.usage}'
        if f.occurs!=1:
            line+=f' OCCURS {f.occurs} TIMES'
            if f.depending_on:line+=f' DEPENDING ON {f.depending_on}'
        lines.append(line+'.')
    return '\n'.join(lines)+'\n'
