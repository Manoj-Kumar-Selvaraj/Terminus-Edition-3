#!/usr/bin/env python3
"""Deterministic image-build seed. Does not import the operator runtime packages."""

from __future__ import annotations

import hashlib
import json
import sqlite3
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UTC = timezone.utc
CST = timezone(timedelta(hours=-6))
CDT = timezone(timedelta(hours=-5))
DST_SWITCH = datetime(2026, 3, 8, 8, 0, tzinfo=UTC)
FACILITY = "DC-AUR-01"
HELD_OUT = "QXRT"
VISIT_N = 12600
WAREHOUSE_N = 4000
OPEN_N = 100
ALPHA = "ABCDEFGHJKLMNPQRSTUVWXYZ"


def scacs() -> list[str]:
    codes: list[str] = []
    for a in ALPHA:
        for b in ALPHA:
            for c in ALPHA:
                for d in ALPHA:
                    code = a + b + c + d
                    if code == HELD_OUT:
                        continue
                    codes.append(code)
                    if len(codes) == 72:
                        return codes
    raise RuntimeError("not enough SCAC codes")


def chicago_tz(local_naive: datetime) -> timezone:
    probe = local_naive.replace(tzinfo=CST).astimezone(UTC)
    if probe >= DST_SWITCH:
        return CDT
    return CST


def from_chicago(year: int, month: int, day: int, hour: int, minute: int) -> datetime:
    naive = datetime(year, month, day, hour, minute, 0)
    return naive.replace(tzinfo=chicago_tz(naive))


def iso(dt: datetime) -> str:
    return dt.astimezone(UTC).replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ")


def visit_type_for(n: int) -> str:
    bucket = n % 20
    if bucket < 8:
        return "LIVE_IN"
    if bucket < 13:
        return "DROP_IN"
    if bucket < 17:
        return "LIVE_OUT"
    if bucket < 19:
        return "EMPTY_OUT"
    return "LOADED_PICKUP"


def equipment_for(n: int, visit_type: str) -> str:
    choices = ("DRY_53", "REEFER_53", "TANK", "CONTAINER_40")
    if visit_type in {"LIVE_IN", "LIVE_OUT"} and n % 11 == 0:
        return "REEFER_53"
    return choices[n % 4]


def door_class_for(equipment: str, visit_type: str) -> str:
    if visit_type in {"LIVE_OUT", "EMPTY_OUT", "LOADED_PICKUP"} and equipment != "REEFER_53":
        return "OUTBOUND"
    if equipment == "REEFER_53":
        return "REEFER"
    return "DRY"


def connect(path: Path) -> sqlite3.Connection:
    if path.exists():
        path.unlink()
    path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(path))
    con.execute("PRAGMA journal_mode = OFF")
    con.execute("PRAGMA synchronous = OFF")
    con.execute("PRAGMA foreign_keys = ON")
    schema = (ROOT / "sql" / "schema.sql").read_text(encoding="utf-8")
    con.executescript(schema)
    con.execute("BEGIN")
    return con


def insert_catalog(con: sqlite3.Connection) -> None:
    for i in range(1, 49):
        if i <= 32:
            door_class, plug, live, drop, allowed = "DRY", 0, 1, 0, '["DRY_53","TANK"]'
        elif i <= 40:
            door_class, plug, live, drop, allowed = "REEFER", 1, 1, 0, '["REEFER_53"]'
        else:
            door_class, plug, live, drop, allowed = "OUTBOUND", 0, 1, 1, '["DRY_53","CONTAINER_40","TANK"]'
        door_id = f"D{i:02d}"
        con.execute(
            "INSERT INTO doors(door_id, door_class, reefer_plug, live_capable, drop_capable, allowed_equipment) "
            "VALUES (?,?,?,?,?,?)",
            (door_id, door_class, plug, live, drop, allowed),
        )
        con.execute(
            "INSERT INTO spots(spot_id, zone, door_id, occupant_visit_id, reserved_move_id) VALUES (?,?,?,?,NULL)",
            (f"A{i:02d}", "DOCK_APRON", door_id, None),
        )
    for i in range(1, 401):
        con.execute(
            "INSERT INTO spots(spot_id, zone, door_id, occupant_visit_id, reserved_move_id) VALUES (?,?,NULL,NULL,NULL)",
            (f"L{i:04d}", "DROP_LOT"),
        )
    for i in range(1, 201):
        con.execute(
            "INSERT INTO spots(spot_id, zone, door_id, occupant_visit_id, reserved_move_id) VALUES (?,?,NULL,NULL,NULL)",
            (f"S{i:04d}", "STAGING"),
        )
    for i in range(1, 73):
        spot_id = f"C{i:04d}"
        con.execute(
            "INSERT INTO spots(spot_id, zone, door_id, occupant_visit_id, reserved_move_id) VALUES (?,?,NULL,NULL,NULL)",
            (spot_id, "CHASSIS_STACK"),
        )
        con.execute(
            "INSERT INTO chassis_units(chassis_id, spot_id, mounted_visit_id) VALUES (?,?,NULL)",
            (f"CH{i:04d}", spot_id),
        )


def window_for(n: int) -> tuple[datetime, datetime, datetime]:
    day = n // 900
    slot = n % 900
    base = datetime(2026, 3, 2, 6, 0) + timedelta(days=day, minutes=slot)
    start_local = from_chicago(base.year, base.month, base.day, base.hour, base.minute)
    end_base = base + timedelta(minutes=90)
    end_local = from_chicago(end_base.year, end_base.month, end_base.day, end_base.hour, end_base.minute)
    gate_base = base + timedelta(minutes=15)
    gate_local = from_chicago(gate_base.year, gate_base.month, gate_base.day, gate_base.hour, gate_base.minute)
    return start_local, end_local, gate_local


def write_contracts(codes: list[str]) -> None:
    table: dict[str, dict[str, int]] = {}
    for idx, scac in enumerate(codes):
        live = 90 + (idx % 5) * 15
        drop = 1200 + (idx % 6) * 60
        table[scac] = {
            "LIVE_IN": live,
            "LIVE_OUT": live,
            "DROP_IN": drop,
            "EMPTY_OUT": 180,
            "LOADED_PICKUP": 240,
        }
    path = ROOT / "config" / "carrier_contracts.json"
    path.write_text(json.dumps(table, indent=2) + "\n", encoding="utf-8")


def occupancy_digest(con: sqlite3.Connection) -> str:
    rows = con.execute(
        "SELECT spot_id, occupant_visit_id, reserved_move_id FROM spots "
        "WHERE occupant_visit_id IS NOT NULL OR reserved_move_id IS NOT NULL ORDER BY spot_id"
    ).fetchall()
    lines: list[str] = []
    for spot_id, visit_id, reserved in rows:
        if visit_id:
            lines.append(f"{spot_id}={visit_id}")
        elif reserved:
            lines.append(f"{spot_id}=#{reserved}")
    blob = "".join(line + "\n" for line in lines).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


def seed_live(con: sqlite3.Connection, codes: list[str], journal_path: Path) -> tuple[int, list[str]]:
    events: list[dict] = []
    seq = 0
    open_ids: list[str] = []

    def push(event: dict) -> None:
        nonlocal seq
        seq += 1
        event["seq"] = seq
        event["accepted_at"] = event.get("at") or event.get("accepted_at")
        events.append(event)

    for n in range(VISIT_N):
        scac = codes[n % 72]
        trailer = f"U{n:06d}"
        vtype = visit_type_for(n)
        equipment = equipment_for(n, vtype)
        door_class = door_class_for(equipment, vtype)
        start_local, end_local, gate_local = window_for(n)
        gate_out_local = gate_local + timedelta(minutes=80 + (n % 40))
        appt_id = f"A{n:06d}"
        visit_id = f"V{n:06d}"
        event_in = f"E{n:06d}I"
        event_out = f"E{n:06d}O"
        is_open = n >= VISIT_N - OPEN_N
        open_index = n - (VISIT_N - OPEN_N)
        if vtype in {"LIVE_IN", "LIVE_OUT"}:
            if equipment == "REEFER_53":
                door_id = f"D{33 + (n % 8):02d}"
            elif door_class == "OUTBOUND":
                door_id = f"D{41 + (n % 8):02d}"
            else:
                door_id = f"D{1 + (n % 32):02d}"
            spot_id = "A" + door_id[1:]
            zone_state = "DOCKED"
            on_ground = 0
        else:
            door_id = None
            spot_id = f"L{(n % 400) + 1:04d}" if vtype == "DROP_IN" else f"S{(n % 200) + 1:04d}"
            zone_state = "ON_YARD"
            on_ground = 1 if vtype == "DROP_IN" else 0
        if is_open:
            if open_index < 48:
                door_id = f"D{open_index + 1:02d}"
                spot_id = f"A{open_index + 1:02d}"
                zone_state = "DOCKED"
                on_ground = 0
            else:
                door_id = None
                spot_id = f"L{open_index - 47:04d}"
                zone_state = "ON_YARD"
                on_ground = 1 if vtype == "DROP_IN" else 0
        con.execute(
            "INSERT INTO appointments(appointment_id, facility_id, scac, visit_type, door_class, "
            "trailer_number, window_start, window_end, door_id, status) VALUES (?,?,?,?,?,?,?,?,?,?)",
            (
                appt_id,
                FACILITY,
                scac,
                vtype,
                door_class,
                trailer if n % 17 else None,
                iso(start_local),
                iso(end_local),
                door_id,
                "CLAIMED",
            ),
        )
        seal = f"SL{n:06d}" if vtype in {"LIVE_IN", "LIVE_OUT", "LOADED_PICKUP"} else None
        state = zone_state if is_open else "CLOSED"
        if is_open and n % 20 == 0:
            state = "MOVING"
        con.execute(
            "INSERT INTO visits(visit_id, scac, trailer_number, visit_type, equipment, state, spot_id, door_id, "
            "appointment_id, gate_in, gate_out, seal, on_ground, chassis_id, clock_start) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                visit_id,
                scac,
                trailer,
                vtype,
                equipment,
                state,
                None if state == "MOVING" else spot_id,
                door_id if state == "DOCKED" else None,
                appt_id,
                iso(gate_local),
                None if is_open else iso(gate_out_local),
                seal,
                on_ground,
                None,
                iso(max(start_local, gate_local)) if vtype in {"LIVE_IN", "LIVE_OUT"} else iso(gate_local),
            ),
        )
        if is_open:
            open_ids.append(visit_id)
            if state in {"ON_YARD", "DOCKED"}:
                con.execute(
                    "UPDATE spots SET occupant_visit_id = ? WHERE spot_id = ?",
                    (visit_id, spot_id),
                )
        if state == "MOVING":
            dest = f"S{(n % 200) + 1:04d}"
            move_id = f"M{n:06d}"
            con.execute(
                "INSERT INTO moves(move_id, visit_id, state, origin_spot_id, dest_spot_id, event_id, seq) "
                "VALUES (?,?,?,?,?,?,?)",
                (move_id, visit_id, "IN_TRANSIT", spot_id, dest, f"E{n:06d}M", 0),
            )
            con.execute(
                "UPDATE spots SET reserved_move_id = ? WHERE spot_id = ?",
                (move_id, dest),
            )
        if n % 23 == 0 and not is_open:
            code = ("YARD_OSND", "YARD_SAFETY", "CARRIER_SEAL", "CARRIER_DOCS")[n % 4]
            placed = iso(gate_local + timedelta(minutes=10))
            released = iso(gate_local + timedelta(minutes=25))
            con.execute(
                "INSERT INTO holds(visit_id, hold_code, placed_at, released_at, active) VALUES (?,?,?,?,0)",
                (visit_id, code, placed, released),
            )
        if is_open and n % 11 == 0:
            code = ("YARD_OSND", "YARD_SAFETY", "CARRIER_SEAL", "CARRIER_DOCS")[n % 4]
            con.execute(
                "INSERT INTO holds(visit_id, hold_code, placed_at, released_at, active) VALUES (?,?,?,?,1)",
                (visit_id, code, iso(gate_local + timedelta(minutes=5)), None),
            )
        push(
            {
                "event_id": event_in,
                "verb": "gate-in",
                "scac": scac,
                "trailer": trailer,
                "visit_type": vtype,
                "equipment": equipment,
                "at": iso(gate_local),
                "appointment_id": appt_id,
                "spot_id": spot_id,
                "door_id": door_id,
                "seal": seal,
                "on_ground": on_ground,
                "visit_id": visit_id,
            }
        )
        if not is_open:
            push(
                {
                    "event_id": event_out,
                    "verb": "gate-out",
                    "visit_id": visit_id,
                    "at": iso(gate_out_local),
                    "seal": seal,
                }
            )
        else:
            pass

    leftover = VISIT_N
    for extra in range(600):
        n = leftover + extra
        scac = codes[n % 72]
        vtype = visit_type_for(n)
        equipment = equipment_for(n, vtype)
        start_local, end_local, _ = window_for(n % VISIT_N)
        con.execute(
            "INSERT INTO appointments(appointment_id, facility_id, scac, visit_type, door_class, "
            "trailer_number, window_start, window_end, door_id, status) VALUES (?,?,?,?,?,?,?,?,?,?)",
            (
                f"P{extra:06d}",
                FACILITY,
                scac,
                vtype,
                door_class_for(equipment, vtype),
                None,
                iso(start_local),
                iso(end_local),
                None,
                "OPEN",
            ),
        )

    journal_path.parent.mkdir(parents=True, exist_ok=True)
    with journal_path.open("w", encoding="utf-8") as handle:
        for event in events:
            handle.write(json.dumps(event, separators=(",", ":")))
            handle.write("\n")
    con.execute("UPDATE applied SET last_applied_seq = 1")
    con.execute("UPDATE applied SET last_applied_seq = ?", (seq,))
    return seq, sorted(open_ids)


def seed_warehouse(path: Path, codes: list[str]) -> None:
    con = connect(path)
    insert_catalog(con)
    for n in range(WAREHOUSE_N):
        scac = codes[n % 72]
        trailer = f"W{n:06d}"
        vtype = visit_type_for(n)
        equipment = equipment_for(n, vtype)
        start_local, end_local, gate_local = window_for(n % 900)
        gate_local = gate_local.replace(year=2025)
        visit_id = f"W{n:06d}"
        is_open = n < 20
        con.execute(
            "INSERT INTO visits(visit_id, scac, trailer_number, visit_type, equipment, state, spot_id, door_id, "
            "appointment_id, gate_in, gate_out, seal, on_ground, chassis_id, clock_start) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                visit_id,
                scac,
                trailer,
                vtype,
                equipment,
                "ON_YARD" if is_open else "CLOSED",
                f"L{(n % 400) + 1:04d}" if is_open else None,
                None,
                None,
                iso(gate_local),
                None if is_open else iso(gate_local + timedelta(hours=2)),
                f"WS{n:06d}",
                0,
                None,
                iso(gate_local),
            ),
        )
    con.commit()
    con.close()


def write_seed_sql(codes: list[str]) -> None:
    lines = [
        "-- Compact deterministic seed for authenticity checks. Runtime sqlite is built by cmd/seed.py.",
        "WITH RECURSIVE x(n) AS (SELECT 0 UNION ALL SELECT n+1 FROM x WHERE n < 125)",
        "INSERT INTO doors(door_id, door_class, reefer_plug, live_capable, drop_capable, allowed_equipment)",
        "SELECT printf('D%02d', n+1),",
        "  CASE WHEN n < 32 THEN 'DRY' WHEN n < 40 THEN 'REEFER' ELSE 'OUTBOUND' END,",
        "  CASE WHEN n >= 32 AND n < 40 THEN 1 ELSE 0 END,",
        "  1,",
        "  CASE WHEN n >= 40 THEN 1 ELSE 0 END,",
        "  CASE WHEN n < 32 THEN '[\"DRY_53\",\"TANK\"]' WHEN n < 40 THEN '[\"REEFER_53\"]' ELSE '[\"DRY_53\",\"CONTAINER_40\",\"TANK\"]' END",
        "FROM x WHERE n < 48;",
        "WITH RECURSIVE x(n) AS (SELECT 0 UNION ALL SELECT n+1 FROM x WHERE n < 125)",
        "INSERT INTO spots(spot_id, zone, door_id) SELECT printf('A%02d', n+1), 'DOCK_APRON', printf('D%02d', n+1) FROM x WHERE n < 48;",
        "WITH RECURSIVE x(n) AS (SELECT 0 UNION ALL SELECT n+1 FROM x WHERE n < 125)",
        "INSERT INTO spots(spot_id, zone) SELECT printf('L%04d', a.n + 126*b.n + 1), 'DROP_LOT' FROM x a CROSS JOIN x b WHERE a.n + 126*b.n < 400;",
        "WITH RECURSIVE x(n) AS (SELECT 0 UNION ALL SELECT n+1 FROM x WHERE n < 125)",
        "INSERT INTO spots(spot_id, zone) SELECT printf('S%04d', a.n + 126*b.n + 1), 'STAGING' FROM x a CROSS JOIN x b WHERE a.n + 126*b.n < 200;",
        "WITH RECURSIVE x(n) AS (SELECT 0 UNION ALL SELECT n+1 FROM x WHERE n < 125)",
        "INSERT INTO spots(spot_id, zone) SELECT printf('C%04d', n+1), 'CHASSIS_STACK' FROM x WHERE n < 72;",
        "WITH RECURSIVE x(n) AS (SELECT 0 UNION ALL SELECT n+1 FROM x WHERE n < 125)",
        "INSERT INTO chassis_units(chassis_id, spot_id) SELECT printf('CH%04d', n+1), printf('C%04d', n+1) FROM x WHERE n < 72;",
    ]
    scac_case = " CASE " + " ".join(
        f"WHEN n % 72 = {idx} THEN '{code}'" for idx, code in enumerate(codes)
    ) + " END"
    lines.append("WITH RECURSIVE x(n) AS (SELECT 0 UNION ALL SELECT n+1 FROM x WHERE n < 125)")
    lines.append(
        "INSERT INTO visits(visit_id, scac, trailer_number, visit_type, equipment, state, spot_id, door_id, "
        "appointment_id, gate_in, gate_out, seal, on_ground, chassis_id, clock_start)"
    )
    lines.append("SELECT")
    lines.append("  printf('V%06d', n),")
    lines.append(scac_case + ",")
    lines.append("  printf('U%06d', n),")
    lines.append(
        "  CASE WHEN n % 20 < 8 THEN 'LIVE_IN' WHEN n % 20 < 13 THEN 'DROP_IN' "
        "WHEN n % 20 < 17 THEN 'LIVE_OUT' WHEN n % 20 < 19 THEN 'EMPTY_OUT' ELSE 'LOADED_PICKUP' END,"
    )
    lines.append("  CASE n % 4 WHEN 0 THEN 'DRY_53' WHEN 1 THEN 'REEFER_53' WHEN 2 THEN 'TANK' ELSE 'CONTAINER_40' END,")
    lines.append("  CASE WHEN n >= 12500 THEN 'ON_YARD' ELSE 'CLOSED' END,")
    lines.append("  NULL, NULL, NULL,")
    lines.append("  datetime('2026-03-02T12:00:00Z', printf('+%d minutes', (n / 900) * 1440 + (n % 900))),")
    lines.append(
        "  CASE WHEN n >= 12500 THEN NULL ELSE datetime('2026-03-02T12:00:00Z', printf('+%d minutes', (n / 900) * 1440 + (n % 900) + 90)) END,"
    )
    lines.append("  printf('SL%06d', n), 0, NULL,")
    lines.append("  datetime('2026-03-02T12:00:00Z', printf('+%d minutes', (n / 900) * 1440 + (n % 900)))")
    lines.append("FROM (SELECT a.n + 126 * b.n AS n FROM x a CROSS JOIN x b) WHERE n < 12600;")
    (ROOT / "sql" / "seed.sql").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_ops(seq: int, open_ids: list[str], digest: str) -> None:
    log = ROOT / "logs" / "gate-desk.log"
    log.parent.mkdir(parents=True, exist_ok=True)
    log.write_text(
        "\n".join(
            [
                "DC-AUR-01 gate desk 2026-03-15 shift close",
                f"journal_head_seq={seq}",
                f"open_visits={len(open_ids)}",
                f"occupancy_digest={digest}",
                "prior_cycle warehouse remains at warehouse/prior_cycle.sqlite",
                "America/Chicago civil clocks including 2026-03-08 spring-forward are in the appointment book",
                "",
            ]
        ),
        encoding="utf-8",
    )
    handoff = ROOT / "ops" / "handoff.txt"
    handoff.parent.mkdir(parents=True, exist_ok=True)
    handoff.write_text(
        "\n".join(
            [
                "Yard desk handoff DC-AUR-01",
                f"Open visits: {len(open_ids)}",
                f"First open: {open_ids[0] if open_ids else 'none'}",
                f"Last open: {open_ids[-1] if open_ids else 'none'}",
                "Carrier QXRT has no free-time contract row.",
                "Publish snapshot/detention/health through yardctl; do not mix prior-cycle warehouse rows.",
                "",
            ]
        ),
        encoding="utf-8",
    )


def main() -> int:
    print("seeding yard...", flush=True)
    cfg = json.loads((ROOT / "config" / "yard.json").read_text(encoding="utf-8"))
    codes = scacs()
    write_contracts(codes)
    sqlite_path = ROOT / cfg["paths"]["sqlite"]
    journal_path = ROOT / cfg["paths"]["journal"]
    checkpoint_path = ROOT / cfg["paths"]["checkpoint"]
    warehouse_path = ROOT / cfg["paths"]["warehouse"]
    con = connect(sqlite_path)
    insert_catalog(con)
    seq, open_ids = seed_live(con, codes, journal_path)
    digest = occupancy_digest(con)
    con.commit()
    con.close()
    checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
    checkpoint_path.write_text(
        json.dumps(
            {
                "last_applied_seq": seq,
                "open_visit_ids": open_ids,
                "occupancy_digest": digest,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    seed_warehouse(warehouse_path, codes)
    write_seed_sql(codes)
    write_ops(seq, open_ids, digest)
    for rel in ("out/snapshot.json", "out/moves.jsonl", "out/detention.jsonl", "out/rejects.jsonl", "out/health.json"):
        path = ROOT / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            path.write_text("", encoding="utf-8")
    print(f"seeded visits={VISIT_N} journal_seq={seq} open={len(open_ids)}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
