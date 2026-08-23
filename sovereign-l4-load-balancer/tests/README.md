# Verifier

Separate verifier image (`tests/Dockerfile`) extends the agent image so Go/C++ binaries execute under the same glibc baseline.

`test.sh` runs `tests/test_outputs.py` and writes `/logs/verifier/reward.txt`.

Empirical evidence (Docker):

- **Starter/NOP:** 3 F2P failures / 13 P2P passes (16 total)
- **Oracle:** 16/16 passes after `/solution/solve.sh`

Remaining authoring gate: expand to 25–30 F2P behavioral cases mapped in `.terminus/designs/sovereign-l4-load-balancer-test-map.json` per `large_system_strict` complexity policy.
