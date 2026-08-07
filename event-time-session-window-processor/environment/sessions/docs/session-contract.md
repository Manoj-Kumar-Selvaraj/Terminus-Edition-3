# Session window processor contract

Binding specification for `/app/sessions`. Operators drive the processor only through `/app/sessions/bin/run-sessions`.

## Paths

| Path | Role |
|------|------|
| `/app/sessions/config/processor.json` | Runtime knobs: `session_gap_ms`, `allowed_lateness_ms`, `max_session_duration_ms` |
| `/app/sessions/data/watermark.journal` | Append-only style journal of watermark advances (JSONL); must reload on restart |
| `/app/sessions/data/open_sessions.json` | Crash-consistent snapshot of in-flight sessions |
| `/app/sessions/output/sessions.jsonl` | Closed session records |
| `/app/sessions/output/late.jsonl` | Too-late side output |
| `/app/sessions/output/rejects.jsonl` | Malformed / fail-closed rejections |

Creating parent directories as needed is required. Outputs are JSONL (one JSON object per line, UTF-8, no BOM).

## CLI

```
/app/sessions/bin/run-sessions --input <events.jsonl> [--feed <events.jsonl>] [--reset-output]
/app/sessions/bin/run-sessions --empty-check
```

- `--input` processes a batch file in arrival order after applying the deterministic tie-break below within equal `event_time_ms` groups when `--feed` is not used for live arrival simulation.
- `--feed` processes events strictly in file order (arrival / processing order) without reordering across different event times; use this for out-of-order holdouts.
- When both `--input` and `--feed` are omitted and `--empty-check` is set, treat the input as empty: leave `sessions.jsonl` and `late.jsonl` empty (or create empty files) and do **not** advance the watermark.
- Unknown flags must be rejected with exit status `2` **before** mutating journal, open-session state, or outputs.
- `--reset-output` truncates `sessions.jsonl`, `late.jsonl`, and `rejects.jsonl` before the run but must **not** clear the watermark journal or open-session state.

## Input event schema

Each non-empty input line is a JSON object:

| Field | Type | Required |
|-------|------|----------|
| `event_id` | string, non-empty | yes |
| `tenant_id` | string, non-empty | yes |
| `user_id` | string, non-empty | yes |
| `event_time_ms` | integer, `>= 0` | yes |
| `payload` | string | yes (may be empty) |

Malformed JSON, missing fields, wrong types, empty ids, or negative `event_time_ms` are **rejected** (not late): append one object to `rejects.jsonl` with:

```json
{"code":"REJECT_MALFORMED","event_id":null,"detail":"<short reason>","line_no":<int>}
```

Use `event_id` from the object when present and a string; otherwise `null`. Continue processing subsequent lines.

## Configuration

`/app/sessions/config/processor.json` must be loaded on every run:

```json
{
  "session_gap_ms": 30000,
  "allowed_lateness_ms": 10000,
  "max_session_duration_ms": 3600000
}
```

All three values are positive integers. The processor must honor these values from the file (not ignore them in favor of hard-coded constants). Changing the file between runs must change behavior accordingly.

## Session identity and intervals

- Session key = `(tenant_id, user_id)`. Sessions **must not** merge across different `tenant_id` values even when `user_id` matches.
- Sessions are half-open on event time: `[start_ms, end_ms)`.
- While a session is open it tracks `start_ms`, `last_event_time_ms`, and the ordered list of accepted `event_id` values.
- Gap rule: when an on-time (or late-but-allowed) event arrives for a key with an open session and `event_time_ms >= last_event_time_ms + session_gap_ms`, **close** the open session first (end_ms = `last_event_time_ms + session_gap_ms`), then open a new session starting at `event_time_ms`.
- Max duration: if accepting an event would make `event_time_ms - start_ms > max_session_duration_ms`, close the open session at `end_ms = start_ms + max_session_duration_ms` (still half-open semantics for the closed record), then open a new session at `event_time_ms` if the event is otherwise acceptable.
- Adjacent sessions that touch at a boundary do not overlap because intervals are half-open.

## Event time vs processing time

All gap, duration, lateness, and watermark decisions use `event_time_ms` from the event. Wall-clock time and arrival index must not drive session membership. Busy-waiting or `sleep`-based windowing is forbidden as the session mechanism.

## Watermark

Maintain `max_observed_event_time_ms` over all **observed** input events that were successfully parsed (including events later classified as late or late-but-allowed). Rejected malformed lines do not update it.

```
watermark_ms = max_observed_event_time_ms - allowed_lateness_ms
```

If no event has been observed yet, the watermark is undefined and must not be written. After the first valid observation, `watermark_ms` may be negative only if that would follow the formula; consumers treat a negative watermark as `0` for lateness comparisons, but the journal still records the raw computed integer.

**Advance order (required):** for each accepted-for-observation event:

1. Compare the event against the **current** watermark (from state before this event updates `max_observed`).
2. Apply late / late-but-allowed / on-time session logic.
3. Then update `max_observed_event_time_ms` and the watermark.
4. Close any open sessions that are eligible under the new watermark (see below).

Never advance the watermark before the late/on-time decision for the current event.

## Lateness

Let `W` be the current watermark in milliseconds used for comparisons (`max(0, watermark_ms)` when watermark is defined; if undefined, treat as no watermark — all valid events are on-time).

- If `event_time_ms < W`:
  - **Late-but-allowed:** an open session exists for `(tenant_id, user_id)` and `event_time_ms >= start_ms` and the event does not violate the gap close against `last_event_time_ms` in a way that would require starting a brand-new session after a close that the watermark has already finalized. Practically: if an open session exists and `event_time_ms >= start_ms` and `event_time_ms < last_event_time_ms + session_gap_ms`, append the event to that open session (update `last_event_time_ms` only if `event_time_ms` is greater; always append `event_id` in tie-break order of acceptance).
  - **Too late:** otherwise append to `late.jsonl`:

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

All fields above are required. `watermark_ms` is the comparison watermark `W` used for the decision.

- If `event_time_ms >= W`: on-time — apply gap/duration session assignment.

## Watermark-triggered closes

After updating the watermark to `W`:

- Close every open session where `last_event_time_ms + session_gap_ms <= W`.
- Set `end_ms = last_event_time_ms + session_gap_ms` for those closes.

## Closed session record

Exactly one line per closed session in `sessions.jsonl`:

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

`event_count` must equal `len(event_ids)`. `end_ms > start_ms` unless the contract close rules yield equality only when gap is zero (gap is always positive here, so `end_ms > start_ms`). Do not emit duplicate closes for the same session identity and interval.

## Deterministic tie-break

When `--input` batches events, stably group by `event_time_ms` and within each group process in ascending order of `(tenant_id, user_id, event_id)`.

When `--feed` is used, preserve file order exactly (no regrouping).

## Journal and restart

`/app/sessions/data/watermark.journal` is JSONL. Each watermark advance appends:

```json
{"watermark_ms": 0, "max_observed_event_time_ms": 0, "seq": 1}
```

`seq` starts at 1 and increases by 1 per append. Across process restarts, newly appended `watermark_ms` values must be **non-decreasing** relative to the last journaled `watermark_ms`. Reloading must restore `max_observed_event_time_ms`, last watermark, next `seq`, and open sessions from `/app/sessions/data/open_sessions.json`.

Open-session snapshot schema:

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

Writes to the journal and open-session snapshot must be crash-consistent (write temp file in the same directory, then atomic replace). A kill between events must not leave a half-closed session recorded in `sessions.jsonl` without a matching journal/state update, and must not truncate prior journal history.

## Idempotent re-run

Given the same starting journal/open state and the same input file, a second run with `--reset-output` must produce byte-identical `sessions.jsonl` and `late.jsonl` digests relative to the first run's outputs (SHA-256 of file bytes). Without `--reset-output`, re-processing the same events must not append duplicate session closes for sessions already reflected in durable state; prefer relying on restored open state and watermark so already-closed work is not emitted again. For verifier checks, `--reset-output` plus restored journal from a clean baseline is the supported idempotency probe: run once from empty state, capture digests, restore empty outputs but keep regenerating from the same empty journal baseline, digests match.

## Empty input

`--empty-check` or a zero-event input creates empty session and late outputs and does not append to the watermark journal.

## Forbidden

- Rewriting this contract to excuse incorrect processor behavior.
- Replacing the Python processor with another language runtime for the core session logic.
- Deleting or ignoring the watermark journal protocol.
- Using wall-clock `sleep` to determine session boundaries.
