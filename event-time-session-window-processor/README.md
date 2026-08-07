# event-time-session-window-processor

Terminus Edition 3 task: repair a broken event-time session window processor (watermarks, lateness, restart journal).

## Layout

- `environment/sessions/` — agent-visible processor, contract, fixtures, operator CLI
- `solution/` — oracle patch + `solve.sh`
- `tests/` — separate verifier image; semantic live-state checks only

## Local Harbor

Jobs on `/mnt/d` can hit verifier mount path issues under WSL; prefer writing jobs to a Linux filesystem:

```bash
stb harbor run -a oracle -p Terminus-Edition-3/event-time-session-window-processor -o /tmp/e3-jobs
stb harbor run -a nop -p Terminus-Edition-3/event-time-session-window-processor -o /tmp/e3-jobs
```

Expect oracle reward `1` and NOP reward `0`.
