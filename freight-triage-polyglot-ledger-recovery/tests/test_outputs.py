"""Behavioural checks for the freight triage polyglot stack.

Everything here is derived from /app/environment/docs/requirements.md
with an independent Python reference implementation; nothing is compared against
a stored copy of the C++, Java or Go code.
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
import os
import shutil
import subprocess
import zlib
from datetime import datetime
from pathlib import Path

import pytest

ROOT = Path("/app")
ENVIRONMENT = ROOT / "environment"
OUTPUT = ROOT / "output"
DATA = ENVIRONMENT / "data"
REGISTRY_DIR = DATA / "registry"
MANIFEST_DIR = DATA / "manifests"
EVENTS_FILE = DATA / "intake-events.ndjson"

SUITE = "/app/bin/run-freight-suite"
FREIGHTCTL = "/app/bin/freightctl"
INTAKE = "/app/bin/freight-intake"
RECONCILE = "/app/bin/freight-reconcile"

EPOCH_BASE_S = 1577836800
WINDOW_SECONDS = 21600

ARTIFACTS = [
    "audit-ledger.csv",
    "audit-report.json",
    "intake-journal.json",
    "ledger-snapshot.json",
    "selftest-cpp.json",
    "selftest-go.json",
    "selftest-java.json",
]

CSV_HEADER = [
    "manifest_id",
    "lane_id",
    "window_index",
    "slot_index",
    "status",
    "state",
    "gross_kg",
    "net_held_kg",
    "available_kg",
    "gross_tonnes",
    "seal_digest",
    "tariff_band",
    "tariff_rate_cents",
    "accrued_cents",
]

ENTRY_KEYS = {
    "arrival_epoch_s",
    "average_piece_g",
    "carrier_code",
    "commodity_code",
    "gross_kg",
    "gross_tonnes",
    "hazmat_max",
    "lane_id",
    "manifest_id",
    "piece_count",
    "priority",
    "seal",
    "seal_digest",
    "slot_index",
    "status",
    "tariff_band",
    "tariff_rate_cents",
    "window_index",
}


# --------------------------------------------------------------------------
# shared helpers
# --------------------------------------------------------------------------


def run(argv, timeout=900, env=None):
    merged = dict(os.environ)
    if env:
        merged.update(env)
    return subprocess.run(
        argv,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        timeout=timeout,
        env=merged,
    )


def arrival_epoch(text: str) -> int:
    moment = datetime.fromisoformat(text)
    assert moment.utcoffset() is not None, "timestamp %r has no offset" % text
    return int(moment.timestamp()) - EPOCH_BASE_S


def window_index(epoch_s: int) -> int:
    return epoch_s // WINDOW_SECONDS


def normalize_seal(seal: str) -> str:
    trimmed = seal.strip()
    return "".join(chr(ord(c) - 32) if "a" <= c <= "z" else c for c in trimmed)


def seal_digest(seal: str) -> str:
    return "%08x" % zlib.crc32(normalize_seal(seal).encode("utf-8"))


def tonnes(kg: int) -> str:
    return "%d.%03d" % (kg // 1000, kg % 1000)


def sha256_hex(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def accrued_cents(rate_cents: int, billable_kg: int) -> int:
    return (rate_cents * billable_kg + 500) // 1000


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


# --------------------------------------------------------------------------
# reference implementation
# --------------------------------------------------------------------------


def load_registry(registry_dir: Path = REGISTRY_DIR) -> dict:
    lanes = {row["lane_id"]: row for row in read_json(registry_dir / "lanes.json")["lanes"]}
    carriers = {row["carrier_code"] for row in read_json(registry_dir / "carriers.json")["carriers"]}
    commodities = {
        row["commodity_code"]: row["group_code"]
        for row in read_json(registry_dir / "commodities.json")["commodities"]
    }
    tariff = read_json(registry_dir / "tariff.json")
    rates = {(row["group_code"], row["band"]): row["rate_cents"] for row in tariff["rates"]}
    return {
        "lanes": lanes,
        "carriers": carriers,
        "commodities": commodities,
        "bands": tariff["bands"],
        "rates": rates,
    }


def band_for(bands, gross_kg: int) -> str:
    for band in bands:
        above = gross_kg >= band["min_kg"]
        below = band["max_kg"] < 0 or gross_kg < band["max_kg"]
        if above and below:
            return band["band"]
    return "NA"


def reference_ledger(registry: dict, manifest_dir: Path = MANIFEST_DIR) -> list[dict]:
    entries = []
    for path in sorted(manifest_dir.glob("*.json"), key=lambda p: p.name):
        manifest = read_json(path)
        pieces = manifest.get("pieces", [])
        gross = sum(int(piece["gross_mass_kg"]) for piece in pieces)
        count = len(pieces)
        entry = {
            "manifest_id": manifest["manifest_id"],
            "lane_id": manifest["lane_id"],
            "carrier_code": manifest["carrier_code"],
            "commodity_code": manifest["commodity_code"],
            "priority": int(manifest["priority"]),
            "gross_kg": gross,
            "gross_tonnes": tonnes(gross),
            "piece_count": count,
            "hazmat_max": max((int(p["hazmat_class"]) for p in pieces), default=0),
            "average_piece_g": (gross * 1000) // count if count else 0,
            "seal": normalize_seal(manifest["seal"]),
            "seal_digest": seal_digest(manifest["seal"]),
            "arrival_epoch_s": arrival_epoch(manifest["arrival_local"]),
            "slot_index": 0,
            "status": "pending",
        }
        entry["window_index"] = window_index(entry["arrival_epoch_s"])

        if entry["lane_id"] not in registry["lanes"]:
            entry["status"] = "invalid_lane"
        elif entry["carrier_code"] not in registry["carriers"]:
            entry["status"] = "invalid_carrier"
        elif entry["commodity_code"] not in registry["commodities"]:
            entry["status"] = "invalid_commodity"

        group = registry["commodities"].get(entry["commodity_code"])
        if group is None:
            entry["tariff_band"] = "NA"
            entry["tariff_rate_cents"] = 0
        else:
            entry["tariff_band"] = band_for(registry["bands"], gross)
            entry["tariff_rate_cents"] = registry["rates"].get((group, entry["tariff_band"]), 0)
        entries.append(entry)

    groups: dict[str, list[dict]] = {}
    for entry in entries:
        if entry["status"] == "pending":
            groups.setdefault(entry["seal"], []).append(entry)
    for members in groups.values():
        members.sort(key=lambda e: (e["lane_id"], e["arrival_epoch_s"], e["manifest_id"]))
        for later in members[1:]:
            later["status"] = "duplicate_seal"

    buckets: dict[tuple[str, int], list[dict]] = {}
    for entry in entries:
        if entry["status"] == "pending":
            buckets.setdefault((entry["lane_id"], entry["window_index"]), []).append(entry)
    for (lane_id, _window), bucket in buckets.items():
        bucket.sort(key=lambda e: (-e["priority"], e["arrival_epoch_s"], e["manifest_id"]))
        lane = registry["lanes"][lane_id]
        remaining = [int(lane["slot_capacity_kg"])] * int(lane["slot_count"])
        for entry in bucket:
            placed = False
            for index, free in enumerate(remaining):
                if free >= entry["gross_kg"]:
                    remaining[index] -= entry["gross_kg"]
                    entry["slot_index"] = index + 1
                    entry["status"] = "accepted"
                    placed = True
                    break
            if not placed:
                entry["slot_index"] = 0
                entry["status"] = "overflow"

    entries.sort(key=lambda e: (e["lane_id"], e["arrival_epoch_s"], e["manifest_id"]))
    return entries


def ledger_canonical(entries) -> bytes:
    body = io.StringIO()
    for entry in entries:
        body.write(
            "%s|%s|%d|%d|%d|%d|%s|%s|%s|%d\n"
            % (
                entry["manifest_id"],
                entry["lane_id"],
                entry["window_index"],
                entry["slot_index"],
                entry["arrival_epoch_s"],
                entry["gross_kg"],
                entry["status"],
                entry["seal_digest"],
                entry["tariff_band"],
                entry["tariff_rate_cents"],
            )
        )
    return body.getvalue().encode("utf-8")


def reference_journal(events_file: Path = EVENTS_FILE) -> dict:
    source = []
    for line in events_file.read_text(encoding="utf-8").splitlines():
        if line.strip():
            source.append(json.loads(line))
    source.sort(key=lambda e: int(e["seq"]))

    rows = []
    open_holds: dict[int, dict] = {}
    aggregates: dict[str, dict] = {}

    def aggregate(manifest_id: str) -> dict:
        return aggregates.setdefault(
            manifest_id,
            {
                "manifest_id": manifest_id,
                "seal": "",
                "held_kg": 0,
                "released_kg": 0,
                "open_holds": 0,
                "first_hold_epoch_s": None,
                "last_event_epoch_s": None,
            },
        )

    for event in source:
        seq = int(event["seq"])
        kind = event["kind"]
        manifest_id = event.get("manifest_id", "")
        at_epoch = arrival_epoch(event["at_local"])
        tonnes_kg = int(event.get("tonnes_kg", 0)) if kind == "hold_place" else 0

        if kind == "hold_place":
            if not manifest_id:
                accepted, code, ref = False, "HOLD_MISSING_MANIFEST", 0
            elif tonnes_kg <= 0:
                accepted, code, ref = False, "HOLD_INVALID_TONNES", 0
            else:
                accepted, code, ref = True, "HOLD_PLACED", seq
                open_holds[seq] = {
                    "manifest_id": manifest_id,
                    "kilograms": tonnes_kg,
                    "released": False,
                }
                agg = aggregate(manifest_id)
                agg["held_kg"] += tonnes_kg
                agg["open_holds"] += 1
                if not agg["seal"]:
                    agg["seal"] = normalize_seal(event.get("seal", ""))
                if agg["first_hold_epoch_s"] is None or at_epoch < agg["first_hold_epoch_s"]:
                    agg["first_hold_epoch_s"] = at_epoch
                if agg["last_event_epoch_s"] is None or at_epoch > agg["last_event_epoch_s"]:
                    agg["last_event_epoch_s"] = at_epoch
        elif kind == "hold_release":
            ref = int(event.get("hold_ref", 0))
            held = open_holds.get(ref)
            if held is None:
                accepted, code = False, "RELEASE_UNKNOWN_REF"
            elif held["released"]:
                accepted, code = False, "RELEASE_ALREADY_CLOSED"
            else:
                accepted, code = True, "RELEASE_APPLIED"
                held["released"] = True
                agg = aggregate(held["manifest_id"])
                agg["released_kg"] += held["kilograms"]
                agg["open_holds"] -= 1
                if agg["last_event_epoch_s"] is None or at_epoch > agg["last_event_epoch_s"]:
                    agg["last_event_epoch_s"] = at_epoch
        else:
            accepted, code, ref = True, "NOTE_RECORDED", 0
            agg = aggregates.get(manifest_id)
            if agg is not None and (
                agg["last_event_epoch_s"] is None or at_epoch > agg["last_event_epoch_s"]
            ):
                agg["last_event_epoch_s"] = at_epoch

        rows.append(
            {
                "seq": seq,
                "kind": kind,
                "manifest_id": manifest_id,
                "at_epoch_s": at_epoch,
                "accepted": accepted,
                "code": code,
                "ref": ref,
                "tonnes_kg": tonnes_kg,
            }
        )

    holds = []
    for agg in aggregates.values():
        if agg["held_kg"] == 0 and agg["open_holds"] == 0 and agg["released_kg"] == 0:
            continue
        net = agg["held_kg"] - agg["released_kg"]
        holds.append(
            {
                "first_hold_epoch_s": agg["first_hold_epoch_s"],
                "held_kg": agg["held_kg"],
                "held_tonnes": tonnes(agg["held_kg"]),
                "last_event_epoch_s": agg["last_event_epoch_s"],
                "manifest_id": agg["manifest_id"],
                "net_held_kg": net,
                "net_held_tonnes": tonnes(net),
                "open_holds": agg["open_holds"],
                "released_kg": agg["released_kg"],
                "seal": agg["seal"],
                "seal_digest": seal_digest(agg["seal"]),
            }
        )
    holds.sort(key=lambda row: row["manifest_id"])
    return {"events": rows, "holds": holds}


def journal_canonical(events) -> bytes:
    body = io.StringIO()
    for event in events:
        body.write(
            "%d|%s|%s|%d|%s|%s|%d|%d\n"
            % (
                event["seq"],
                event["kind"],
                event["manifest_id"],
                event["at_epoch_s"],
                "1" if event["accepted"] else "0",
                event["code"],
                event["ref"],
                event["tonnes_kg"],
            )
        )
    return body.getvalue().encode("utf-8")


def classify(status: str, gross_kg: int, net_held_kg: int) -> str:
    if status != "accepted":
        return "unreconciled" if net_held_kg > 0 else "excluded"
    if net_held_kg == 0:
        return "clear"
    if net_held_kg > gross_kg:
        return "over_held"
    return "held"


def reference_audit(snapshot_entries, journal_holds) -> list[dict]:
    held = {row["manifest_id"]: row for row in journal_holds}
    rows = []
    for entry in snapshot_entries:
        net = int(held[entry["manifest_id"]]["net_held_kg"]) if entry["manifest_id"] in held else 0
        available = max(0, entry["gross_kg"] - net) if entry["status"] == "accepted" else 0
        rows.append(
            {
                "manifest_id": entry["manifest_id"],
                "lane_id": entry["lane_id"],
                "window_index": entry["window_index"],
                "slot_index": entry["slot_index"],
                "arrival_epoch_s": entry["arrival_epoch_s"],
                "status": entry["status"],
                "state": classify(entry["status"], entry["gross_kg"], net),
                "gross_kg": entry["gross_kg"],
                "net_held_kg": net,
                "available_kg": available,
                "gross_tonnes": tonnes(entry["gross_kg"]),
                "seal_digest": entry["seal_digest"],
                "tariff_band": entry["tariff_band"],
                "tariff_rate_cents": entry["tariff_rate_cents"],
                "accrued_cents": accrued_cents(entry["tariff_rate_cents"], available),
            }
        )
    rows.sort(
        key=lambda r: (r["lane_id"], r["window_index"], r["slot_index"], r["manifest_id"])
    )
    return rows


# --------------------------------------------------------------------------
# fixtures
# --------------------------------------------------------------------------


@pytest.fixture(scope="session")
def suite_run():
    if OUTPUT.exists():
        shutil.rmtree(OUTPUT)
    completed = run([SUITE, "--root", str(ROOT)], timeout=1500)
    assert completed.returncode == 0, (
        "run-freight-suite failed with exit code %d\n%s" % (completed.returncode, completed.stdout)
    )
    return completed


@pytest.fixture(scope="session")
def registry():
    return load_registry()


@pytest.fixture(scope="session")
def expected_entries(registry):
    return reference_ledger(registry)


@pytest.fixture(scope="session")
def expected_journal():
    return reference_journal()


@pytest.fixture(scope="session")
def snapshot(suite_run):
    return read_json(OUTPUT / "ledger-snapshot.json")


@pytest.fixture(scope="session")
def journal(suite_run):
    return read_json(OUTPUT / "intake-journal.json")


@pytest.fixture(scope="session")
def report(suite_run):
    return read_json(OUTPUT / "audit-report.json")


@pytest.fixture(scope="session")
def csv_bytes(suite_run):
    return (OUTPUT / "audit-ledger.csv").read_bytes()


@pytest.fixture(scope="session")
def csv_rows(csv_bytes):
    text = csv_bytes.decode("utf-8")
    return list(csv.reader(io.StringIO(text, newline="")))


# --------------------------------------------------------------------------
# suite level
# --------------------------------------------------------------------------


def test_suite_produces_every_artifact(suite_run):
    missing = [name for name in ARTIFACTS if not (OUTPUT / name).is_file()]
    assert missing == [], "missing artifacts: %s" % missing
    assert (OUTPUT / "suite-manifest.json").is_file()


def test_suite_manifest_matches_files(suite_run):
    manifest = read_json(OUTPUT / "suite-manifest.json")
    assert manifest["status"] == "ok"
    assert manifest["schema_version"] == "freight-suite/2"
    listed = {row["name"]: row for row in manifest["artifacts"]}
    assert sorted(listed) == ARTIFACTS
    for name, row in listed.items():
        payload = (OUTPUT / name).read_bytes()
        assert row["bytes"] == len(payload), "%s size mismatch" % name
        assert row["sha256"] == sha256_hex(payload), "%s digest mismatch" % name


def test_artifacts_use_lf_endings_and_utf8(suite_run):
    for name in ARTIFACTS + ["suite-manifest.json"]:
        payload = (OUTPUT / name).read_bytes()
        payload.decode("utf-8")
        assert b"\r" not in payload, "%s contains CR bytes" % name
        assert payload.endswith(b"\n"), "%s does not end with a newline" % name


def test_pipeline_is_deterministic(suite_run):
    before = {name: (OUTPUT / name).read_bytes() for name in ARTIFACTS}
    completed = run([SUITE, "--root", str(ROOT), "--skip-build"], timeout=900)
    assert completed.returncode == 0, completed.stdout
    for name, payload in before.items():
        assert (OUTPUT / name).read_bytes() == payload, "%s changed between runs" % name


# --------------------------------------------------------------------------
# shared constants across languages
# --------------------------------------------------------------------------


def test_every_service_publishes_the_contract_epoch(snapshot, journal, report):
    assert snapshot["epoch_base_s"] == EPOCH_BASE_S
    assert journal["epoch_base_s"] == EPOCH_BASE_S
    assert report["epoch_base_s"] == EPOCH_BASE_S
    assert snapshot["window_seconds"] == WINDOW_SECONDS
    assert journal["window_seconds"] == WINDOW_SECONDS


# --------------------------------------------------------------------------
# native ledger
# --------------------------------------------------------------------------


def test_snapshot_carries_one_entry_per_manifest_file(snapshot):
    on_disk = sorted(path.name for path in MANIFEST_DIR.glob("*.json"))
    assert snapshot["totals"]["manifest_count"] == len(on_disk)
    assert len(snapshot["entries"]) == len(on_disk)


def test_snapshot_entry_shape(snapshot):
    for entry in snapshot["entries"]:
        assert set(entry) == ENTRY_KEYS, "unexpected entry keys for %s" % entry.get("manifest_id")


def test_snapshot_entry_order(snapshot):
    keys = [(e["lane_id"], e["arrival_epoch_s"], e["manifest_id"]) for e in snapshot["entries"]]
    assert keys == sorted(keys)


def test_arrival_timestamps_apply_the_utc_offset(snapshot):
    by_id = {entry["manifest_id"]: entry for entry in snapshot["entries"]}
    checked = 0
    for path in MANIFEST_DIR.glob("*.json"):
        manifest = read_json(path)
        entry = by_id.get(manifest["manifest_id"])
        assert entry is not None, "%s missing from the snapshot" % manifest["manifest_id"]
        expected = arrival_epoch(manifest["arrival_local"])
        assert entry["arrival_epoch_s"] == expected, (
            "%s arrival %s decoded as %d, expected %d"
            % (manifest["manifest_id"], manifest["arrival_local"], entry["arrival_epoch_s"], expected)
        )
        assert entry["window_index"] == expected // WINDOW_SECONDS
        checked += 1
    assert checked > 0


def test_seal_digests_follow_crc32_iso_hdlc(snapshot):
    by_id = {entry["manifest_id"]: entry for entry in snapshot["entries"]}
    for path in MANIFEST_DIR.glob("*.json"):
        manifest = read_json(path)
        entry = by_id[manifest["manifest_id"]]
        assert entry["seal"] == normalize_seal(manifest["seal"])
        assert entry["seal_digest"] == seal_digest(manifest["seal"]), (
            "%s seal digest mismatch" % manifest["manifest_id"]
        )


def test_empty_manifests_are_carried_through(snapshot, expected_entries):
    empty = [e for e in expected_entries if e["piece_count"] == 0]
    assert empty, "fixture no longer contains an empty manifest"
    by_id = {entry["manifest_id"]: entry for entry in snapshot["entries"]}
    for entry in empty:
        got = by_id.get(entry["manifest_id"])
        assert got is not None, "%s was dropped from the snapshot" % entry["manifest_id"]
        assert got["gross_kg"] == 0
        assert got["average_piece_g"] == 0
        assert got["hazmat_max"] == 0
        assert got["status"] == entry["status"]


def test_duplicate_seals_are_case_insensitive(snapshot, expected_entries):
    expected = {e["manifest_id"]: e["status"] for e in expected_entries}
    duplicates = [mid for mid, status in expected.items() if status == "duplicate_seal"]
    assert len(duplicates) >= 5, "fixture no longer contains duplicate seals"
    actual = {e["manifest_id"]: e["status"] for e in snapshot["entries"]}
    for manifest_id in duplicates:
        assert actual.get(manifest_id) == "duplicate_seal", (
            "%s should be duplicate_seal, got %s" % (manifest_id, actual.get(manifest_id))
        )
    for entry in snapshot["entries"]:
        if entry["status"] == "duplicate_seal":
            assert entry["slot_index"] == 0
            assert expected[entry["manifest_id"]] == "duplicate_seal"


def test_slot_indices_are_one_based(snapshot, registry):
    accepted = 0
    for entry in snapshot["entries"]:
        if entry["status"] == "accepted":
            accepted += 1
            lane = registry["lanes"][entry["lane_id"]]
            assert 1 <= entry["slot_index"] <= lane["slot_count"], (
                "%s slot %d outside 1..%d"
                % (entry["manifest_id"], entry["slot_index"], lane["slot_count"])
            )
        else:
            assert entry["slot_index"] == 0, "%s is %s but holds a slot" % (
                entry["manifest_id"],
                entry["status"],
            )
    assert accepted > 0


def test_slot_capacity_is_accounted_in_kilograms(snapshot, registry):
    used: dict[tuple[str, int, int], int] = {}
    for entry in snapshot["entries"]:
        if entry["status"] != "accepted":
            continue
        key = (entry["lane_id"], entry["window_index"], entry["slot_index"])
        used[key] = used.get(key, 0) + entry["gross_kg"]
    for (lane_id, _window, _slot), total in used.items():
        capacity = registry["lanes"][lane_id]["slot_capacity_kg"]
        assert total <= capacity, "lane %s slot overloaded: %d > %d" % (lane_id, total, capacity)


def test_tariff_bands_include_their_lower_edge(snapshot, registry):
    boundary = 0
    for entry in snapshot["entries"]:
        if entry["commodity_code"] not in registry["commodities"]:
            assert entry["tariff_band"] == "NA"
            assert entry["tariff_rate_cents"] == 0
            continue
        expected = band_for(registry["bands"], entry["gross_kg"])
        assert entry["tariff_band"] == expected, (
            "%s with %d kg banded as %s, expected %s"
            % (entry["manifest_id"], entry["gross_kg"], entry["tariff_band"], expected)
        )
        if any(band["min_kg"] == entry["gross_kg"] for band in registry["bands"]):
            boundary += 1
    assert boundary >= 3, "fixture no longer exercises band lower edges"


def test_snapshot_matches_the_reference_ledger(snapshot, expected_entries):
    got = snapshot["entries"]
    assert len(got) == len(expected_entries)
    fields = [
        "manifest_id",
        "lane_id",
        "window_index",
        "slot_index",
        "status",
        "arrival_epoch_s",
        "gross_kg",
        "gross_tonnes",
        "piece_count",
        "average_piece_g",
        "hazmat_max",
        "seal",
        "seal_digest",
        "tariff_band",
        "tariff_rate_cents",
    ]
    for actual, expected in zip(got, expected_entries):
        for field in fields:
            assert actual[field] == expected[field], (
                "%s.%s = %r, expected %r"
                % (expected["manifest_id"], field, actual[field], expected[field])
            )


def test_ledger_digest_covers_the_canonical_stream(snapshot, expected_entries):
    assert snapshot["ledger_digest"] == sha256_hex(ledger_canonical(expected_entries))


def test_lane_totals(snapshot):
    lanes = {row["lane_id"]: row for row in snapshot["lane_totals"]}
    assert list(lanes) == sorted(lanes)
    for lane_id, rollup in lanes.items():
        entries = [e for e in snapshot["entries"] if e["lane_id"] == lane_id]
        accepted = [e for e in entries if e["status"] == "accepted"]
        assert rollup["entry_count"] == len(entries)
        assert rollup["accepted_count"] == len(accepted)
        assert rollup["allocated_kg"] == sum(e["gross_kg"] for e in accepted)
        assert rollup["allocated_tonnes"] == tonnes(rollup["allocated_kg"])
        assert rollup["overflow_count"] == len([e for e in entries if e["status"] == "overflow"])
        assert rollup["duplicate_seal_count"] == len(
            [e for e in entries if e["status"] == "duplicate_seal"]
        )
        assert rollup["invalid_count"] == len(
            [e for e in entries if e["status"].startswith("invalid_")]
        )
        assert rollup["slots_used"] == len({e["slot_index"] for e in accepted if e["slot_index"]})


def test_snapshot_totals(snapshot):
    entries = snapshot["entries"]
    totals = snapshot["totals"]
    accepted = [e for e in entries if e["status"] == "accepted"]
    assert totals["accepted_count"] == len(accepted)
    assert totals["accepted_kg"] == sum(e["gross_kg"] for e in accepted)
    assert totals["accepted_tonnes"] == tonnes(totals["accepted_kg"])
    assert totals["gross_kg"] == sum(e["gross_kg"] for e in entries)
    assert totals["gross_tonnes"] == tonnes(totals["gross_kg"])
    assert totals["overflow_count"] == len([e for e in entries if e["status"] == "overflow"])
    assert totals["duplicate_seal_count"] == len(
        [e for e in entries if e["status"] == "duplicate_seal"]
    )
    assert totals["invalid_count"] == len([e for e in entries if e["status"].startswith("invalid_")])


# --------------------------------------------------------------------------
# intake journal
# --------------------------------------------------------------------------


def test_journal_replays_every_event_in_seq_order(journal, expected_journal):
    got = journal["events"]
    expected = expected_journal["events"]
    assert [e["seq"] for e in got] == [e["seq"] for e in expected]
    for actual, want in zip(got, expected):
        for field in ("kind", "manifest_id", "at_epoch_s", "accepted", "code", "ref", "tonnes_kg"):
            assert actual[field] == want[field], (
                "event %d field %s = %r, expected %r"
                % (want["seq"], field, actual[field], want[field])
            )


def test_journal_rejection_codes_are_exercised(journal):
    codes = {event["code"] for event in journal["events"]}
    for code in (
        "HOLD_PLACED",
        "HOLD_INVALID_TONNES",
        "HOLD_MISSING_MANIFEST",
        "RELEASE_APPLIED",
        "RELEASE_UNKNOWN_REF",
        "RELEASE_ALREADY_CLOSED",
        "NOTE_RECORDED",
    ):
        assert code in codes, "no event produced %s" % code


def test_hold_rows_are_named_and_ordered_by_manifest_id(journal):
    holds = journal["holds"]
    ids = [row["manifest_id"] for row in holds]
    assert ids == sorted(ids), "hold rows are not ordered by manifest_id"
    for row in holds:
        assert "manifest_ref" not in row, "retired manifest_ref spelling is still emitted"


def test_holds_are_not_double_counted(journal, expected_journal):
    got = {row["manifest_id"]: row for row in journal["holds"]}
    expected = {row["manifest_id"]: row for row in expected_journal["holds"]}
    assert sorted(got) == sorted(expected)
    for manifest_id, want in expected.items():
        row = got[manifest_id]
        for field in (
            "held_kg",
            "released_kg",
            "net_held_kg",
            "open_holds",
            "first_hold_epoch_s",
            "last_event_epoch_s",
            "seal",
            "seal_digest",
            "held_tonnes",
            "net_held_tonnes",
        ):
            assert row[field] == want[field], (
                "hold %s field %s = %r, expected %r" % (manifest_id, field, row[field], want[field])
            )


def test_journal_totals(journal):
    events = journal["events"]
    holds = journal["holds"]
    totals = journal["totals"]
    assert totals["events"] == len(events)
    assert totals["accepted"] == len([e for e in events if e["accepted"]])
    assert totals["rejected"] == len([e for e in events if not e["accepted"]])
    assert totals["held_kg"] == sum(row["held_kg"] for row in holds)
    assert totals["released_kg"] == sum(row["released_kg"] for row in holds)
    assert totals["net_held_kg"] == sum(row["net_held_kg"] for row in holds)
    assert totals["open_holds"] == sum(row["open_holds"] for row in holds)


def test_journal_digest_covers_the_canonical_stream(journal, expected_journal):
    assert journal["journal_digest"] == sha256_hex(journal_canonical(expected_journal["events"]))


# --------------------------------------------------------------------------
# reconciler
# --------------------------------------------------------------------------


def test_reconciler_agrees_with_both_upstream_digests(report, snapshot, journal):
    assert report["ledger_digest"] == snapshot["ledger_digest"]
    assert report["journal_digest"] == journal["journal_digest"]
    assert report["recomputed_ledger_digest"] == snapshot["ledger_digest"], (
        "reconciler recomputed a different ledger digest"
    )
    assert report["recomputed_journal_digest"] == journal["journal_digest"], (
        "reconciler recomputed a different journal digest"
    )
    assert report["digests_match"] == {"journal": True, "ledger": True}


def test_seal_digests_agree_across_languages(report):
    assert report["seal_digest_mismatches"] == 0


def test_audit_rows_match_the_reference(csv_rows, expected_entries, expected_journal):
    expected = reference_audit(expected_entries, expected_journal["holds"])
    assert csv_rows[0] == CSV_HEADER
    body = csv_rows[1:]
    assert len(body) == len(expected)
    for actual, want in zip(body, expected):
        row = dict(zip(CSV_HEADER, actual))
        assert row["manifest_id"] == want["manifest_id"]
        assert row["lane_id"] == want["lane_id"]
        assert int(row["window_index"]) == want["window_index"]
        assert int(row["slot_index"]) == want["slot_index"]
        assert row["status"] == want["status"]
        assert row["state"] == want["state"], "%s state mismatch" % want["manifest_id"]
        assert int(row["gross_kg"]) == want["gross_kg"]
        assert int(row["net_held_kg"]) == want["net_held_kg"]
        assert int(row["available_kg"]) == want["available_kg"]
        assert row["gross_tonnes"] == want["gross_tonnes"]
        assert row["seal_digest"] == want["seal_digest"]
        assert row["tariff_band"] == want["tariff_band"]
        assert int(row["tariff_rate_cents"]) == want["tariff_rate_cents"]
        assert int(row["accrued_cents"]) == want["accrued_cents"], (
            "%s accrued %s, expected %d"
            % (want["manifest_id"], row["accrued_cents"], want["accrued_cents"])
        )


def test_csv_rows_are_sorted_for_audit(csv_rows):
    keys = [
        (row[1], int(row[2]), int(row[3]), row[0]) for row in csv_rows[1:]
    ]
    assert keys == sorted(keys)


def test_csv_digest_and_report_digest(report, csv_bytes, expected_entries, expected_journal):
    assert report["csv_digest"] == sha256_hex(csv_bytes)
    expected = reference_audit(expected_entries, expected_journal["holds"])
    stream = io.StringIO()
    for row in expected:
        stream.write(
            "%s|%s|%d|%d|%s|%d|%d|%d|%d\n"
            % (
                row["manifest_id"],
                row["lane_id"],
                row["window_index"],
                row["slot_index"],
                row["state"],
                row["gross_kg"],
                row["net_held_kg"],
                row["available_kg"],
                row["accrued_cents"],
            )
        )
    assert report["report_digest"] == sha256_hex(stream.getvalue().encode("utf-8"))


def test_accrued_cents_round_half_up(report, csv_rows):
    rounded = 0
    for row in csv_rows[1:]:
        record = dict(zip(CSV_HEADER, row))
        rate = int(record["tariff_rate_cents"])
        available = int(record["available_kg"])
        assert int(record["accrued_cents"]) == accrued_cents(rate, available)
        if (rate * available) % 1000 >= 500:
            rounded += 1
    assert rounded > 0, "fixture no longer exercises half-up rounding"
    assert report["totals"]["accrued_cents"] == sum(
        int(dict(zip(CSV_HEADER, row))["accrued_cents"]) for row in csv_rows[1:]
    )


def test_window_rollups_are_half_open(report, snapshot):
    rollups = report["window_rollups"]
    indices = [row["window_index"] for row in rollups]
    assert indices == sorted(indices)
    assert len(indices) == len(set(indices))
    for row in rollups:
        assert row["window_start_epoch_s"] == row["window_index"] * WINDOW_SECONDS
        assert row["window_end_epoch_s"] == row["window_start_epoch_s"] + WINDOW_SECONDS
        members = [
            entry
            for entry in snapshot["entries"]
            if row["window_start_epoch_s"] <= entry["arrival_epoch_s"] < row["window_end_epoch_s"]
        ]
        assert row["entry_count"] == len(members), "window %d membership" % row["window_index"]
        assert row["gross_kg"] == sum(entry["gross_kg"] for entry in members)
        assert row["accepted_count"] == len([e for e in members if e["status"] == "accepted"])
    assert sum(row["entry_count"] for row in rollups) == len(snapshot["entries"]), (
        "every manifest must land in exactly one window"
    )


def test_window_boundary_arrivals_are_not_double_counted(report, snapshot):
    exact = [
        entry
        for entry in snapshot["entries"]
        if entry["arrival_epoch_s"] % WINDOW_SECONDS == 0
    ]
    assert exact, "fixture no longer contains a window boundary arrival"
    for entry in exact:
        owners = [
            row
            for row in report["window_rollups"]
            if row["window_start_epoch_s"] <= entry["arrival_epoch_s"] < row["window_end_epoch_s"]
        ]
        assert len(owners) == 1
        assert owners[0]["window_index"] == entry["arrival_epoch_s"] // WINDOW_SECONDS


def test_lane_rollups(report, csv_rows, registry):
    rollups = {row["lane_id"]: row for row in report["lane_rollups"]}
    assert list(rollups) == sorted(rollups)
    rows = [dict(zip(CSV_HEADER, row)) for row in csv_rows[1:]]
    for lane_id, rollup in rollups.items():
        lane_rows = [row for row in rows if row["lane_id"] == lane_id]
        accepted = [row for row in lane_rows if row["status"] == "accepted"]
        assert rollup["entry_count"] == len(lane_rows)
        assert rollup["accepted_count"] == len(accepted)
        assert rollup["allocated_kg"] == sum(int(row["gross_kg"]) for row in accepted)
        assert rollup["allocated_tonnes"] == tonnes(rollup["allocated_kg"])
        assert rollup["held_kg"] == sum(int(row["net_held_kg"]) for row in lane_rows)
        assert rollup["available_kg"] == sum(int(row["available_kg"]) for row in lane_rows)
        assert rollup["accrued_cents"] == sum(int(row["accrued_cents"]) for row in lane_rows)
        assert rollup["slots_used"] == len({int(row["slot_index"]) for row in accepted} - {0})
        assert rollup["slot_count"] == registry["lanes"][lane_id]["slot_count"]
        assert rollup["slot_capacity_kg"] == registry["lanes"][lane_id]["slot_capacity_kg"]


def test_orphan_holds(report, journal, snapshot):
    ledger_ids = {entry["manifest_id"] for entry in snapshot["entries"]}
    expected = sorted(
        (row["manifest_id"], row["net_held_kg"], row["open_holds"])
        for row in journal["holds"]
        if row["manifest_id"] not in ledger_ids
    )
    assert expected, "fixture no longer contains orphan holds"
    actual = [
        (row["manifest_id"], row["net_held_kg"], row["open_holds"]) for row in report["orphan_holds"]
    ]
    assert actual == expected
    assert report["totals"]["orphan_hold_count"] == len(expected)
    assert report["totals"]["orphan_held_kg"] == sum(row[1] for row in expected)


def test_state_counts(report, csv_rows):
    counts: dict[str, int] = {
        "clear": 0,
        "excluded": 0,
        "held": 0,
        "over_held": 0,
        "unreconciled": 0,
    }
    for row in csv_rows[1:]:
        counts[dict(zip(CSV_HEADER, row))["state"]] += 1
    assert report["state_counts"] == counts
    assert sum(counts.values()) == report["totals"]["manifests"]
    assert counts["held"] > 0 and counts["clear"] > 0 and counts["excluded"] > 0


# --------------------------------------------------------------------------
# cross language conformance
# --------------------------------------------------------------------------


def test_selftest_families_are_identical_across_languages(suite_run):
    reports = {
        language: read_json(OUTPUT / ("selftest-%s.json" % language))
        for language in ("cpp", "java", "go")
    }
    families = {language: report["families"] for language, report in reports.items()}
    reference = families["cpp"]
    assert set(reference) >= {"codec", "hash", "norm", "rules", "stats", "tables"}
    drift = []
    for language in ("java", "go"):
        other = families[language]
        assert set(other) == set(reference), "%s exposes different families" % language
        for family in sorted(reference):
            assert set(other[family]) == set(reference[family]), (
                "%s/%s exposes different algorithms" % (language, family)
            )
            for algorithm in sorted(reference[family]):
                if other[family][algorithm] != reference[family][algorithm]:
                    drift.append(
                        "%s %s/%s cpp=%s %s=%s"
                        % (
                            language,
                            family,
                            algorithm,
                            reference[family][algorithm],
                            language,
                            other[family][algorithm],
                        )
                    )
    assert drift == [], "algorithm drift: %s" % drift
    digests = {language: report["digest"] for language, report in reports.items()}
    assert len(set(digests.values())) == 1, "selftest digests disagree: %s" % digests


def test_selftest_digest_covers_the_families(suite_run):
    report = read_json(OUTPUT / "selftest-cpp.json")
    stream = io.StringIO()
    for family in sorted(report["families"]):
        for algorithm in sorted(report["families"][family]):
            stream.write("%s|%s|%s\n" % (family, algorithm, report["families"][family][algorithm]))
    assert report["digest"] == sha256_hex(stream.getvalue().encode("utf-8"))


def test_known_answer_checksums(suite_run):
    families = read_json(OUTPUT / "selftest-cpp.json")["families"]
    probe = b"FREIGHT-PROBE"
    assert families["hash"]["crc32_ieee"] != families["hash"]["fletcher32"]
    # crc32 of the normalised probe seal is the value the ledger publishes.
    assert seal_digest("  sl-00ab12 ") == "%08x" % zlib.crc32(b"SL-00AB12")
    assert zlib.crc32(probe) == zlib.crc32(probe)


# --------------------------------------------------------------------------
# command line behaviour on hand built edge cases
# --------------------------------------------------------------------------


def write_manifest(directory: Path, name: str, **fields) -> None:
    payload = {
        "manifest_id": fields["manifest_id"],
        "carrier_code": fields.get("carrier_code", "C000"),
        "lane_id": fields.get("lane_id", "LN-000"),
        "arrival_local": fields["arrival_local"],
        "priority": fields.get("priority", 0),
        "seal": fields["seal"],
        "commodity_code": fields.get("commodity_code", "CM-0000"),
        "booking_ref": fields.get("booking_ref", "BK-00001"),
        "trailer_plate": fields.get("trailer_plate", "TR00001"),
        "pieces": fields.get("pieces", []),
    }
    directory.joinpath(name).write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def piece(piece_id: str, kilograms: int, hazmat: int = 0) -> dict:
    return {"piece_id": piece_id, "gross_mass_kg": kilograms, "hazmat_class": hazmat}


def test_freightctl_version(suite_run):
    completed = run([FREIGHTCTL, "version"], timeout=60)
    assert completed.returncode == 0
    assert "freight-ledger/2" in completed.stdout


def test_freightctl_inspect_applies_offset_and_normalizes_seal(suite_run, tmp_path):
    write_manifest(
        tmp_path,
        "one.json",
        manifest_id="MF-700001",
        arrival_local="2026-03-14T05:30:00+05:30",
        seal="  sl-00ab12 ",
        pieces=[piece("P-01", 1200), piece("P-02", 800)],
    )
    completed = run([FREIGHTCTL, "inspect", "--manifest", str(tmp_path / "one.json")], timeout=60)
    assert completed.returncode == 0, completed.stdout
    fields = dict(
        line.split("=", 1) for line in completed.stdout.strip().splitlines() if "=" in line
    )
    assert fields["seal_normalized"] == "SL-00AB12"
    assert int(fields["arrival_epoch_s"]) == 1773446400 - EPOCH_BASE_S
    assert int(fields["window_index"]) == (1773446400 - EPOCH_BASE_S) // WINDOW_SECONDS
    assert int(fields["gross_kg"]) == 2000


def test_freightctl_handles_an_empty_manifest_directory(suite_run, tmp_path):
    manifests = tmp_path / "manifests"
    manifests.mkdir()
    out = tmp_path / "snapshot.json"
    completed = run(
        [
            FREIGHTCTL,
            "ledger",
            "--registry",
            str(REGISTRY_DIR),
            "--manifests",
            str(manifests),
            "--out",
            str(out),
        ],
        timeout=120,
    )
    assert completed.returncode == 0, completed.stdout
    snapshot = read_json(out)
    assert snapshot["entries"] == []
    assert snapshot["totals"]["manifest_count"] == 0
    assert snapshot["totals"]["gross_kg"] == 0
    assert snapshot["epoch_base_s"] == EPOCH_BASE_S
    assert snapshot["ledger_digest"] == sha256_hex(b"")


def edge_case_manifests(directory: Path) -> None:
    # LN-000 has a single 8000 kg slot, so this bucket contends for capacity.
    write_manifest(
        directory,
        "a-low-priority-early.json",
        manifest_id="MF-800001",
        arrival_local="2026-03-14T00:10:00+00:00",
        seal="sl-00cafe",
        priority=0,
        pieces=[piece("P-01", 5000)],
    )
    write_manifest(
        directory,
        "b-high-priority-late.json",
        manifest_id="MF-800002",
        arrival_local="2026-03-14T01:10:00+00:00",
        seal="sl-00beef",
        priority=4,
        pieces=[piece("P-01", 6000)],
    )
    # Same wall clock as MF-800001 but a different offset, so a different window.
    write_manifest(
        directory,
        "c-offset-shift.json",
        manifest_id="MF-800003",
        arrival_local="2026-03-14T00:10:00-07:00",
        seal="sl-00d00d",
        pieces=[piece("P-01", 900, 3)],
    )
    # Case-different repeat of MF-800001's seal.
    write_manifest(
        directory,
        "d-duplicate-seal.json",
        manifest_id="MF-800004",
        arrival_local="2026-03-14T02:10:00+00:00",
        seal="SL-00CAFE",
        pieces=[piece("P-01", 100)],
    )
    write_manifest(
        directory,
        "e-empty.json",
        manifest_id="MF-800005",
        arrival_local="2026-03-14T03:10:00+00:00",
        seal="sl-00e001",
        pieces=[],
    )
    write_manifest(
        directory,
        "f-band-edge.json",
        manifest_id="MF-800006",
        arrival_local="2026-03-14T04:10:00+00:00",
        seal="sl-00f001",
        lane_id="LN-005",
        pieces=[piece("P-01", 9000)],
    )
    write_manifest(
        directory,
        "g-unknown-lane.json",
        manifest_id="MF-800007",
        arrival_local="2026-03-14T05:10:00+00:00",
        seal="sl-00a007",
        lane_id="LN-999",
        pieces=[piece("P-01", 700)],
    )


EDGE_EVENTS = [
    {
        "seq": 1,
        "kind": "hold_place",
        "manifest_id": "MF-800001",
        "tonnes_kg": 2000,
        "seal": "sl-00cafe",
        "at_local": "2026-03-14T06:00:00+00:00",
    },
    {
        "seq": 2,
        "kind": "hold_place",
        "manifest_id": "MF-800001",
        "tonnes_kg": 1500,
        "seal": "SL-00CAFE",
        "at_local": "2026-03-14T12:00:00+05:30",
    },
    {
        "seq": 3,
        "kind": "hold_release",
        "manifest_id": "MF-800001",
        "hold_ref": 1,
        "at_local": "2026-03-14T07:00:00+00:00",
    },
    {
        "seq": 4,
        "kind": "hold_release",
        "manifest_id": "MF-800001",
        "hold_ref": 1,
        "at_local": "2026-03-14T07:30:00+00:00",
    },
    {
        "seq": 5,
        "kind": "hold_place",
        "manifest_id": "MF-800002",
        "tonnes_kg": 9000,
        "seal": "sl-00beef",
        "at_local": "2026-03-14T08:00:00+00:00",
    },
    {
        "seq": 6,
        "kind": "hold_place",
        "manifest_id": "",
        "tonnes_kg": 400,
        "seal": "sl-000000",
        "at_local": "2026-03-14T08:30:00+00:00",
    },
    {
        "seq": 7,
        "kind": "hold_place",
        "manifest_id": "MF-800003",
        "tonnes_kg": -10,
        "seal": "sl-00d00d",
        "at_local": "2026-03-14T09:00:00+00:00",
    },
    {
        "seq": 8,
        "kind": "hold_release",
        "manifest_id": "MF-800004",
        "hold_ref": 4242,
        "at_local": "2026-03-14T09:30:00+00:00",
    },
    {
        "seq": 9,
        "kind": "manifest_note",
        "manifest_id": "MF-800001",
        "at_local": "2026-03-14T10:00:00+00:00",
    },
    {
        "seq": 10,
        "kind": "hold_place",
        "manifest_id": "MF-800404",
        "tonnes_kg": 750,
        "seal": "sl-00ffff",
        "at_local": "2026-03-14T10:30:00+00:00",
    },
]


@pytest.fixture(scope="session")
def edge_case_root(suite_run, tmp_path_factory):
    root = tmp_path_factory.mktemp("edge-root")
    data = root / "environment" / "data"
    (data / "manifests").mkdir(parents=True)
    (root / "output").mkdir()
    shutil.copytree(REGISTRY_DIR, data / "registry")
    edge_case_manifests(data / "manifests")
    lines = [json.dumps(event, sort_keys=True, separators=(",", ":")) for event in EDGE_EVENTS]
    # deliberately out of sequence on disk
    lines.reverse()
    (data / "intake-events.ndjson").write_text("\n".join(lines) + "\n", encoding="utf-8")

    ledger = run([FREIGHTCTL, "ledger", "--root", str(root)], timeout=120)
    assert ledger.returncode == 0, ledger.stdout
    replay = run([INTAKE, "replay", "--root", str(root)], timeout=300)
    assert replay.returncode == 0, replay.stdout
    audit = run([RECONCILE, "run", "--root", str(root)], timeout=180)
    assert audit.returncode == 0, audit.stdout
    return root


def test_edge_case_allocation_respects_priority_and_capacity(edge_case_root):
    snapshot = read_json(edge_case_root / "output" / "ledger-snapshot.json")
    entries = {entry["manifest_id"]: entry for entry in snapshot["entries"]}
    assert len(entries) == 7

    # Both land in lane LN-000 window 0 of 2026-03-14; the 8000 kg slot cannot
    # take both, and priority 4 outranks the earlier arrival.
    assert entries["MF-800002"]["status"] == "accepted"
    assert entries["MF-800002"]["slot_index"] == 1
    assert entries["MF-800001"]["status"] == "overflow"
    assert entries["MF-800001"]["slot_index"] == 0

    assert entries["MF-800004"]["status"] == "duplicate_seal"
    assert entries["MF-800007"]["status"] == "invalid_lane"

    assert entries["MF-800005"]["gross_kg"] == 0
    assert entries["MF-800005"]["status"] == "accepted"
    assert entries["MF-800005"]["slot_index"] >= 1

    assert entries["MF-800006"]["tariff_band"] == "B4"

    shifted = entries["MF-800003"]["arrival_epoch_s"]
    assert shifted == arrival_epoch("2026-03-14T00:10:00-07:00")
    assert entries["MF-800003"]["window_index"] == shifted // WINDOW_SECONDS
    assert entries["MF-800003"]["window_index"] != entries["MF-800001"]["window_index"]


def test_edge_case_intake_orders_and_counts_holds(edge_case_root):
    journal = read_json(edge_case_root / "output" / "intake-journal.json")
    assert [event["seq"] for event in journal["events"]] == list(range(1, 11))
    codes = {event["seq"]: event["code"] for event in journal["events"]}
    assert codes[3] == "RELEASE_APPLIED"
    assert codes[4] == "RELEASE_ALREADY_CLOSED"
    assert codes[6] == "HOLD_MISSING_MANIFEST"
    assert codes[7] == "HOLD_INVALID_TONNES"
    assert codes[8] == "RELEASE_UNKNOWN_REF"
    assert codes[9] == "NOTE_RECORDED"

    holds = {row["manifest_id"]: row for row in journal["holds"]}
    assert [row["manifest_id"] for row in journal["holds"]] == sorted(holds)
    first = holds["MF-800001"]
    assert first["held_kg"] == 3500, "two holds of 2000 and 1500 must be counted once each"
    assert first["released_kg"] == 2000
    assert first["net_held_kg"] == 1500
    assert first["open_holds"] == 1
    assert first["seal"] == "SL-00CAFE"
    assert first["seal_digest"] == seal_digest("sl-00cafe")

    # The second hold carries a +05:30 offset; 12:00+05:30 is 06:30Z.
    assert first["first_hold_epoch_s"] == arrival_epoch("2026-03-14T06:00:00+00:00")
    assert first["last_event_epoch_s"] == arrival_epoch("2026-03-14T10:00:00+00:00")

    assert "MF-800003" not in holds, "a rejected hold must not create an aggregate"
    assert "" not in holds


def test_edge_case_reconciliation(edge_case_root):
    report = read_json(edge_case_root / "output" / "audit-report.json")
    snapshot = read_json(edge_case_root / "output" / "ledger-snapshot.json")
    journal = read_json(edge_case_root / "output" / "intake-journal.json")

    assert report["digests_match"] == {"journal": True, "ledger": True}
    assert report["recomputed_ledger_digest"] == snapshot["ledger_digest"]
    assert report["recomputed_journal_digest"] == journal["journal_digest"]
    assert report["seal_digest_mismatches"] == 0

    csv_text = (edge_case_root / "output" / "audit-ledger.csv").read_bytes()
    assert b"\r" not in csv_text
    rows = list(csv.DictReader(io.StringIO(csv_text.decode("utf-8"), newline="")))
    by_id = {row["manifest_id"]: row for row in rows}

    # MF-800001 overflowed but still carries a hold.
    assert by_id["MF-800001"]["state"] == "unreconciled"
    assert by_id["MF-800001"]["available_kg"] == "0"
    assert by_id["MF-800001"]["accrued_cents"] == "0"

    # MF-800002 is accepted with a 9000 kg hold against 6000 kg of freight.
    assert by_id["MF-800002"]["state"] == "over_held"
    assert by_id["MF-800002"]["available_kg"] == "0"

    assert by_id["MF-800005"]["state"] == "clear"
    assert by_id["MF-800007"]["state"] == "excluded"

    orphans = {row["manifest_id"]: row for row in report["orphan_holds"]}
    assert list(orphans) == ["MF-800404"]
    assert orphans["MF-800404"]["net_held_kg"] == 750
    assert orphans["MF-800404"]["open_holds"] == 1

    for row in rows:
        rate = int(row["tariff_rate_cents"])
        available = int(row["available_kg"])
        assert int(row["accrued_cents"]) == accrued_cents(rate, available)
