"""Live-state checks for the DC yard gate-to-dock dwell control plane."""

from __future__ import annotations

import itertools
import json
import os
import sqlite3
import subprocess
import sys
from pathlib import Path
from typing import Any, Optional

ROOT = Path(os.environ.get("YARD_ROOT", "/app/yard"))
BIN = ROOT / "bin" / "yardctl"
CONFIG = ROOT / "config" / "yard.json"
CONTRACTS = ROOT / "config" / "carrier_contracts.json"
SQLITE = ROOT / "var" / "yard.sqlite"
JOURNAL = ROOT / "var" / "events.jsonl"
CHECKPOINT = ROOT / "var" / "checkpoint.json"
WAREHOUSE = ROOT / "warehouse" / "prior_cycle.sqlite"
OUT = ROOT / "out"
SNAPSHOT = OUT / "snapshot.json"
DETENTION = OUT / "detention.jsonl"
MOVES = OUT / "moves.jsonl"
REJECTS = OUT / "rejects.jsonl"
HEALTH = OUT / "health.json"
FACILITY = "DC-AUR-01"

_SEQ = itertools.count(1)


def _eid(prefix: str = "E") -> str:
    return f"{prefix}{next(_SEQ):06d}"


def _trailer(prefix: str = "ZT") -> str:
    return f"{prefix}{next(_SEQ):06d}"


def _appt_id(prefix: str = "TA") -> str:
    return f"{prefix}{next(_SEQ):06d}"


def _run(args: list[str], check: bool = False) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT)
    env["YARD_ROOT"] = str(ROOT)
    # Interpreter + script works on Windows hosts and Linux verifier images.
    return subprocess.run(
        [sys.executable, str(BIN), *args],
        cwd=str(ROOT),
        env=env,
        text=True,
        capture_output=True,
        check=check,
    )


def _stdout_json(proc: subprocess.CompletedProcess[str]) -> dict[str, Any]:
    lines = [line for line in proc.stdout.splitlines() if line.strip()]
    assert lines, f"empty stdout rc={proc.returncode} stderr={proc.stderr}"
    return json.loads(lines[-1])


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file() or path.stat().st_size == 0:
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def _db() -> sqlite3.Connection:
    con = sqlite3.connect(str(SQLITE))
    con.row_factory = sqlite3.Row
    return con


def _insert_appointment(
    *,
    appointment_id: str,
    scac: str,
    visit_type: str,
    door_class: str,
    trailer: Optional[str],
    window_start: str,
    window_end: str,
    status: str = "OPEN",
) -> None:
    con = _db()
    try:
        con.execute(
            "INSERT INTO appointments("
            "appointment_id, facility_id, scac, visit_type, door_class, trailer_number, "
            "window_start, window_end, door_id, status"
            ") VALUES (?,?,?,?,?,?,?,?,NULL,?)",
            (
                appointment_id,
                FACILITY,
                scac,
                visit_type,
                door_class,
                trailer,
                window_start,
                window_end,
                status,
            ),
        )
        con.commit()
    finally:
        con.close()


def _free_spot(zones: tuple[str, ...]) -> str:
    con = _db()
    try:
        placeholders = ",".join("?" for _ in zones)
        row = con.execute(
            f"SELECT spot_id FROM spots WHERE occupant_visit_id IS NULL "
            f"AND reserved_move_id IS NULL AND zone IN ({placeholders}) "
            f"ORDER BY spot_id LIMIT 1",
            zones,
        ).fetchone()
        assert row is not None, f"no free spot in {zones}"
        return str(row["spot_id"])
    finally:
        con.close()


def _free_apron(door_class: Optional[str] = None, reefer: Optional[int] = None) -> tuple[str, str]:
    def _query(con: sqlite3.Connection) -> Optional[sqlite3.Row]:
        clauses = [
            "s.zone = 'DOCK_APRON'",
            "s.occupant_visit_id IS NULL",
            "s.reserved_move_id IS NULL",
            "d.live_capable = 1",
        ]
        params: list[Any] = []
        if door_class is not None:
            clauses.append("d.door_class = ?")
            params.append(door_class)
        if reefer is not None:
            clauses.append("d.reefer_plug = ?")
            params.append(reefer)
        sql = (
            "SELECT s.spot_id, d.door_id FROM spots s "
            "JOIN doors d ON d.door_id = s.door_id WHERE "
            + " AND ".join(clauses)
            + " ORDER BY s.spot_id LIMIT 1"
        )
        return con.execute(sql, params).fetchone()

    con = _db()
    try:
        row = _query(con)
        if row is not None:
            return str(row["spot_id"]), str(row["door_id"])
        # Liberate one docked visit so later live scenarios still have apron capacity.
        clauses = ["s.zone = 'DOCK_APRON'", "s.occupant_visit_id IS NOT NULL", "d.live_capable = 1"]
        params: list[Any] = []
        if door_class is not None:
            clauses.append("d.door_class = ?")
            params.append(door_class)
        if reefer is not None:
            clauses.append("d.reefer_plug = ?")
            params.append(reefer)
        occupied = con.execute(
            "SELECT s.spot_id, d.door_id, s.occupant_visit_id AS visit_id FROM spots s "
            "JOIN doors d ON d.door_id = s.door_id WHERE "
            + " AND ".join(clauses)
            + " ORDER BY s.spot_id LIMIT 1",
            params,
        ).fetchone()
        assert occupied is not None, "no free apron"
        visit_id = str(occupied["visit_id"])
    finally:
        con.close()

    # Clear holds that would block gate-out, then exit the unit.
    hold_con = _db()
    try:
        hold_con.execute(
            "UPDATE holds SET active = 0, released_at = ? WHERE visit_id = ? AND active = 1",
            ("2026-03-16T00:00:00Z", visit_id),
        )
        hold_con.commit()
    finally:
        hold_con.close()
    out = _run(
        [
            "gate-out",
            "--event-id",
            _eid("X"),
            "--visit-id",
            visit_id,
            "--at",
            "2026-03-16T00:00:00Z",
        ]
    )
    assert out.returncode == 0, out.stdout + out.stderr
    con = _db()
    try:
        row = _query(con)
        assert row is not None, "no free apron after liberate"
        return str(row["spot_id"]), str(row["door_id"])
    finally:
        con.close()


def _free_chassis() -> str:
    con = _db()
    try:
        row = con.execute(
            "SELECT chassis_id FROM chassis_units WHERE mounted_visit_id IS NULL "
            "ORDER BY chassis_id LIMIT 1"
        ).fetchone()
        assert row is not None
        return str(row["chassis_id"])
    finally:
        con.close()


def _visit_row(visit_id: str) -> sqlite3.Row:
    con = _db()
    try:
        row = con.execute("SELECT * FROM visits WHERE visit_id = ?", (visit_id,)).fetchone()
        assert row is not None, visit_id
        return row
    finally:
        con.close()


def _spot_row(spot_id: str) -> sqlite3.Row:
    con = _db()
    try:
        row = con.execute("SELECT * FROM spots WHERE spot_id = ?", (spot_id,)).fetchone()
        assert row is not None, spot_id
        return row
    finally:
        con.close()


def _journal_size() -> int:
    return JOURNAL.stat().st_size if JOURNAL.is_file() else 0


def _checkpoint_bytes() -> bytes:
    return CHECKPOINT.read_bytes() if CHECKPOINT.is_file() else b""


def _applied_seq() -> int:
    con = _db()
    try:
        return int(con.execute("SELECT last_applied_seq FROM applied WHERE id = 1").fetchone()[0])
    finally:
        con.close()


def _gate_drop(
    *,
    scac: str = "AAAA",
    trailer: Optional[str] = None,
    at: str = "2026-03-10T15:30:00Z",
    window_start: str = "2026-03-10T15:00:00Z",
    window_end: str = "2026-03-10T16:00:00Z",
    on_ground: int = 1,
    equipment: str = "DRY_53",
    seal: Optional[str] = None,
) -> tuple[str, str, str]:
    trailer = trailer or _trailer()
    appt = _appt_id()
    spot = _free_spot(("DROP_LOT", "STAGING"))
    _insert_appointment(
        appointment_id=appt,
        scac=scac,
        visit_type="DROP_IN",
        door_class="DRY",
        trailer=trailer,
        window_start=window_start,
        window_end=window_end,
    )
    args = [
        "gate-in",
        "--event-id",
        _eid(),
        "--scac",
        scac,
        "--trailer",
        trailer,
        "--visit-type",
        "DROP_IN",
        "--equipment",
        equipment,
        "--at",
        at,
        "--appointment-id",
        appt,
        "--spot-id",
        spot,
        "--on-ground",
        str(on_ground),
    ]
    if seal:
        args.extend(["--seal", seal])
    proc = _run(args)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    visit_id = str(_stdout_json(proc)["result"]["visit_id"])
    return visit_id, spot, trailer


def _gate_live(
    *,
    scac: str = "AAAA",
    trailer: Optional[str] = None,
    at: str = "2026-03-10T15:30:00Z",
    window_start: str = "2026-03-10T15:00:00Z",
    window_end: str = "2026-03-10T16:00:00Z",
    equipment: str = "DRY_53",
    door_class: str = "DRY",
    seal: str = "SEAL1",
) -> tuple[str, str, str, str]:
    trailer = trailer or _trailer()
    appt = _appt_id()
    spot, door = _free_apron(door_class=door_class, reefer=1 if equipment == "REEFER_53" else 0)
    _insert_appointment(
        appointment_id=appt,
        scac=scac,
        visit_type="LIVE_IN",
        door_class=door_class if door_class != "OUTBOUND" else "DRY",
        trailer=trailer,
        window_start=window_start,
        window_end=window_end,
    )
    proc = _run(
        [
            "gate-in",
            "--event-id",
            _eid(),
            "--scac",
            scac,
            "--trailer",
            trailer,
            "--visit-type",
            "LIVE_IN",
            "--equipment",
            equipment,
            "--at",
            at,
            "--appointment-id",
            appt,
            "--spot-id",
            spot,
            "--door-id",
            door,
            "--seal",
            seal,
        ]
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    visit_id = str(_stdout_json(proc)["result"]["visit_id"])
    return visit_id, spot, door, trailer


# --- preservation ---


def test_p2p_bin_and_contract_present() -> None:
    """Operator binary and binding yard contract remain present after repair."""
    assert BIN.is_file()
    assert (ROOT / "docs" / "yard-contract.md").is_file()
    assert CONFIG.is_file()
    assert CONTRACTS.is_file()


def test_p2p_seed_scale_preserved() -> None:
    """Inherited operating history stays at production scale."""
    con = _db()
    try:
        visits = int(con.execute("SELECT COUNT(*) FROM visits").fetchone()[0])
        doors = int(con.execute("SELECT COUNT(*) FROM doors").fetchone()[0])
        spots = int(con.execute("SELECT COUNT(*) FROM spots").fetchone()[0])
    finally:
        con.close()
    assert visits >= 10000
    assert doors == 48
    assert spots >= 700


def test_p2p_config_timezone_and_grace() -> None:
    """Published yard.json still declares Chicago TZ and grace minutes."""
    cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
    assert cfg["yard_tz"] == "America/Chicago"
    assert int(cfg["grace_early_minutes"]) == 30
    assert int(cfg["grace_late_minutes"]) == 15


# --- usage fence ---


def test_f2p_usage_unknown_verb_leaves_artifacts_untouched() -> None:
    """Unknown verb exits 2 and must not create or mutate journal, sqlite, checkpoint, or out files."""
    if REJECTS.exists():
        REJECTS.unlink()
    journal_before = _journal_size()
    checkpoint_before = _checkpoint_bytes()
    applied_before = _applied_seq()
    snap_before = SNAPSHOT.read_bytes() if SNAPSHOT.exists() else None
    health_before = HEALTH.read_bytes() if HEALTH.exists() else None

    proc = _run(["not-a-verb"])
    assert proc.returncode == 2
    assert _journal_size() == journal_before
    assert _checkpoint_bytes() == checkpoint_before
    assert _applied_seq() == applied_before
    assert not REJECTS.exists()
    if snap_before is None:
        assert not SNAPSHOT.exists()
    else:
        assert SNAPSHOT.read_bytes() == snap_before
    if health_before is None:
        assert not HEALTH.exists()
    else:
        assert HEALTH.read_bytes() == health_before


def test_f2p_usage_empty_event_id_no_reject_append() -> None:
    """Empty --event-id is usage failure and must not create or append rejects.jsonl."""
    if REJECTS.exists():
        REJECTS.unlink()
    journal_before = _journal_size()
    applied_before = _applied_seq()
    proc = _run(
        [
            "gate-in",
            "--event-id",
            "",
            "--scac",
            "AAAA",
            "--trailer",
            _trailer(),
            "--visit-type",
            "DROP_IN",
            "--equipment",
            "DRY_53",
            "--at",
            "2026-03-10T15:30:00Z",
            "--appointment-id",
            "MISSING",
            "--spot-id",
            "L0013",
        ]
    )
    assert proc.returncode == 2
    assert _journal_size() == journal_before
    assert _applied_seq() == applied_before
    assert not REJECTS.exists()


def test_f2p_missing_required_flag_is_usage() -> None:
    """gate-in without required flags exits 2 and must not append rejects.jsonl."""
    if REJECTS.exists():
        REJECTS.unlink()
    journal_before = _journal_size()
    proc = _run(["gate-in", "--event-id", _eid()])
    assert proc.returncode == 2
    assert _journal_size() == journal_before
    assert not REJECTS.exists()


# --- civil time / appointments ---


def test_f2p_on_window_gate_in_succeeds() -> None:
    """Gate-in inside the appointment window creates an open visit on the named spot."""
    visit_id, spot, _ = _gate_drop(at="2026-03-10T15:30:00Z")
    visit = _visit_row(visit_id)
    assert visit["state"] == "ON_YARD"
    assert visit["spot_id"] == spot
    assert _spot_row(spot)["occupant_visit_id"] == visit_id


def test_f2p_grace_early_accepts() -> None:
    """Arrivals within grace_early_minutes before window_start are accepted."""
    visit_id, _, _ = _gate_drop(at="2026-03-10T14:45:00Z")
    assert _visit_row(visit_id)["state"] == "ON_YARD"


def test_f2p_grace_late_accepts() -> None:
    """Arrivals within grace_late_minutes after window_end are accepted."""
    visit_id, _, _ = _gate_drop(at="2026-03-10T16:10:00Z")
    assert _visit_row(visit_id)["state"] == "ON_YARD"


def test_f2p_outside_grace_window_rejected() -> None:
    """Gate-in beyond window and grace publishes APPOINTMENT_WINDOW."""
    trailer = _trailer()
    appt = _appt_id()
    spot = _free_spot(("DROP_LOT", "STAGING"))
    _insert_appointment(
        appointment_id=appt,
        scac="AAAA",
        visit_type="DROP_IN",
        door_class="DRY",
        trailer=trailer,
        window_start="2026-03-10T15:00:00Z",
        window_end="2026-03-10T16:00:00Z",
    )
    proc = _run(
        [
            "gate-in",
            "--event-id",
            _eid(),
            "--scac",
            "AAAA",
            "--trailer",
            trailer,
            "--visit-type",
            "DROP_IN",
            "--equipment",
            "DRY_53",
            "--at",
            "2026-03-10T16:30:00Z",
            "--appointment-id",
            appt,
            "--spot-id",
            spot,
            "--on-ground",
            "1",
        ]
    )
    assert proc.returncode == 1
    assert _stdout_json(proc)["code"] == "APPOINTMENT_WINDOW"
    rejects = _load_jsonl(REJECTS)
    assert rejects
    assert rejects[-1]["code"] == "APPOINTMENT_WINDOW"


def test_f2p_grace_minutes_follow_yard_json() -> None:
    """Raising grace_early_minutes in yard.json must accept an arrival that the shipped 30-minute band would reject."""
    original = CONFIG.read_text(encoding="utf-8")
    trailer = _trailer()
    appt = _appt_id()
    spot = _free_spot(("DROP_LOT", "STAGING"))
    _insert_appointment(
        appointment_id=appt,
        scac="AAAA",
        visit_type="DROP_IN",
        door_class="DRY",
        trailer=trailer,
        window_start="2026-03-10T15:00:00Z",
        window_end="2026-03-10T16:00:00Z",
    )
    try:
        cfg = json.loads(original)
        cfg["grace_early_minutes"] = 90
        CONFIG.write_text(json.dumps(cfg, indent=2) + "\n", encoding="utf-8")
        proc = _run(
            [
                "gate-in",
                "--event-id",
                _eid(),
                "--scac",
                "AAAA",
                "--trailer",
                trailer,
                "--visit-type",
                "DROP_IN",
                "--equipment",
                "DRY_53",
                "--at",
                "2026-03-10T13:45:00Z",
                "--appointment-id",
                appt,
                "--spot-id",
                spot,
                "--on-ground",
                "1",
            ]
        )
        assert proc.returncode == 0, proc.stdout + proc.stderr
        visit_id = str(_stdout_json(proc)["result"]["visit_id"])
        assert _visit_row(visit_id)["state"] == "ON_YARD"
    finally:
        CONFIG.write_text(original, encoding="utf-8")


def test_f2p_dst_horizon_grace_early() -> None:
    """Chicago DST horizon still applies grace against America/Chicago civil windows."""
    # 2026-03-08 is US spring-forward; window 15:00-16:00Z is 10:00-11:00 CDT.
    visit_id, _, _ = _gate_drop(
        at="2026-03-08T14:45:00Z",
        window_start="2026-03-08T15:00:00Z",
        window_end="2026-03-08T16:00:00Z",
    )
    assert _visit_row(visit_id)["gate_in"] == "2026-03-08T14:45:00Z"


def test_f2p_live_clock_start_is_max_window_and_gate() -> None:
    """LIVE_IN clock_start is max(window_start, gate_in), not early gate_in alone."""
    visit_id, _, _, _ = _gate_live(
        at="2026-03-10T14:45:00Z",
        window_start="2026-03-10T15:00:00Z",
        window_end="2026-03-10T16:00:00Z",
    )
    assert _visit_row(visit_id)["clock_start"] == "2026-03-10T15:00:00Z"


def test_f2p_drop_clock_start_is_gate_in() -> None:
    """DROP_IN that arrives in early grace keeps clock_start equal to gate_in."""
    visit_id, _, _ = _gate_drop(at="2026-03-10T14:45:00Z")
    assert _visit_row(visit_id)["clock_start"] == "2026-03-10T14:45:00Z"


# --- occupancy / moves ---


def test_f2p_exclusive_spot_blocks_second_occupant() -> None:
    """A second gate-in to an occupied spot is SPOT_OCCUPIED."""
    visit_id, spot, _ = _gate_drop()
    trailer2 = _trailer()
    appt = _appt_id()
    _insert_appointment(
        appointment_id=appt,
        scac="AAAA",
        visit_type="DROP_IN",
        door_class="DRY",
        trailer=trailer2,
        window_start="2026-03-10T15:00:00Z",
        window_end="2026-03-10T16:00:00Z",
    )
    proc = _run(
        [
            "gate-in",
            "--event-id",
            _eid(),
            "--scac",
            "AAAA",
            "--trailer",
            trailer2,
            "--visit-type",
            "DROP_IN",
            "--equipment",
            "DRY_53",
            "--at",
            "2026-03-10T15:30:00Z",
            "--appointment-id",
            appt,
            "--spot-id",
            spot,
            "--on-ground",
            "1",
        ]
    )
    assert proc.returncode == 1
    assert _stdout_json(proc)["code"] == "SPOT_OCCUPIED"
    assert _spot_row(spot)["occupant_visit_id"] == visit_id


def test_f2p_dispatch_vacates_origin_and_reserves_dest() -> None:
    """IN_TRANSIT clears origin occupancy and reserves the destination spot."""
    visit_id, origin, _ = _gate_drop(on_ground=1)
    chassis = _free_chassis()
    assert _run(["mount-chassis", "--event-id", _eid(), "--visit-id", visit_id, "--chassis-id", chassis]).returncode == 0
    dest = _free_spot(("DROP_LOT", "STAGING"))
    proc = _run(
        [
            "dispatch-move",
            "--event-id",
            _eid(),
            "--visit-id",
            visit_id,
            "--dest-spot-id",
            dest,
        ]
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    move_id = str(_stdout_json(proc)["result"]["move_id"])
    assert _spot_row(origin)["occupant_visit_id"] is None
    dest_row = _spot_row(dest)
    assert dest_row["occupant_visit_id"] is None
    assert dest_row["reserved_move_id"] == move_id
    assert _visit_row(visit_id)["state"] == "MOVING"
    assert _visit_row(visit_id)["spot_id"] is None


def test_f2p_confirm_move_relocates_occupancy() -> None:
    """confirm-move occupies dest, clears reservation, and leaves origin empty."""
    visit_id, origin, _ = _gate_drop(on_ground=1)
    chassis = _free_chassis()
    assert _run(["mount-chassis", "--event-id", _eid(), "--visit-id", visit_id, "--chassis-id", chassis]).returncode == 0
    dest = _free_spot(("DROP_LOT", "STAGING"))
    disp = _run(
        ["dispatch-move", "--event-id", _eid(), "--visit-id", visit_id, "--dest-spot-id", dest]
    )
    assert disp.returncode == 0
    move_id = str(_stdout_json(disp)["result"]["move_id"])
    conf = _run(["confirm-move", "--event-id", _eid(), "--move-id", move_id])
    assert conf.returncode == 0, conf.stdout + conf.stderr
    assert _spot_row(origin)["occupant_visit_id"] is None
    assert _spot_row(dest)["occupant_visit_id"] == visit_id
    assert _spot_row(dest)["reserved_move_id"] is None
    assert _visit_row(visit_id)["spot_id"] == dest


def test_f2p_cancel_move_restores_origin() -> None:
    """cancel-move restores origin occupancy and clears the dest reservation."""
    visit_id, origin, _ = _gate_drop(on_ground=1)
    chassis = _free_chassis()
    assert _run(["mount-chassis", "--event-id", _eid(), "--visit-id", visit_id, "--chassis-id", chassis]).returncode == 0
    dest = _free_spot(("DROP_LOT", "STAGING"))
    disp = _run(
        ["dispatch-move", "--event-id", _eid(), "--visit-id", visit_id, "--dest-spot-id", dest]
    )
    move_id = str(_stdout_json(disp)["result"]["move_id"])
    canc = _run(["cancel-move", "--event-id", _eid(), "--move-id", move_id])
    assert canc.returncode == 0, canc.stdout + canc.stderr
    assert _spot_row(origin)["occupant_visit_id"] == visit_id
    assert _spot_row(dest)["reserved_move_id"] is None
    assert _spot_row(dest)["occupant_visit_id"] is None


def test_f2p_dest_reservation_blocks_second_dispatch() -> None:
    """A reserved destination rejects another dispatch with SPOT_OCCUPIED."""
    visit_a, _, _ = _gate_drop(on_ground=1)
    visit_b, _, _ = _gate_drop(on_ground=1)
    for visit_id in (visit_a, visit_b):
        chassis = _free_chassis()
        assert (
            _run(
                ["mount-chassis", "--event-id", _eid(), "--visit-id", visit_id, "--chassis-id", chassis]
            ).returncode
            == 0
        )
    dest = _free_spot(("DROP_LOT", "STAGING"))
    first = _run(
        ["dispatch-move", "--event-id", _eid(), "--visit-id", visit_a, "--dest-spot-id", dest]
    )
    assert first.returncode == 0
    second = _run(
        ["dispatch-move", "--event-id", _eid(), "--visit-id", visit_b, "--dest-spot-id", dest]
    )
    assert second.returncode == 1
    assert _stdout_json(second)["code"] == "SPOT_OCCUPIED"


# --- doors / chassis ---


def test_f2p_reefer_on_dry_door_rejected() -> None:
    """REEFER_53 at a dry door without a plug is DOOR_CLASS."""
    trailer = _trailer()
    appt = _appt_id()
    spot, door = _free_apron(door_class="DRY", reefer=0)
    _insert_appointment(
        appointment_id=appt,
        scac="AAAA",
        visit_type="LIVE_IN",
        door_class="DRY",
        trailer=trailer,
        window_start="2026-03-10T15:00:00Z",
        window_end="2026-03-10T16:00:00Z",
    )
    proc = _run(
        [
            "gate-in",
            "--event-id",
            _eid(),
            "--scac",
            "AAAA",
            "--trailer",
            trailer,
            "--visit-type",
            "LIVE_IN",
            "--equipment",
            "REEFER_53",
            "--at",
            "2026-03-10T15:30:00Z",
            "--appointment-id",
            appt,
            "--spot-id",
            spot,
            "--door-id",
            door,
            "--seal",
            "R1",
        ]
    )
    assert proc.returncode == 1
    assert _stdout_json(proc)["code"] == "DOOR_CLASS"


def test_f2p_drop_on_apron_rejected() -> None:
    """DROP_IN may not occupy a DOCK_APRON spot."""
    trailer = _trailer()
    appt = _appt_id()
    spot, _door = _free_apron(door_class="DRY", reefer=0)
    _insert_appointment(
        appointment_id=appt,
        scac="AAAA",
        visit_type="DROP_IN",
        door_class="DRY",
        trailer=trailer,
        window_start="2026-03-10T15:00:00Z",
        window_end="2026-03-10T16:00:00Z",
    )
    proc = _run(
        [
            "gate-in",
            "--event-id",
            _eid(),
            "--scac",
            "AAAA",
            "--trailer",
            trailer,
            "--visit-type",
            "DROP_IN",
            "--equipment",
            "DRY_53",
            "--at",
            "2026-03-10T15:30:00Z",
            "--appointment-id",
            appt,
            "--spot-id",
            spot,
            "--on-ground",
            "1",
        ]
    )
    assert proc.returncode == 1
    assert _stdout_json(proc)["code"] == "DOOR_CLASS"


def test_f2p_grounded_drop_requires_chassis_before_move() -> None:
    """Grounded DROP_IN equipment cannot enter IN_TRANSIT without a mounted chassis."""
    visit_id, _, _ = _gate_drop(on_ground=1)
    dest = _free_spot(("DROP_LOT", "STAGING"))
    proc = _run(
        ["dispatch-move", "--event-id", _eid(), "--visit-id", visit_id, "--dest-spot-id", dest]
    )
    assert proc.returncode == 1
    assert _stdout_json(proc)["code"] == "CHASSIS_REQUIRED"


def test_f2p_mount_clears_on_ground_and_is_exclusive() -> None:
    """mount-chassis sets on_ground=0 and a second visit cannot claim the same chassis."""
    visit_a, _, _ = _gate_drop(on_ground=1)
    visit_b, _, _ = _gate_drop(on_ground=1)
    chassis = _free_chassis()
    assert (
        _run(
            ["mount-chassis", "--event-id", _eid(), "--visit-id", visit_a, "--chassis-id", chassis]
        ).returncode
        == 0
    )
    assert int(_visit_row(visit_a)["on_ground"]) == 0
    assert _visit_row(visit_a)["chassis_id"] == chassis
    busy = _run(
        ["mount-chassis", "--event-id", _eid(), "--visit-id", visit_b, "--chassis-id", chassis]
    )
    assert busy.returncode == 1
    assert _stdout_json(busy)["code"] == "CHASSIS_BUSY"


# --- holds / detention ---


def test_f2p_hold_blocks_gate_out_until_release() -> None:
    """Any active hold blocks gate-out; release then allows exit."""
    visit_id, _, _ = _gate_drop()
    hold = _run(
        [
            "hold",
            "--event-id",
            _eid(),
            "--visit-id",
            visit_id,
            "--hold-code",
            "YARD_OSND",
            "--at",
            "2026-03-10T15:40:00Z",
        ]
    )
    assert hold.returncode == 0
    blocked = _run(
        [
            "gate-out",
            "--event-id",
            _eid(),
            "--visit-id",
            visit_id,
            "--at",
            "2026-03-10T18:00:00Z",
        ]
    )
    assert blocked.returncode == 1
    assert _stdout_json(blocked)["code"] == "HOLD_BLOCKS_OUT"
    rel = _run(
        [
            "release-hold",
            "--event-id",
            _eid(),
            "--visit-id",
            visit_id,
            "--hold-code",
            "YARD_OSND",
            "--at",
            "2026-03-10T16:00:00Z",
        ]
    )
    assert rel.returncode == 0, rel.stdout + rel.stderr
    out = _run(
        [
            "gate-out",
            "--event-id",
            _eid(),
            "--visit-id",
            visit_id,
            "--at",
            "2026-03-10T18:00:00Z",
        ]
    )
    assert out.returncode == 0, out.stdout + out.stderr
    assert _visit_row(visit_id)["state"] == "CLOSED"


def test_f2p_yard_hold_pauses_detention_carrier_does_not() -> None:
    """YARD_OSND pauses chargeable time; CARRIER_SEAL does not."""
    # Live free_minutes for AAAA LIVE_IN is 90. Build two early arrivals with long as-of.
    yard_visit, _, _, _ = _gate_live(
        trailer=_trailer("YA"),
        at="2026-03-10T14:45:00Z",
        window_start="2026-03-10T15:00:00Z",
        window_end="2026-03-10T16:00:00Z",
    )
    carrier_visit, _, _, _ = _gate_live(
        trailer=_trailer("CA"),
        at="2026-03-10T14:45:00Z",
        window_start="2026-03-10T15:00:00Z",
        window_end="2026-03-10T16:00:00Z",
    )
    assert (
        _run(
            [
                "hold",
                "--event-id",
                _eid(),
                "--visit-id",
                yard_visit,
                "--hold-code",
                "YARD_OSND",
                "--at",
                "2026-03-10T15:00:00Z",
            ]
        ).returncode
        == 0
    )
    assert (
        _run(
            [
                "hold",
                "--event-id",
                _eid(),
                "--visit-id",
                carrier_visit,
                "--hold-code",
                "CARRIER_SEAL",
                "--at",
                "2026-03-10T15:00:00Z",
            ]
        ).returncode
        == 0
    )
    as_of = "2026-03-10T18:00:00Z"
    assert _run(["detention-run", "--as-of", as_of]).returncode == 0
    rows = {row["visit_id"]: row for row in _load_jsonl(DETENTION)}
    assert rows[yard_visit]["pause_minutes"] >= 90
    assert rows[carrier_visit]["pause_minutes"] == 0
    assert rows[carrier_visit]["chargeable_minutes"] > rows[yard_visit]["chargeable_minutes"]


# --- journal / identity ---


def test_f2p_identical_event_id_replays_without_double_occupancy() -> None:
    """Replaying the same event_id and payload returns success without a second occupant."""
    trailer = _trailer()
    appt = _appt_id()
    spot = _free_spot(("DROP_LOT", "STAGING"))
    _insert_appointment(
        appointment_id=appt,
        scac="AAAA",
        visit_type="DROP_IN",
        door_class="DRY",
        trailer=trailer,
        window_start="2026-03-10T15:00:00Z",
        window_end="2026-03-10T16:00:00Z",
    )
    eid = _eid("R")
    args = [
        "gate-in",
        "--event-id",
        eid,
        "--scac",
        "AAAA",
        "--trailer",
        trailer,
        "--visit-type",
        "DROP_IN",
        "--equipment",
        "DRY_53",
        "--at",
        "2026-03-10T15:30:00Z",
        "--appointment-id",
        appt,
        "--spot-id",
        spot,
        "--on-ground",
        "1",
    ]
    first = _run(args)
    assert first.returncode == 0
    visit_id = str(_stdout_json(first)["result"]["visit_id"])
    journal_before = _journal_size()
    second = _run(args)
    assert second.returncode == 0
    body = _stdout_json(second)
    assert body.get("replayed") is True
    assert body["result"]["visit_id"] == visit_id
    assert _journal_size() == journal_before
    assert _spot_row(spot)["occupant_visit_id"] == visit_id


def test_f2p_event_id_payload_conflict() -> None:
    """Same event_id with a different payload is EVENT_CONFLICT and leaves occupancy unchanged."""
    trailer = _trailer()
    appt = _appt_id()
    spot = _free_spot(("DROP_LOT", "STAGING"))
    _insert_appointment(
        appointment_id=appt,
        scac="AAAA",
        visit_type="DROP_IN",
        door_class="DRY",
        trailer=trailer,
        window_start="2026-03-10T15:00:00Z",
        window_end="2026-03-10T16:00:00Z",
    )
    eid = _eid("C")
    first = _run(
        [
            "gate-in",
            "--event-id",
            eid,
            "--scac",
            "AAAA",
            "--trailer",
            trailer,
            "--visit-type",
            "DROP_IN",
            "--equipment",
            "DRY_53",
            "--at",
            "2026-03-10T15:30:00Z",
            "--appointment-id",
            appt,
            "--spot-id",
            spot,
            "--on-ground",
            "1",
        ]
    )
    assert first.returncode == 0
    visit_id = str(_stdout_json(first)["result"]["visit_id"])
    conflict = _run(
        [
            "gate-in",
            "--event-id",
            eid,
            "--scac",
            "AAAA",
            "--trailer",
            trailer,
            "--visit-type",
            "DROP_IN",
            "--equipment",
            "DRY_53",
            "--at",
            "2026-03-10T15:31:00Z",
            "--appointment-id",
            appt,
            "--spot-id",
            spot,
            "--on-ground",
            "1",
        ]
    )
    assert conflict.returncode == 1
    assert _stdout_json(conflict)["code"] == "EVENT_CONFLICT"
    assert _spot_row(spot)["occupant_visit_id"] == visit_id


def test_f2p_seal_required_for_live_in() -> None:
    """LIVE_IN without a seal is SEAL_REQUIRED."""
    trailer = _trailer()
    appt = _appt_id()
    spot, door = _free_apron(door_class="DRY", reefer=0)
    _insert_appointment(
        appointment_id=appt,
        scac="AAAA",
        visit_type="LIVE_IN",
        door_class="DRY",
        trailer=trailer,
        window_start="2026-03-10T15:00:00Z",
        window_end="2026-03-10T16:00:00Z",
    )
    proc = _run(
        [
            "gate-in",
            "--event-id",
            _eid(),
            "--scac",
            "AAAA",
            "--trailer",
            trailer,
            "--visit-type",
            "LIVE_IN",
            "--equipment",
            "DRY_53",
            "--at",
            "2026-03-10T15:30:00Z",
            "--appointment-id",
            appt,
            "--spot-id",
            spot,
            "--door-id",
            door,
        ]
    )
    assert proc.returncode == 1
    assert _stdout_json(proc)["code"] == "SEAL_REQUIRED"


def test_f2p_contract_missing_for_holdout_scac() -> None:
    """Hold-out SCAC QXRT has no carrier contract and rejects with CONTRACT_MISSING."""
    trailer = _trailer()
    appt = _appt_id()
    spot = _free_spot(("DROP_LOT", "STAGING"))
    _insert_appointment(
        appointment_id=appt,
        scac="QXRT",
        visit_type="DROP_IN",
        door_class="DRY",
        trailer=trailer,
        window_start="2026-03-10T15:00:00Z",
        window_end="2026-03-10T16:00:00Z",
    )
    proc = _run(
        [
            "gate-in",
            "--event-id",
            _eid(),
            "--scac",
            "QXRT",
            "--trailer",
            trailer,
            "--visit-type",
            "DROP_IN",
            "--equipment",
            "DRY_53",
            "--at",
            "2026-03-10T15:30:00Z",
            "--appointment-id",
            appt,
            "--spot-id",
            spot,
            "--on-ground",
            "1",
        ]
    )
    assert proc.returncode == 1
    assert _stdout_json(proc)["code"] == "CONTRACT_MISSING"


def test_f2p_open_key_is_scac_and_trailer() -> None:
    """Two SCACs may hold the same trailer number open concurrently."""
    unit = _trailer("SH")
    visit_a, _, _ = _gate_drop(scac="AAAA", trailer=unit)
    visit_b, _, _ = _gate_drop(scac="AAAB", trailer=unit)
    assert visit_a != visit_b
    assert _visit_row(visit_a)["state"] == "ON_YARD"
    assert _visit_row(visit_b)["state"] == "ON_YARD"


def test_f2p_pool_appointment_same_scac_only() -> None:
    """Pool appointments (null trailer) match only the appointment SCAC."""
    appt = _appt_id("POOL")
    _insert_appointment(
        appointment_id=appt,
        scac="AAAA",
        visit_type="DROP_IN",
        door_class="DRY",
        trailer=None,
        window_start="2026-03-10T15:00:00Z",
        window_end="2026-03-10T16:00:00Z",
    )
    ok = _run(
        [
            "gate-in",
            "--event-id",
            _eid(),
            "--scac",
            "AAAA",
            "--trailer",
            _trailer("PL"),
            "--visit-type",
            "DROP_IN",
            "--equipment",
            "DRY_53",
            "--at",
            "2026-03-10T15:30:00Z",
            "--appointment-id",
            appt,
            "--spot-id",
            _free_spot(("DROP_LOT", "STAGING")),
            "--on-ground",
            "1",
        ]
    )
    assert ok.returncode == 0, ok.stdout + ok.stderr

    appt2 = _appt_id("POOL")
    _insert_appointment(
        appointment_id=appt2,
        scac="AAAA",
        visit_type="DROP_IN",
        door_class="DRY",
        trailer=None,
        window_start="2026-03-10T15:00:00Z",
        window_end="2026-03-10T16:00:00Z",
    )
    bad = _run(
        [
            "gate-in",
            "--event-id",
            _eid(),
            "--scac",
            "AAAB",
            "--trailer",
            _trailer("PX"),
            "--visit-type",
            "DROP_IN",
            "--equipment",
            "DRY_53",
            "--at",
            "2026-03-10T15:30:00Z",
            "--appointment-id",
            appt2,
            "--spot-id",
            _free_spot(("DROP_LOT", "STAGING")),
            "--on-ground",
            "1",
        ]
    )
    assert bad.returncode == 1
    assert _stdout_json(bad)["code"] == "APPOINTMENT_MISSING"


# --- publish / warehouse / health ---


def test_f2p_snapshot_excludes_warehouse_visits() -> None:
    """Snapshot open_visits must not include prior-cycle warehouse visit ids."""
    assert _run(["snapshot"]).returncode == 0
    snap = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    open_ids = {row["visit_id"] for row in snap["open_visits"]}
    assert "W000000" not in open_ids
    assert not any(str(vid).startswith("W0") for vid in open_ids)
    assert list(snap.keys())[:4] == ["facility_id", "generated_at", "yard_tz", "as_of"]
    assert snap["yard_tz"] == "America/Chicago"


def test_f2p_detention_excludes_warehouse_visits() -> None:
    """Detention ledger covers operating sqlite visits only, never warehouse rows."""
    assert _run(["detention-run", "--as-of", "2026-03-16T00:00:00Z"]).returncode == 0
    ids = {row["visit_id"] for row in _load_jsonl(DETENTION)}
    assert "W000000" not in ids
    assert not any(str(vid).startswith("W0") for vid in ids)


def test_f2p_health_ok_when_caught_up_and_warehouse_untouched() -> None:
    """Health is ok only with matching seqs, digest agreement, and warehouse_untouched publish."""
    assert _run(["snapshot"]).returncode == 0
    snap = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    assert "W000000" not in {row["visit_id"] for row in snap["open_visits"]}
    assert _run(["health"]).returncode == 0
    health = json.loads(HEALTH.read_text(encoding="utf-8"))
    assert health["warehouse_untouched"] is True
    assert health["applied_seq"] == health["journal_seq"]
    assert health["ok"] is True
    assert isinstance(health["occupancy_digest"], str)
    assert len(health["occupancy_digest"]) == 64
    assert health["open_visit_ids"] == sorted(health["open_visit_ids"])


def test_f2p_sqlite_lag_catchup_keeps_single_occupant() -> None:
    """When sqlite applied_seq lags, the next mutating command catches up from the checkpoint fence without double occupancy."""
    visit_id, spot, _ = _gate_drop()
    trailer = str(_visit_row(visit_id)["trailer_number"])
    con = _db()
    try:
        con.execute("UPDATE applied SET last_applied_seq = 0")
        con.commit()
    finally:
        con.close()
    hold = _run(
        [
            "hold",
            "--event-id",
            _eid(),
            "--visit-id",
            visit_id,
            "--hold-code",
            "YARD_SAFETY",
            "--at",
            "2026-03-10T15:41:00Z",
        ]
    )
    assert hold.returncode == 0, hold.stdout + hold.stderr
    assert _spot_row(spot)["occupant_visit_id"] == visit_id
    con = _db()
    try:
        open_same = int(
            con.execute(
                "SELECT COUNT(*) FROM visits WHERE trailer_number = ? AND scac = ? "
                "AND state IN ('ON_YARD','MOVING','DOCKED')",
                (trailer, "AAAA"),
            ).fetchone()[0]
        )
    finally:
        con.close()
    assert open_same == 1
    events = _load_jsonl(JOURNAL)
    head = max(int(event["seq"]) for event in events)
    assert _applied_seq() == head


def test_f2p_moves_publish_sorted_by_seq() -> None:
    """moves.jsonl enumerates move rows sorted by seq after snapshot."""
    visit_id, _, _ = _gate_drop(on_ground=1)
    chassis = _free_chassis()
    assert _run(["mount-chassis", "--event-id", _eid(), "--visit-id", visit_id, "--chassis-id", chassis]).returncode == 0
    dest = _free_spot(("DROP_LOT", "STAGING"))
    assert (
        _run(
            ["dispatch-move", "--event-id", _eid(), "--visit-id", visit_id, "--dest-spot-id", dest]
        ).returncode
        == 0
    )
    assert _run(["snapshot"]).returncode == 0
    rows = _load_jsonl(MOVES)
    assert rows
    seqs = [int(row["seq"]) for row in rows]
    assert seqs == sorted(seqs)
