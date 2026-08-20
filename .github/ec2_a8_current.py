#!/usr/bin/env python3
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys

ROOT=Path('.')
WORK=Path(sys.argv[1]); WORK.mkdir(parents=True,exist_ok=True)
TASK=os.environ['TASK']; TASK_COMMIT=os.environ['TASK_COMMIT']; CONTROL=os.environ['CONTROL_COMMIT']
TASK_HASH=os.environ['TASK_HASH']; CONTROL_HASH=os.environ['CONTROL_HASH']

inputs={
 'APPROVED_WORK_PACKAGE':{
  'ID':'WP1_UNIFIED_EC2_ARTIFACT_ADMISSION',
  'ENGINEERING_OBJECTIVE':'Unify OS-package, container, and build-dependency acquisition behind one Go policy engine.',
  'REQUIRED_END_STATE':'All acquisition surfaces enforce trusted sources, immutable digests, current scanner/cache evidence, scoped current vulnerability exceptions, exact-scope secret-keyed permits with replay safety, and durable restart-safe allow/deny audit history.'},
 'IMPLEMENTATION_EVIDENCE':{
  'REFERENCE_SOLUTION_STATUS':'IMPLEMENTED',
  'RESTORED_INVARIANTS':['one source/digest policy boundary across package, container and dependency managers','current scanner evidence and cache identity bound to digest, policy version, scanner DB revision and TTL','exact current vulnerability exceptions that cannot bypass prerequisites','secret-keyed exact-scope permits with optional durable single-use replay enforcement','durable ALLOW/DENY audit before derived projection and crash-safe state transitions','restart/concurrency-safe idempotency and replay semantics'],
  'PRESERVED_BEHAVIOR':['artifactguard evaluate and verify-permit interfaces and documented exits','valid cache reuse and valid scoped exceptions','supplied policy/scanner/exception fixtures','existing audit history'],
  'DETERMINISM':'caller-provided time, local fixtures, local state and no required network dependency'},
 'VERIFICATION_EVIDENCE':{
  'VERIFIER_STATUS':'VERIFIER_READY','F2P_COUNT':27,'P2P_COUNT':9,
  'COVERAGE_FAMILIES':['source/digest prerequisites across acquisition managers','scanner/cache freshness and corruption','exception expiry/scope/prerequisite ordering','permit authentication, scope and restart/concurrent replay','audit durability, projection, recovery and idempotent retry','healthy behavior, cache, stateless permit and fixture preservation'],
  'SPEC_ALIGNMENT':{'Q1_STATUS':'NO_GAP','Q2_STATUS':'COVERED','Q3_STATUS':'CLEAR'},
  'EMPIRICAL_STATUS':'Runtime/oracle validation remains mandatory at the later deterministic-validation checkpoint; no pass claim is made at documentation time.'}}
(WORK/'inputs.json').write_text(json.dumps(inputs,indent=2,sort_keys=True)+'\n')

def run(*args): subprocess.run(args,cwd=ROOT,check=True)
run('python3','.terminus/execution/controller_cli.py','continue','--task-id',TASK,'--task-commit',TASK_COMMIT,'--control-plane-commit',CONTROL,'--inputs-json',str(WORK/'inputs.json'),'--output',str(WORK/'continue.json'))
payload=json.loads((WORK/'continue.json').read_text()); inv=payload.get('invocation')
assert payload.get('next',{}).get('stage_id')=='DOCUMENTATION_DRAFT',payload.get('next')
assert payload.get('execution_mode')=='INLINE_SPECIALIST',payload.get('execution_mode')
assert isinstance(inv,dict) and inv.get('readiness')=='READY'
(WORK/'invocation.json').write_text(json.dumps(inv,indent=2,sort_keys=True)+'\n')

readme='''# ArtifactGuard EC2 Software Acquisition Gate

ArtifactGuard is the host-local admission client used by governed EC2 instances before software is acquired. It applies one policy model to operating-system packages, OCI container images, and build dependencies so changing package managers or using a lower-level installer does not create a policy bypass.

## Public interfaces

The existing command surface is part of the compatibility contract:

- `artifactguard evaluate` evaluates an acquisition request. Policy denials use exit code `42`; malformed input or operational failures use exit code `2`.
- `artifactguard verify-permit` verifies an issued decision permit. Invalid, expired, out-of-scope, or replayed stateful permits use exit code `43`.

Permit verification remains compatible with stateless callers. When replay state is supplied with `--state`, the first exact valid use records consumption and later or concurrent attempts to consume the same permit are rejected.

## Admission policy

Every request belongs to one acquisition surface: package, container, or dependency. Manager-specific input is normalized into that shared policy boundary. Source trust and required immutable-digest checks are prerequisites; an exception cannot make an untrusted source or missing required digest acceptable.

A request may proceed only with current vulnerability evidence. Scanner results must be usable for the active scanner database revision. Cached evidence is reusable only while it still represents the same immutable artifact and active policy/scanner state within its TTL. Mutable names such as image tags, package versions, or dependency coordinates are not substitutes for immutable digest identity. Scanner unavailability, stale evidence, or corrupt evidence must fail closed.

Vulnerability exceptions are narrow waivers for the vulnerability threshold only. A usable exception must be current and match the exact artifact digest, acquisition surface, environment, and policy code. It does not override source, digest, or scanner-evidence prerequisites.

## Decision permits

An ALLOW decision can issue a short-lived permit. Permit integrity is secret-keyed and covers the exact request, EC2 instance, artifact digest, policy version, and expiry. Changing any bound field must invalidate the permit. Stateful verification additionally enforces durable single use across process restart and concurrent verification.

## Durable state and recovery

The caller-provided state directory contains reusable scan evidence, the decision journal, the latest-decision projection, and optional permit-consumption state. The decision journal is authoritative: every ALLOW and DENY is durably appended before the command reports completion, and the derived latest-decision view may advance only after the corresponding journal record is durable.

Repeated evaluation of an identical deterministic request is idempotent and must not duplicate an already committed decision. Recovery preserves valid history. A complete final JSON journal record remains valid even when its trailing newline was not durable; malformed durable history is treated as corruption and new operations fail closed rather than silently truncating or extending that history.

## Engineering constraints

Keep the shipped policy, scanner, and exception fixtures unchanged. They provide deterministic local inputs for development and CI; repairs belong in the policy runtime and state machinery rather than in fixture data. Existing audit history, healthy cache behavior, valid scoped exceptions, and documented CLI behavior must remain intact while security and recovery invariants are restored.

Start with `environment/enforcer/notes/oncall.md` for the observed failure modes. The governing behavior is documented in `environment/enforcer/docs/policy-contract.md`, `environment/enforcer/docs/state-format.md`, `environment/enforcer/docs/operations.md`, and `environment/enforcer/docs/architecture.md`.

From `environment/enforcer`, use `go test ./...` and `go build ./cmd/artifactguard` for the Go module checks. The task-level behavioral verifier exercises the public CLI and durable state across normal, negative, restart, corruption, and concurrency scenarios.
'''
path=ROOT/TASK/'README.md'; path.write_text(readme)
forbidden=['Terminus','benchmark','Oracle','F2P','P2P','hidden test','reference solution','intentional defect']
bad=[x for x in forbidden if x.lower() in readme.lower()]
if bad: raise SystemExit('README leakage/framing: '+', '.join(bad))
required=['artifactguard evaluate','artifactguard verify-permit','exit code `42`','exit code `43`','--state','durably','fail closed']
missing=[x for x in required if x not in readme]
if missing: raise SystemExit('README missing engineering contract: '+', '.join(missing))

result={
 'schema_version':'1.0','invocation_id':inv['invocation_id'],'output_task_commit':TASK_COMMIT,'status':'DOCUMENTATION_READY',
 'outputs':{
  'README_PATH':f'{TASK}/README.md',
  'DIFFICULTY_EXPLANATION':'The engineering difficulty is the coupling between canonical artifact identity, fail-closed evidence freshness, exact exception scope, permit authentication/replay, and crash-safe durable state. A local fix to only one manager, cache field, permit check, or projection can leave another acquisition or restart/concurrency path inconsistent.',
  'SOLUTION_EXPLANATION':'The reference repair restores one normalized package/container/dependency admission pipeline; binds cache evidence to immutable digest plus policy/scanner freshness; restricts exceptions to exact current vulnerability scope; authenticates exact-scope permits with secret-keyed integrity and optional durable single-use replay state; and commits ALLOW/DENY journal state durably before derived projection while preserving idempotent retry and recovery semantics.',
  'VERIFICATION_EXPLANATION':'The verifier maps the public contract to 27 failure-to-pass and 9 preservation cases covering manager/source/digest policy, scanner/cache freshness, exception scope/order, permit authentication and replay, audit/recovery/idempotency, healthy cache/stateless-permit compatibility, and fixture preservation. SPEC_ALIGNMENT is current with Q1=NO_GAP, Q2=COVERED, Q3=CLEAR. Runtime/oracle success is deliberately not claimed here and remains mandatory downstream.'},
 'evidence_refs':[{'kind':'COMMIT','ref':f'commit:{TASK_COMMIT}','content_hash':TASK_HASH},{'kind':'COMMIT','ref':f'commit:{CONTROL}','content_hash':CONTROL_HASH}]}
(WORK/'result.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
run('python3','.terminus/execution/controller_cli.py','record','--invocation',str(WORK/'invocation.json'),'--result',str(WORK/'result.json'),'--output',str(WORK/'record.json'))
record=json.loads((WORK/'record.json').read_text())['record']
assert record['status']=='DOCUMENTATION_READY' and record['transition'].get('target')=='FORMAT_GATE',record
print(f'A8 invocation={inv["invocation_id"]} record={record["record_id"]}')
