# Solution

`solve.sh` copies corrected modules from `overlays/rds/` onto `/app/rds/rds/`, then runs `publish_outputs.py` to emit deterministic readiness artifacts under `/app/rds/out` (Postgres when reachable; otherwise offline fixtures).
