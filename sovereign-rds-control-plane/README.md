# Sovereign RDS Control Plane

Terminus Edition 3 large-system task: a sovereign PostgreSQL control plane that mirrors AWS RDS semantics for instance lifecycle, WAL-backed PITR, parameter-group apply fencing, replica promotion, multi-AZ failover leases, and EventBridge-style outbox delivery.

## Layout

- `environment/` — agent-visible control plane (Python + Postgres 16 compose lab)
- `solution/` — reference overlays + `solve.sh`
- `tests/` — separate verifier (34 offline pytest cases)

## Verification (local)

```bash
# NOP: starter code should fail all 30 F2P cases (4 P2P pass)
RDS_HOME=/path/to/environment/rds PYTHONPATH=/path/to/environment/rds \
  pytest tests/test_outputs.py -q

# Oracle: apply overlays then re-run
bash solution/solve.sh
RDS_HOME=/app/rds PYTHONPATH=/app/rds pytest tests/test_outputs.py -q
```

## Complexity

`large_system_strict` gate: ~3k substantive LOC, 28 defects / 7 root causes, 30 F2P + 4 P2P cases.
