# event-time-session-window-processor

Repair the inherited Python event-time sessionizer so tenant-keyed sessions, watermarks, lateness, gap/duration closes, and journal restart agree with `/app/sessions/docs/session-contract.md`.

## Layout

- `environment/sessions/` — processor, contract, fixtures, warehouse catalog, operator CLI
- `solution/` — oracle copies of the defective modules plus `solve.sh`
- `tests/` — separate verifier image; semantic live-state checks only

The warehouse click dump is generated at image build from `sessions/tools/generate_seed.py` into `/app/sessions/warehouse`.

## Local Harbor

Prefer writing jobs to a Linux filesystem:

```bash
stb harbor run -a oracle -p Terminus-Edition-3/event-time-session-window-processor -o /tmp/e3-jobs
stb harbor run -a nop -p Terminus-Edition-3/event-time-session-window-processor -o /tmp/e3-jobs
```

Expect oracle reward `1` and NOP reward `0`.
