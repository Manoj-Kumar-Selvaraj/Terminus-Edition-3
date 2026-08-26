# Sovereign RDS Control Plane

Local Python + PostgreSQL 16 control plane that implements RDS-style instance lifecycle, WAL-backed PITR, parameter-group apply modes, replica promotion, Multi-AZ failover fencing, and EventBridge outbox delivery.

## Layout

- `environment/` — control plane sources and compose lab under `environment/rds/`
- `solution/` — reference overlays and `solve.sh`
- `tests/` — verifier image and pytest suite

## Local checks

```bash
# Starter (NOP)
RDS_HOME=/path/to/environment/rds PYTHONPATH=/path/to/environment/rds \
  pytest tests/test_outputs.py -q

# After applying solution overlays
bash solution/solve.sh
RDS_HOME=/app/rds PYTHONPATH=/app/rds pytest tests/test_outputs.py -q
```
