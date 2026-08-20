#!/usr/bin/env python3
from pathlib import Path

adapter = Path('.github/chat_inline_stage_adapter.py')
source = adapter.read_text(encoding='utf-8')
old_domain = "'--domain','terraform ansible provider platform cloud infrastructure linux managed resources lifecycle'"
new_domain = "'--domain','go http edge routing traffic management dynamic reconciliation runtime'"
old_profile = "task_profile={'voice':'direct platform engineering change request','structure':['state the inherited provider objective first','preserve exact public contracts and hard safety/state constraints','reference solver-visible technical contracts instead of reproducing hidden verifier rows','keep implementation-neutral observable outcomes'],'must_preserve':['ten documented resource interfaces','stable external-object identity','Ansible mutation versus native observation boundary','transactional state publication and retry semantics','scoped ownership/deletion','runner process safety','normalization/idempotency','Terraform Core sole durable state authority'],'avoid':['invented incidents or personal claims','rubric-like hidden-test enumeration','style-driven omission of lifecycle constraints','copied distinctive source wording']}"
new_profile = "task_profile={'voice':'direct platform engineering change request','structure':['state the inherited edge-router objective first','preserve exact public contracts and hard lifecycle/state constraints','reference solver-visible technical contracts instead of reproducing hidden verifier rows','keep implementation-neutral observable outcomes'],'must_preserve':['generation-safe publication','independent source authority','stable endpoint identity and incarnation','request snapshot consistency','bounded drain and retirement','durable checkpoint recovery','public edge-router contracts'],'avoid':['invented incidents or personal claims','rubric-like hidden-test enumeration','style-driven omission of lifecycle constraints','copied distinctive source wording']}"
if old_domain not in source or old_profile not in source:
    raise SystemExit('expected generic HWR adapter literals not found')
source = source.replace(old_domain, new_domain, 1).replace(old_profile, new_profile, 1)
exec(compile(source, str(adapter), 'exec'), {'__name__': '__main__', '__file__': str(adapter)})
