# SYSTEM_ARCHITECTURE — hydrograph-stage-forecast-desk

```text
STATUS: ARCHITECTURE_READY
CONTROL_PLANE_COMMIT: 72c0df6ee13f275bfa7d9573bb90e6d5711123d7
CREATION_PROFILE: large_system_strict
CATEGORY/SUBCATEGORY: Science / Earth
LANGUAGES: python, sql
NETWORK_MODE: public
TASK_SLUG: hydrograph-stage-forecast-desk
WORKDIR: /app/hydro
```

This is the **clean inherited hydro stage-forecast desk**. No defects, incomplete behaviors, starter gaps, Oracle, or tests are decided here.

The work package is an operational hydrology desk: gage observations convert through rating-curve segments into stage/flow series, QC holds gate export, civil-time windows drive forecast horizons, and publish artifacts agree after restart. It is not a generic KV store, not event-time session windows, not yard occupancy, and not a textbook hydraulics solver dump.

---

## COMPONENT_GRAPH

Solver-visible runtime lives under `/app/hydro`. Image-build seed is an operator tool, not the production decision path.

| Package | Responsibility |
| --- | --- |
| `hydroctl` (`cli/`) | Operator CLI. Parse/validate args, fail usage errors before any journal or output write, dispatch one command, print documented JSON. |
| `hydro.journal` | Append-only event log with monotonic `seq`, durable `event_id` idempotency, and `EVENT_CONFLICT` when the same id arrives with a different payload. |
| `hydro.replay` | Restart: apply only journal events with `seq > max(applied_seq, checkpoint.last_applied_seq)`. Must not invent or drop open QC holds or accepted observations. |
| `hydro.sites` | Site catalog: `site_id`, datum, timezone (IANA), active curve_id, status. |
| `hydro.timeutil` | Instant storage in UTC with trailing `Z`. Observation windows, forecast horizons, and QC “as-of” convert through each site’s IANA zone including DST. |
| `hydro.observations` | Ingest and normalize stage/flow observations: units, precision, duplicate `(site_id, observed_at, parameter)` rejection, open vs superseded. |
| `hydro.rating` | Rating-curve segments: stage bounds, coeffs, interpolation/extrapolation policy, effective date ranges. Stage→discharge (and reverse when contracted). |
| `hydro.qc` | QC flags and hold codes. Holds block forecast publish and export for the affected site/parameter until released. |
| `hydro.series` | Build ordered stage/flow series from accepted observations + rating lookup; whole-minute alignment where the contract requires it. |
| `hydro.forecast` | Horizon windows relative to as-of in site local time; produce forecast package rows from the live series and site config lead times. |
| `hydro.publish` | Write series, forecast package, rejects, and health. Never mix `warehouse/prior_season.sqlite` into live artifacts. |
| `hydro.policy` | Load `/app/hydro/config/hydro.json` and site/curve tables. Changing `default_tz`, grace, or horizon minutes must change behavior. |
| `sql/` | Physical schema, check constraints, series/hold views used at publish/health. |
| `cmd/seed` | Deterministic image-build materializer of multi-site observation history. Not counted as production decision logic. |

Coupling that must stay in the architecture:

```text
site TZ + observation instant
  -> QC accept / hold
  -> rating-curve segment selection (stage + effective dates)
  -> stage/flow series row
  -> forecast horizon (local civil as-of + lead minutes)
  -> publish series + forecast + health
  -> journal/checkpoint restart preserves accepted observations and active holds
```

A wrong timezone, curve segment, or hold class corrupts peaks **and** forecast packages. Partial completion of one box without the next is an A3 concern later.

---

## ENTRYPOINTS

| Surface | Path / name |
| --- | --- |
| Operator CLI | `/app/hydro/bin/hydroctl` |
| Image-build seed | `/app/hydro/bin/seed` |
| Workdir | `/app/hydro` |
| Config | `/app/hydro/config/hydro.json` |
| Binding contract | `/app/hydro/docs/hydro-contract.md` |
| Layout | `/app/hydro/docs/layout.md` |
| Schema | `/app/hydro/sql/schema.sql` |
| Env | `HYDRO_ROOT` default `/app/hydro` |

CLI verbs (public, stable). Usage/parse failures exit `2` and must not create, truncate, or append journal, sqlite, checkpoint, or `/app/hydro/out/*`.

| Verb | Mutates | Result |
| --- | --- | --- |
| `ingest-obs` | yes | accept observation or reject |
| `apply-rating` | yes | materialize/refresh series rows for a site window or reject |
| `hold` / `release-hold` | yes | QC hold register |
| `forecast-run` | yes (publish) | write forecast package or reject when held |
| `series-publish` | no (publish only) | `/app/hydro/out/series.jsonl` |
| `health` | no | `/app/hydro/out/health.json` |
| `replay` | derived state only | rebuild sqlite from checkpoint + journal |

Every mutating verb requires `--event-id`. Identical id + payload is a stored replay. Same id + different payload is `EVENT_CONFLICT` and leaves state unchanged.

On process start of any mutating verb, if sqlite `applied_seq` lags the journal, run replay catch-up before the new event.

---

## STATE_MODEL

### Source of truth

- `/app/hydro/var/events.jsonl` — accepted events (source of truth).
- `/app/hydro/var/hydro.sqlite` — derived operating state.
- `/app/hydro/var/checkpoint.json` — `last_applied_seq`, sorted active hold keys, series digest.
- `/app/hydro/warehouse/prior_season.sqlite` — prior season dump. Immutable for the agent work package. Live publish must not mix those rows.

### Core entities

| Entity | Keys / notes |
| --- | --- |
| sites | `site_id`, `tz`, `datum`, `curve_id`, `status` |
| rating_curves | `curve_id`, version, effective_start/end |
| rating_segments | `curve_id`, `seg_ord`, stage_min/max inclusive bounds, coeffs, method |
| observations | `obs_id`, `site_id`, `parameter` (`STAGE`\|`FLOW`), `observed_at` UTC Z, `value`, `unit`, `status` |
| series_points | derived `(site_id, parameter, at)` with `value`, `source_obs_id`, `curve_id`, `seg_ord` |
| holds | `(site_id, hold_code, placed_at)` active flag; codes `QC_SPIKE`, `QC_MISSING`, `RATING_OUTAGE`, `MANUAL` |
| forecasts | `(site_id, issued_at, horizon_end)` rows with parameter series |
| event_log | `event_id`, `seq`, verb, body |
| applied | singleton `last_applied_seq` |

### Rating semantics (clean)

- Select the curve effective at `observed_at`.
- Select the segment whose stage interval contains the stage (inclusive lower, exclusive upper except the last segment which is inclusive upper).
- Out-of-range stage → reject `RATING_RANGE` (no silent extrapolation unless config `allow_extrapolate` is true **and** the contract allows it — default false).
- FLOW observations may reverse through the curve only when the contract says reverse is defined for that method; otherwise reject `RATING_REVERSE`.

### Time semantics (clean)

- Store all instants as UTC Z.
- Convert to `site.tz` (fallback `hydro.json` `default_tz`) for horizon math and “same local day” QC windows.
- `grace_early_minutes` / `grace_late_minutes` apply only where the contract defines observation acceptance windows relative to expected slots (if sites use scheduled slots); otherwise grace applies to forecast as-of skew checks in config.

### Holds (clean)

- All four hold codes block `forecast-run` and any export that would include the held site’s live series in the forecast package.
- `release-hold` clears active; releasing an inactive code is `HOLD_MISSING`.
- Duplicate active `(site_id, hold_code)` is `HOLD_ACTIVE`.

### Journal / restart (clean)

- Accepted mutating commands append one complete journal line, then commit sqlite, then refresh checkpoint.
- Usage errors exit 2 with no journal/sqlite/checkpoint/out mutation (including no create of rejects).
- Parsed rejects append one object to `/app/hydro/out/rejects.jsonl`.
- Kill mid-command: either the journal line is absent (no state change after replay) or the line is complete and sqlite may catch up.

---

## SOLVER_VISIBLE_DOC_PLAN

| Doc | Role |
| --- | --- |
| `/app/hydro/docs/hydro-contract.md` | Binding CLI, rating, QC, time, journal, publish schemas |
| `/app/hydro/docs/layout.md` | Path map under `/app/hydro` |
| `/app/hydro/ops/handoff.txt` | Shift handoff counts (when instruction asserts current state) |
| `/app/hydro/logs/desk.log` | Desk log excerpt (when instruction asserts current state) |
| `/app/hydro/config/hydro.json` | default_tz, grace, horizons, path map, extrapolate flag |
| `/app/hydro/sql/schema.sql` | Physical model |

Docs define requirements/schemas/protocols. They must not become a repair walkthrough or second prompt.

---

## PRODUCTION_CHARACTERISTICS

- Differentiated modules with distinct responsibilities (ingest, rating, QC, series, forecast, journal, publish).
- Real operator entrypoint `hydroctl` reaching all mutating paths.
- Persistent journal + derived sqlite + checkpoint fencing.
- Validation and typed reject codes.
- Config-driven horizons/TZ/grace.
- Restart/idempotency/conflict semantics.
- Warehouse isolation as an operational boundary.
- Domain coupling: time × rating × holds × forecast publish.

---

## SCALE_FIT

| Axis | Plan |
| --- | --- |
| Substantive LOC | Natural package set supports ≥3000 reachable runtime LOC (seed excluded from decision logic). |
| Primary records | 12,000–16,000 observations across ≥8 sites, ≥14 days spanning a US DST transition, multiple parameters. |
| Curves | ≥12 curve versions / ≥40 segments with varied bounds. |
| Open holds | Small active set for realism (~tens), not thousands of identical flags. |
| Organic F2P surface | ingest accept/reject, rating range, segment selection, reverse policy, DST/TZ, hold block/release, forecast horizon, event_id replay/conflict, usage no-touch, catch-up, warehouse isolation, health digest, config mutation — comfortably 25–30 without filler. |

---

## RESOURCE_GRAPH

```text
hydroctl
  -> policy (hydro.json)
  -> journal / replay / store
  -> observations / rating / qc / series / forecast
  -> publish (out/*)
warehouse/prior_season.sqlite (read-only isolation)
```

Artifacts (agent-visible outputs; A7 must name every verifier-consumed path):

| Path | Content |
| --- | --- |
| `/app/hydro/out/series.jsonl` | Live series points, sorted |
| `/app/hydro/out/forecast.jsonl` | Forecast package rows, sorted |
| `/app/hydro/out/rejects.jsonl` | Parsed rejects |
| `/app/hydro/out/health.json` | ok, seqs, digest, warehouse_untouched |
| `/app/hydro/var/events.jsonl` | Journal |
| `/app/hydro/var/hydro.sqlite` | Derived state |
| `/app/hydro/var/checkpoint.json` | Fence + digest |

`task.toml` should transfer `/app/hydro` (or the named out+var set) under `environment_mode=separate`.

---

## DATA_VOLUME_PLAN

- Horizon: 2026-03-01 .. 2026-03-15 (includes US spring-forward 2026-03-08) plus enough history for rating effective ranges.
- Sites: 8–12 gages, mixed `America/Chicago`, `America/Denver`, `America/New_York`.
- Observations: ~12,600 STAGE primary rows; subset FLOW where reverse is defined.
- Warehouse: ~3,000–4,000 prior-season rows including some open-looking statuses to tempt naive publish mixes.
- Deterministic seed integer in `hydro.json`.

---

## PUBLISH SCHEMAS (clean contract sketch)

Exact field order belongs in `hydro-contract.md`. Architecture requires:

**series.jsonl** — one object per live series point: `site_id`, `parameter`, `at`, `value`, `unit`, `curve_id`, `seg_ord`, `source_obs_id`. Sorted by `site_id`, `parameter`, `at`.

**forecast.jsonl** — `site_id`, `issued_at`, `horizon_end`, `parameter`, `points` (array of `{at,value}`) or flattened rows per contract — pick one representation in the contract and keep it. Sorted by `site_id`, `issued_at`.

**rejects.jsonl** — `code`, `event_id`, `detail`.

**health.json** — `ok`, `applied_seq`, `journal_seq`, `series_digest`, `active_hold_keys` (sorted), `warehouse_untouched`. `ok` true only when seqs match, digest matches journal-derived series, and warehouse was not mixed.

Series digest: lowercase hex SHA-256 of sorted `site_id|parameter|at=value` lines, newline-terminated UTF-8.

---

## UNRESOLVED_RISKS

1. **Rating reverse** — keep reverse narrowly defined for one method only so instruction stays ≤20 bullets.
2. **Scheduled observation slots** — optional; if included, grace applies to slots; if omitted, grace applies only to forecast as-of skew. Decide in A3/docs so Q3 does not invent both.
3. **Artifact copy** — verifier needs live `/app/hydro` tree after agent work; declare `artifacts = ["/app/hydro"]`.
4. **Anti-textbook** — formulas stay in the contract as operational rules, not multi-page hydraulics essays.
5. **Novelty** — stay clear of event-time session processor topology (this is rating+QC+forecast desk, not session gaps).

```text
SCALE_FIT: PASS
ARCHITECTURE_READY -> DEFECT_TOPOLOGY
```
