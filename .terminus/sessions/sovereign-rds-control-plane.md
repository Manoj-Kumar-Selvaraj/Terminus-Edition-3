# sovereign-rds-control-plane

## Identity
- task: `sovereign-rds-control-plane`
- TASK_COMMIT: pending after Python 3.13 wheel pin fix
- control_plane_commit (live): `474f2b09fcda1848ef64d894a1b702be4f923b2b`

## Status
- Ledger compact (15 live events) published on `bfb087f3`
- Hosted DET reconstruct PASS on run 33950616194
- Oracle/NOP failed: `psycopg-binary==3.1.18` has no cp313 wheels; `pydantic-core` also lacks wheels for pinned stack
- Fix: bump `environment/requirements.txt` to 3.13-compatible pins (`psycopg 3.2.9`, `pydantic 2.10.6`, `pyyaml 6.0.2`); local `docker build` OK
