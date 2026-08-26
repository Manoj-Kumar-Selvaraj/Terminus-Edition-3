# sovereign-rds-control-plane

## Identity
- task: `sovereign-rds-control-plane`
- branch: `main`
- TASK_COMMIT: _(set after remediation commit)_
- prior TASK_COMMIT: `80f30305a5d92128e780ee16a2227e2c195a68c8`

## Modes
- TERMINUS_Q4_Q6_MODE: AUTOMATED (packet-bound isolated subagent reviews)
- TERMINUS_Q8_MODE: OFF

## Deterministic local evidence (post-remediation, pre-commit)
- NOP pytest: 30 failed / 4 passed
- Oracle overlays: 34 passed
- Complexity gate: PASS (`large_system_strict`, substantive_loc=3575)
- Reachability: operator substantive ~3409 LOC; unreachable modules 0
- Ruff on `tests/test_outputs.py`: clean
- Test map: 34/34 (30 F2P + 4 P2P); no undeclared 35th F2P

## Remediation applied after 80f30305 quality wave
1. **Instruction / HQ**: Rewrote `instruction.md` as objective + end-state prose and grouped bullets; binds `/app/rds/docs/*`; offline/fail-closed/READY/checkpoints/tenant isolation discoverable.
2. **Q3 AMB**: Docs + contracts aligned for inclusive PITR window, `replication_lag_bytes` / 10485760, reset dual pending flags, SourceType+category (not SourceIdentifier match), health reason tokens, VIP evidence, promote endpoints vs failover VIP, digest on snapshot only.
3. **Q6**: Wired formerly dead modules into entrypoints; leaf traps retained so NOP stays 30/4.
4. **Q2**: Strengthened transactional outbox ordering assertion inside existing F2P; companion-artifact existence F2P not added (map stays 34). Updated `solver-visible-requirements.json`. Softened operator-contract/architecture/README so they are not a second acceptance checklist.

## Quality interlock
- Blocking until Q4 PASS + Q6 PASS on the new TASK_COMMIT.
