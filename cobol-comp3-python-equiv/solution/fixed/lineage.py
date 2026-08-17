from __future__ import annotations
from dataclasses import dataclass,asdict
from hashlib import sha256
import json
from pathlib import Path

@dataclass(frozen=True)
class LineageNode:
    node_id:str
    kind:str
    sha256:str
    size:int
    parents:tuple[str,...]
    metadata:dict[str,str]
@dataclass(frozen=True)
class LineageGraph:
    generation_id:str
    nodes:tuple[LineageNode,...]
    def ids(self)->set[str]:return {n.node_id for n in self.nodes}
    def validate(self)->None:
        ids=self.ids()
        if len(ids)!=len(self.nodes):raise ValueError('duplicate lineage node id')
        for n in self.nodes:
            if any(p not in ids for p in n.parents):raise ValueError(f'unknown lineage parent for {n.node_id}')
    def sinks(self)->list[LineageNode]:
        parents={p for n in self.nodes for p in n.parents};return [n for n in self.nodes if n.node_id not in parents]
def hash_path(path:str|Path)->tuple[str,int]:
    path=Path(path);h=sha256();size=0
    with path.open('rb') as f:
        for block in iter(lambda:f.read(65536),b''):h.update(block);size+=len(block)
    return h.hexdigest(),size
def source_node(node_id:str,kind:str,path:str|Path,metadata:dict[str,str]|None=None)->LineageNode:
    digest,size=hash_path(path);return LineageNode(node_id,kind,digest,size,tuple(),metadata or {})
def derived_node(node_id:str,kind:str,path:str|Path,parents:list[str],metadata:dict[str,str]|None=None)->LineageNode:
    digest,size=hash_path(path);return LineageNode(node_id,kind,digest,size,tuple(parents),metadata or {})
def write(graph:LineageGraph,path:str|Path)->None:
    graph.validate();Path(path).write_text(json.dumps({'generation_id':graph.generation_id,'nodes':[asdict(n) for n in graph.nodes]},indent=2,sort_keys=True)+"\n",encoding='utf-8')
def read(path:str|Path)->LineageGraph:
    data=json.loads(Path(path).read_text(encoding='utf-8'));graph=LineageGraph(data['generation_id'],tuple(LineageNode(**{**n,'parents':tuple(n['parents'])}) for n in data['nodes']));graph.validate();return graph
def verify_files(graph:LineageGraph,paths:dict[str,Path])->bool:
    graph.validate()
    for n in graph.nodes:
        if n.node_id not in paths:continue
        digest,size=hash_path(paths[n.node_id])
        if digest!=n.sha256 or size!=n.size:return False
    return True
