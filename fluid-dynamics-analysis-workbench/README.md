# fluid-dynamics-analysis-workbench

Edition 3 physics task: repair an inherited Python fluid-dynamics analysis workbench under `/app/fluidlab` and publish deterministic fleet reports for mixed liquid and ideal-gas operating cases.

## Layout

- `instruction.md` — solver-facing contract
- `environment/` — agent image and solver-visible workbench
- `solution/` — reference repair (`solve.sh` + `fixed/`)
- `tests/` — separate verifier image, pytest checks, golden fixtures

## Local gates

```bash
stb harbor run -a oracle -p Terminus-Edition-3/fluid-dynamics-analysis-workbench -o /tmp/e3-fluid-jobs
stb harbor run -a nop    -p Terminus-Edition-3/fluid-dynamics-analysis-workbench -o /tmp/e3-fluid-jobs
```

Docker simulation (no Harbor): build `environment/Dockerfile` as `fluidlab-agent`, mount `solution/` and `tests/`, run `solution/solve.sh` then `tests/test.sh`.

Expected: oracle reward **1.0**, NOP reward **0.0**.
