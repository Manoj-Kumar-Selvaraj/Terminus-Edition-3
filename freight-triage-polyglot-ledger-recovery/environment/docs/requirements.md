# Freight ledger — schema and protocol

Binding constants, artifact schemas and reconciliation rules for the warehouse
freight triage stack. Where an implementation disagrees with this document on
those details, the implementation is wrong. Delivery goals are in the task
prompt (`instruction.md`).

## 1. Shared constants

| Name | Value |
| --- | --- |
| `epoch_base_s` | `1577836800` (1970-01-01 based unix seconds for 2020-01-01T00:00:00Z) |
| `window_seconds` | `21600` (six hour dock windows) |

All three services must agree on both values and must publish them in their
artifacts.

### 1.1 Timestamps

Wire timestamps are ISO-8601 with an explicit numeric UTC offset, for example
`2026-03-14T08:30:00-05:00` or `2026-03-14T14:15:00+05:45`. The offset is part
of the value and must be applied:

```
arrival_epoch_s = unix_seconds(instant) - epoch_base_s
```

A timestamp is never to be read as if it were already UTC.

### 1.2 Windows

```
window_index       = floor(arrival_epoch_s / window_seconds)
window_start_epoch = window_index * window_seconds          (inclusive)
window_end_epoch   = window_start_epoch + window_seconds    (exclusive)
```

Window membership is half open: `window_start <= arrival_epoch_s < window_end`.

### 1.3 Mass

All mass is integer kilograms. Tonnage strings are exact, never rounded:

```
gross_tonnes = "<kg / 1000>.<kg % 1000 zero padded to three digits>"
```

### 1.4 Seals

A seal is normalized by trimming ASCII whitespace and upper-casing ASCII
letters. `seal_digest` is CRC-32/ISO-HDLC over the UTF-8 bytes of the
*normalized* seal (reflected, polynomial `0xEDB88320`, init `0xFFFFFFFF`, final
xor `0xFFFFFFFF`), rendered as eight lowercase hex digits in natural byte order.

### 1.5 Digests

Every `*_digest` field is lowercase hex SHA-256 (FIPS 180-4) over the UTF-8
bytes of the canonical record stream described for that artifact. Canonical
records are joined with no separator; each record already ends in `\n`.

## 2. Normative registries

`/app/environment/data/registry/` is authoritative:

* `lanes.json` - `lane_id`, `slot_count`, `slot_capacity_kg`, hubs, service class
* `carriers.json` - `carrier_code` and carrier attributes
* `commodities.json` - `commodity_code` and its `group_code`
* `tariff.json` - `bands` and per `group_code` `rate_cents`

The compiled tables under `native/src/tables`, `intake/src/com/freight/tables`
and `reconcile/internal/tablex` are an offline mirror of the same data. They are
not permitted to drift from each other.

## 3. Native ledger engine - `ledger-snapshot.json`

`freightctl ledger --root <root>` reads every `*.json` under
`<root>/environment/data/manifests` in ascending filename order and writes
`<root>/output/ledger-snapshot.json`.

### 3.1 Per manifest derivation

* `gross_kg` - sum of `pieces[].gross_mass_kg`; `0` when there are no pieces
* `piece_count` - number of pieces
* `hazmat_max` - largest `pieces[].hazmat_class`, `0` when there are no pieces
* `average_piece_g` - `gross_kg * 1000 / piece_count` floored; `0` when there
  are no pieces
* `seal` - normalized seal (section 1.4)
* `seal_digest` - CRC-32 of the normalized seal
* `arrival_epoch_s`, `window_index` - section 1.1 and 1.2

A manifest with an empty `pieces` array is a valid manifest. It is carried
through the whole pipeline with `gross_kg = 0` and is eligible for allocation.

### 3.2 Status

Status is resolved in this order; the first match wins:

1. `invalid_arrival` - the arrival timestamp cannot be parsed
2. `invalid_lane` - `lane_id` is not in the lane registry
3. `invalid_carrier` - `carrier_code` is not in the carrier registry
4. `invalid_commodity` - `commodity_code` is not in the commodity registry
5. `duplicate_seal` - see 3.3
6. `accepted` or `overflow` - decided by allocation, see 3.4

### 3.3 Duplicate seals

Group every manifest that survived checks 1 to 4 by **normalized** seal, so
seal comparison is case insensitive. Within a group, order by
`(lane_id, arrival_epoch_s, manifest_id)` ascending. The first manifest keeps
the seal; every later manifest gets status `duplicate_seal`, is excluded from
allocation and gets `slot_index = 0`.

### 3.4 Slot allocation

Allocation is per `(lane_id, window_index)` bucket over the manifests that
survived 3.2 and 3.3.

* Order within the bucket: `priority` **descending**, then `arrival_epoch_s`
  ascending, then `manifest_id` ascending.
* The lane provides `slot_count` slots numbered **1 .. slot_count**. Each slot
  starts with `slot_capacity_kg` kilograms of remaining capacity.
* A manifest is placed in the lowest numbered slot whose remaining capacity is
  greater than or equal to its `gross_kg`; that slot's remaining capacity is
  then reduced by `gross_kg` and the status becomes `accepted`.
* Capacity accounting is exact in kilograms. Truncating to whole tonnes is not
  permitted.
* If no slot fits, the status becomes `overflow` and `slot_index = 0`.

`slot_index` is one based. `0` means "not allocated".

### 3.5 Tariff band

The band table is half open on the lower edge:

```
band applies when min_kg <= gross_kg < max_kg      (max_kg < 0 means unbounded)
```

`tariff_rate_cents` is the rate for `(commodity.group_code, band)`. A manifest
with an unknown commodity has `tariff_band = "NA"` and `tariff_rate_cents = 0`.

### 3.6 Document

Entries are ordered by `(lane_id, arrival_epoch_s, manifest_id)` ascending.

Each entry object carries exactly: `arrival_epoch_s`, `average_piece_g`,
`carrier_code`, `commodity_code`, `gross_kg`, `gross_tonnes`, `hazmat_max`,
`lane_id`, `manifest_id`, `piece_count`, `priority`, `seal`, `seal_digest`,
`slot_index`, `status`, `tariff_band`, `tariff_rate_cents`, `window_index`.

`lane_totals` is ordered by `lane_id` and carries `accepted_count`,
`allocated_kg`, `allocated_tonnes`, `duplicate_seal_count`, `entry_count`,
`invalid_count`, `lane_id`, `overflow_count`, `slots_used`. `allocated_kg`
counts `accepted` entries only. `slots_used` is the number of distinct non-zero
slot indices used on that lane.

`totals` carries `accepted_count`, `accepted_kg`, `accepted_tonnes`,
`duplicate_seal_count`, `gross_kg`, `gross_tonnes`, `invalid_count`,
`manifest_count`, `overflow_count`. `manifest_count` equals the number of
manifest files on disk.

Canonical ledger record, one per entry in document order:

```
manifest_id|lane_id|window_index|slot_index|arrival_epoch_s|gross_kg|status|seal_digest|tariff_band|tariff_rate_cents\n
```

`ledger_digest` is the SHA-256 of that stream.

## 4. Intake service - `intake-journal.json`

The Java service exposes `POST /v2/holds`, `POST /v2/releases`,
`POST /v2/notes`, `GET /v2/journal` and `GET /v2/healthz` on loopback.
`IntakeMain replay` starts the service, posts
`<root>/environment/data/intake-events.ndjson` through the HTTP API and writes
`<root>/output/intake-journal.json`.

### 4.1 Ordering

The event file is deliberately not in sequence order. Intake applies events in
ascending `seq` order regardless of `kind`; a release can only succeed after the
hold it references has been applied.

### 4.2 Semantics

* `hold_place`
  * empty `manifest_id` -> rejected, code `HOLD_MISSING_MANIFEST`, `ref = 0`
  * `tonnes_kg <= 0` -> rejected, code `HOLD_INVALID_TONNES`, `ref = 0`
  * otherwise accepted, code `HOLD_PLACED`, `ref = seq`; the manifest's
    `held_kg` increases by `tonnes_kg` **once** and `open_holds` increases by 1
* `hold_release`
  * unknown `hold_ref` -> rejected, code `RELEASE_UNKNOWN_REF`
  * already released -> rejected, code `RELEASE_ALREADY_CLOSED`
  * otherwise accepted, code `RELEASE_APPLIED`; `released_kg` increases by the
    referenced hold's tonnage and `open_holds` decreases by 1
* `manifest_note` -> always accepted, code `NOTE_RECORDED`, `ref = 0`, no
  tonnage effect

A release row echoes the requested `hold_ref` in `ref` whether it was accepted
or rejected. `tonnes_kg` is echoed from the request on `hold_place` rows,
including rejected ones, and is `0` on releases and notes.

`at_epoch_s` is derived per section 1.1 from `at_local`, offset included.

### 4.3 Document

`events` is ordered by `seq` ascending and each event carries `accepted`,
`at_epoch_s`, `code`, `kind`, `manifest_id`, `ref`, `seq`, `tonnes_kg`.

`holds` contains one row per manifest that received at least one accepted
`hold_place`, **ordered by `manifest_id` ascending**. Each row carries
`first_hold_epoch_s`, `held_kg`, `held_tonnes`, `last_event_epoch_s`,
`manifest_id`, `net_held_kg`, `net_held_tonnes`, `open_holds`, `released_kg`,
`seal` and `seal_digest`. The manifest identifier field is named
`manifest_id`; the `manifest_ref` spelling used by freight-intake/1 was retired.
`net_held_kg = held_kg - released_kg`. `seal` is the normalized seal of the
first accepted hold and `seal_digest` follows section 1.4, so it must equal the
`seal_digest` the native engine publishes for the same manifest.
`first_hold_epoch_s` is the earliest accepted `hold_place` for the manifest.
`last_event_epoch_s` is the latest `at_epoch_s` among that manifest's accepted
holds and releases plus any `manifest_note` recorded after its first accepted
hold. Rejected events never move either value and never create a row.

`totals` carries `accepted`, `events`, `held_kg`, `net_held_kg`, `open_holds`,
`rejected`, `released_kg`.

Canonical journal record, one per event in `seq` order:

```
seq|kind|manifest_id|at_epoch_s|accepted|code|ref|tonnes_kg\n
```

`accepted` is rendered as `1` or `0`. `journal_digest` is the SHA-256 of that
stream.

## 5. Reconciler - `audit-report.json` and `audit-ledger.csv`

`reconcile run --root <root>` reads the snapshot, the journal and the lane
registry.

### 5.1 Per manifest

`net_held_kg` comes from the journal hold row with the same `manifest_id`, or
`0` when there is none.

```
available_kg = max(0, gross_kg - net_held_kg)   when status == "accepted"
available_kg = 0                                otherwise
accrued_cents = round_half_up(tariff_rate_cents * available_kg / 1000)
              = (tariff_rate_cents * available_kg + 500) / 1000   (integer)
```

`state`:

| condition | state |
| --- | --- |
| `status != "accepted"` and `net_held_kg > 0` | `unreconciled` |
| `status != "accepted"` | `excluded` |
| `net_held_kg == 0` | `clear` |
| `net_held_kg > gross_kg` | `over_held` |
| otherwise | `held` |

### 5.2 `audit-ledger.csv`

UTF-8, LF line endings, one header row, rows ordered by
`(lane_id, window_index, slot_index, manifest_id)` ascending. Columns in exactly
this order:

```
manifest_id,lane_id,window_index,slot_index,status,state,gross_kg,net_held_kg,available_kg,gross_tonnes,seal_digest,tariff_band,tariff_rate_cents,accrued_cents
```

### 5.3 `audit-report.json`

* `csv_digest` - SHA-256 of the bytes written to `audit-ledger.csv`
* `digests_match` - `{"journal": bool, "ledger": bool}`
* `epoch_base_s` - section 1
* `journal_digest` / `ledger_digest` - copied from the inputs
* `recomputed_journal_digest` / `recomputed_ledger_digest` - recomputed locally
  from the input documents using sections 3.6 and 4.3; both must equal the
  copied values
* `lane_rollups` - ordered by `lane_id`, carrying `accepted_count`,
  `accrued_cents`, `allocated_kg`, `allocated_tonnes`, `available_kg`,
  `entry_count`, `held_kg`, `lane_id`, `slot_capacity_kg`, `slot_count`,
  `slots_used`. `allocated_kg` counts `accepted` rows only. `slots_used` counts
  distinct non-zero one based slot indices among accepted rows. A rollup
  publishes lane geometry taken from the lane registry, so only registered
  lanes get one; rows on an unregistered lane still appear in the CSV and in
  `totals`.
* `window_rollups` - ordered by `window_index`, carrying `accepted_count`,
  `entry_count`, `gross_kg`, `held_kg`, `window_end_epoch_s`, `window_index`,
  `window_start_epoch_s`. Membership is half open (section 1.2), so every
  manifest lands in exactly one window.
* `orphan_holds` - journal holds with no ledger entry, ordered by `manifest_id`,
  carrying `manifest_id`, `net_held_kg`, `open_holds`
* `seal_digest_mismatches` - number of manifests present in both documents whose
  `seal_digest` values disagree. A healthy stack reports `0`.
* `state_counts` - all five states, zero valued when unused
* `totals` - `accepted`, `accrued_cents`, `available_kg`, `held_kg`,
  `manifests`, `orphan_held_kg`, `orphan_hold_count`
* `report_digest` - SHA-256 over one canonical line per CSV row in CSV order:

```
manifest_id|lane_id|window_index|slot_index|state|gross_kg|net_held_kg|available_kg|accrued_cents\n
```

## 6. Cross language conformance - `selftest-*.json`

Each service exposes a `selftest` subcommand that runs a fixed probe corpus
through the shared algorithm families (`codec`, `format`, `hash`, `norm`,
`rules`, `stats`, `tables`) and writes a report with a `families` map of
`family -> algorithm -> 16 hex digit fold` plus a `digest` over

```
family|algorithm|value\n
```

sorted by family then algorithm. The `families` maps and the `digest` produced
by C++, Java and Go must be identical. A differing entry names the exact
algorithm that has drifted.

## 7. Suite runner

`run-freight-suite [--root DIR] [--skip-build]` builds all three services and
runs the pipeline, then writes `<root>/output/suite-manifest.json` listing
`bytes`, `name` and `sha256` for each of `audit-ledger.csv`,
`audit-report.json`, `intake-journal.json`, `ledger-snapshot.json`,
`selftest-cpp.json`, `selftest-go.json`, `selftest-java.json`.

## 8. Determinism

Artifacts must be byte identical across runs on the same inputs: UTF-8, LF line
endings, two space indented JSON with object keys in ascending order, no
timestamps, no host names, no run identifiers, no random values and no network
access.
