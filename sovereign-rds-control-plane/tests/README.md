# Verifier

Separate verifier image runs `test.sh` → pytest on `test_outputs.py` against the transferred `/app/rds` artifact tree. Reward is binary `0`/`1` under `/logs/verifier/reward.txt`. Tests are offline behavioral checks of control-plane modules (no live AWS).
