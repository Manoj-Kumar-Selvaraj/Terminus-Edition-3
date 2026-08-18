# yard-gate-dock-dwell-control

A DC yard desk can accept a gate-in that looks fine on UTC stamps and still miss the Chicago window, double-book a spot while a jockey move is in flight, or publish prior-cycle warehouse rows as live occupancy. Hardness is that coupling, not file volume.

Keep the Python/SQL plane and `/app/yard/bin/yardctl`. Appointments convert to `America/Chicago` with grace and DST. Open visits are `(scac, trailer)`. DROP_IN stays off the apron. Grounded dry/reefer/container units need a mounted chassis before `IN_TRANSIT`. Dispatch vacates origin and reserves dest. All holds block gate-out; only yard holds pause detention. The journal is source of truth; sqlite catches up past the checkpoint fence. Usage errors exit 2 without touching journal, sqlite, checkpoint, or `out/`.

The verifier drives `yardctl` on the inherited live yard. Families: usage fence; window/grace/DST/clock_start; exclusive occupancy and dest reservation; door/chassis fit; hold block vs pause class; event_id replay/conflict; identity/pool/contract; warehouse-isolated snapshot/detention/health; sqlite lag catch-up. Presence checks cover the CLI, contract, and seed scale.

`/app/yard/warehouse/prior_cycle.sqlite` is a prior cycle generated at image build. Reference entrypoint: `solution/solve.sh`.

## Local Harbor

Prefer writing jobs to a Linux filesystem:

```bash
stb harbor run -a oracle -p Terminus-Edition-3/yard-gate-dock-dwell-control -o /tmp/e3-jobs
stb harbor run -a nop -p Terminus-Edition-3/yard-gate-dock-dwell-control -o /tmp/e3-jobs
```

Oracle reward 1, NOP 0.
