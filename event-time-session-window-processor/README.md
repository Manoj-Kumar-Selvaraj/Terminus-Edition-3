# event-time-session-window-processor

A gap close that looks right on a sorted one-tenant file can still mix tenants, treat a too-late straggler as an extend, or rewind the watermark after a bounce. Empty or invalid CLI use must not move the journal. Hardness is that coupling, not file volume.

Keep the Python processor and journal protocol. Sessions are event-time, tenant+user keyed, half-open. Watermark is max observed minus allowed lateness and never steps back; open sessions reload so a later in-gap event extends. `--input` uses the contract tie-break; `--feed` keeps file order. Fail closed to rejects. `--reset-output` may wipe side files, not journal or in-flight sessions. Catalog overlays gap for contracted tenants; the warehouse dump stays untouched; last_run/ops-report refresh from that catalog.

The verifier drives the submitted `run-sessions` CLI on isolated live state. Families: unknown/missing flags leave journal and outputs untouched; empty and zero-event runs do not append watermarks; gap, max duration, and allowed lateness follow `processor.json`; `--input` sort/tie-break versus `--feed` arrival; tenant isolation; restart prefix plus nondecreasing watermark and open-session extend; late-allowed versus TOO_LATE versus rejects; warehouse dump unchanged; catalog-backed ops-report and enterprise versus non-enterprise gap overlay. Presence checks for the CLI and contract exist alongside those live-state cases.

The warehouse click dump is generated at image build from `sessions/tools/generate_seed.py` into `/app/sessions/warehouse`. Reference entrypoint: `solution/solve.sh`.

## Local Harbor

Prefer writing jobs to a Linux filesystem:

```bash
stb harbor run -a oracle -p Terminus-Edition-3/event-time-session-window-processor -o /tmp/e3-jobs
stb harbor run -a nop -p Terminus-Edition-3/event-time-session-window-processor -o /tmp/e3-jobs
```

Oracle reward 1, NOP 0.
