# Session window processor contract

Binding specification for `/app/sessions`. Operators drive the processor only through `/app/sessions/bin/run-sessions`.

## Paths

| Path | Role |
|------|------|
| `/app/sessions/config/processor.json` | `session_gap_ms`, `allowed_lateness_ms`, `max_session_duration_ms` |
| `/app/sessions/data/watermark.journal` | JSONL watermark advances; reload on restart |
| `/app/sessions/data/open_sessions.json` | Crash-consistent snapshot of in-flight sessions |
| `/app/sessions/data/last_run.json` | Operator desk snapshot after a successful run |
| `/app/sessions/data/ops-report.json` | Catalog/ledger reconcile report after a successful run |
| `/app/sessions/output/sessions.jsonl` | Closed session records |
| `/app/sessions/output/late.jsonl` | Too-late side output |
| `/app/sessions/output/rejects.jsonl` | Malformed / fail-closed rejections |
| `/app/sessions/warehouse/click_ledger.jsonl` | Inherited production click dump; do not wipe |

Create parent directories as needed. Outputs are UTF-8 JSONL, no BOM.

## CLI

```
/app/sessions/bin/run-sessions --input <events.jsonl> [--feed <events.jsonl>] [--reset-output]
/app/sessions/bin/run-sessions --empty-check
```

- `--input` processes a batch after the deterministic tie-break: group by `event_time_ms`, then `(tenant_id, user_id, event_id)` ascending.
- `--feed` processes strictly in file order (arrival / processing order). Use this when out-of-order event times must be preserved.
- When both `--input` and `--feed` are omitted and `--empty-check` is set, treat input as empty: leave `sessions.jsonl` and `late.jsonl` empty (create empty files if needed) and do not advance the watermark.
- Omitting `--input`, `--feed`, and `--empty-check` is a usage error: exit status `2` before mutating journal, open-session state, or outputs.
- Unknown flags must be rejected with exit status `2` before mutating journal, open-session state, or outputs.
- `--reset-output` truncates `sessions.jsonl`, `late.jsonl`, and `rejects.jsonl` before the run. It must not clear the watermark journal or open-session state.
- A successful run (including `--empty-check`) requires `/app/sessions/warehouse/catalog.sqlite` and rewrites `last_run.json` and `ops-report.json`.

`last_run.json` is a JSON object and must include integer `warehouse.event_count` equal to `COUNT(*)` of `click_event` in `catalog.sqlite`. `ops-report.json` is a JSON object and must include boolean `catalog.available` (`true` when that catalog loaded) and integer `inventory.event_count` equal to the same `click_event` count.

## Input event schema

Each non-empty input line is a JSON object:

| Field | Type | Required |
|-------|------|----------|
| `event_id` | string, non-empty | yes |
| `tenant_id` | string, non-empty | yes |
| `user_id` | string, non-empty | yes |
| `event_time_ms` | integer, `>= 0` | yes |
| `payload` | string | yes (may be empty) |

Malformed JSON, missing fields, wrong types, empty ids, or negative `event_time_ms` are rejected (not late). Append one object to `rejects.jsonl`:

```json
{"code":"REJECT_MALFORMED","event_id":null,"detail":"<short reason>","line_no":1}
```

Use `event_id` from the object when it is a string; otherwise `null`. Continue with later lines.

## Configuration

Load `/app/sessions/config/processor.json` on every run:

```json
{
  "session_gap_ms": 30000,
  "allowed_lateness_ms": 10000,
  "max_session_duration_ms": 3600000
}
```

All three values are positive integers. Honor the file; changing it between runs must change behavior.

Catalog-backed tenants (those listed in `/app/sessions/warehouse/catalog.sqlite`) overlay `session_gap_ms` from plan: `enterprise` uses `45000`; every other catalog plan keeps the processor.json gap. Tenants that are not in the catalog keep all three knobs from processor.json. `allowed_lateness_ms` and `max_session_duration_ms` always come from processor.json.

## Session identity and intervals

- Session key = `(tenant_id, user_id)`. Do not merge across tenants even when `user_id` matches.
- Sessions are half-open on event time: `[start_ms, end_ms)`.
- An open session tracks `start_ms`, `last_event_time_ms`, and accepted `event_id` values in acceptance order.
- Gap: when an on-time (or late-but-allowed) event arrives for a key with an open session and `event_time_ms >= last_event_time_ms + session_gap_ms`, close the open session first (`end_ms = last_event_time_ms + session_gap_ms`), then open a new session at `event_time_ms`.
- Max duration: if accepting an event would make `event_time_ms - start_ms > max_session_duration_ms`, close at `end_ms = start_ms + max_session_duration_ms`, then open a new session at `event_time_ms` if the event is otherwise acceptable.
- Adjacent sessions that touch at a boundary do not overlap because intervals are half-open.

## Event time vs processing time

Gap, duration, lateness, and watermark decisions use `event_time_ms`. Wall-clock time and arrival index must not drive session membership. Sleep-based windowing is not a session mechanism.

## Watermark

Maintain `max_observed_event_time_ms` over successfully parsed input events, including events later classified as late or late-but-allowed. Rejected malformed lines do not update it.

```
watermark_ms = max_observed_event_time_ms - allowed_lateness_ms
```

If no event has been observed yet, the watermark is undefined and must not be written. After the first valid observation, `watermark_ms` may be negative; consumers treat a negative watermark as `0` for lateness comparisons, but the journal records the raw computed integer.

Advance order for each accepted-for-observation event:

1. Compare the event against the current watermark (state before this event updates `max_observed`).
2. Apply late / late-but-allowed / on-time session logic.
3. Then update `max_observed_event_time_ms` and the watermark.
4. Close any open sessions eligible under the new watermark.

Never advance the watermark before the late/on-time decision for the current event.

## Lateness

Let `W` be the comparison watermark (`max(0, watermark_ms)` when defined). If undefined, every valid event is on-time.

- If `event_time_ms < W`:
  - Late-but-allowed: an open session exists for `(tenant_id, user_id)` and `event_time_ms >= start_ms` and `event_time_ms < last_event_time_ms + session_gap_ms`. Append the event (update `last_event_time_ms` only if `event_time_ms` is greater; always append `event_id`).
  - Too late: otherwise append to `late.jsonl`:

```json
{
  "event_id": "...",
  "tenant_id": "...",
  "user_id": "...",
  "event_time_ms": 0,
  "watermark_ms": 0,
  "reason": "TOO_LATE"
}
```

`watermark_ms` is the comparison watermark `W` used for the decision.

- If `event_time_ms >= W`: on-time — apply gap/duration session assignment.

## Watermark-triggered closes

After updating the watermark to `W`, close every open session where `last_event_time_ms + session_gap_ms <= W`. Set `end_ms = last_event_time_ms + session_gap_ms`.

## Closed session record

One line per closed session in `sessions.jsonl`:

```json
{
  "tenant_id": "...",
  "user_id": "...",
  "start_ms": 0,
  "end_ms": 0,
  "event_ids": ["..."],
  "event_count": 1
}
```

`event_count` must equal `len(event_ids)`. With a positive gap, `end_ms > start_ms`. Do not emit duplicate closes for the same session identity and interval.

## Journal and restart

Each successfully parsed observation appends one journal line, including when `watermark_ms` is unchanged because `max_observed_event_time_ms` did not increase:

```json
{"watermark_ms": 0, "max_observed_event_time_ms": 0, "seq": 1}
```

`seq` starts at 1 and increases by 1 per append. Across restarts, newly appended `watermark_ms` values must be non-decreasing relative to the last journaled `watermark_ms`. Reload restores `max_observed_event_time_ms`, last watermark, next `seq`, and open sessions from `/app/sessions/data/open_sessions.json`.

Open-session snapshot:

```json
{
  "max_observed_event_time_ms": null,
  "sessions": [
    {
      "tenant_id": "...",
      "user_id": "...",
      "start_ms": 0,
      "last_event_time_ms": 0,
      "event_ids": ["..."]
    }
  ]
}
```

Write journal and snapshot crash-consistently (temp file in the same directory, then atomic replace for the snapshot; journal appends whole JSON lines).

## Idempotent re-run

Given the same starting journal/open state and the same input, a second run with `--reset-output` from a clean baseline must produce byte-identical `sessions.jsonl` and `late.jsonl` (SHA-256 of file bytes).

## Empty input

`--empty-check` or a zero-event input creates empty session and late outputs and does not append to the watermark journal.

## Forbidden

- Rewriting this contract to excuse incorrect processor behavior.
- Replacing the Python processor with another language runtime for core session logic.
- Deleting or ignoring the watermark journal protocol.
- Using wall-clock sleep to determine session boundaries.
