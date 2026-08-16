from __future__ import annotations

from decimal import Decimal
from hashlib import sha256
import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
from typing import Callable

import pytest

ROOT = Path(os.environ.get("EQUIV_ROOT", "/app/equiv"))
sys.path.insert(0, str(ROOT))

from src.accounting import apply_effect, issue_effect, transfer_effect
from src.checkpoint import resume_sequence, validate_checkpoint
from src.comp3 import PackedSpec, pack, unpack
from src.database import apply_sql, connect, seed_inventory
from src.event_journal import ensure_table as ensure_journal_table
from src.framing import RecordDecodeError, decode_record, iter_records
from src.generation import assert_resume_compatible, build_identity, generation_id
from src.layout import Field, Layout, active_occurs, resolve_offsets
from src.models import (
    Checkpoint,
    GenerationIdentity,
    InventoryEffect,
    InventoryPosition,
    Movement,
    MovementType,
    ReconciliationControl,
    ReconciliationResult,
)
from src.pipeline import PipelineConfig, process
from src.policy import (
    ItemPolicy,
    WarehousePolicy,
    validate_item,
    validate_shape,
    validate_warehouses,
)
from src.publication import atomic_publish
from src.reconciliation import reconcile
from src.reconciliation_detail import findings as reconciliation_findings

SCHEMA = ROOT / "sql" / "schema.sql"
SEED = ROOT / "sql" / "seed.sql"
DEFAULT_LAYOUT = ROOT / "config" / "movement.layout.json"


def identity(
    *,
    gid: str = "g",
    source: str = "s",
    layout: str = "l",
    date: str = "20260815",
) -> GenerationIdentity:
    return GenerationIdentity(gid, "source.dat", 10, source, layout, date)


def movement(
    *,
    movement_id: str = "MOVE00000001",
    sequence: int = 1,
    movement_type: MovementType = MovementType.RECEIPT,
    item_id: str = "SKU00001",
    source: str | None = None,
    destination: str | None = "W01",
    quantity: str = "1.000",
    unit_cost: str = "10.00",
    reason: str = "PO",
    gid: str = "g",
) -> Movement:
    return Movement(
        movement_id,
        sequence,
        movement_type,
        item_id,
        source,
        destination,
        Decimal(quantity),
        Decimal(unit_cost),
        "20260815",
        reason,
        gid,
    )


def fresh_db(tmp_path: Path) -> sqlite3.Connection:
    db = connect(tmp_path / "state.db")
    apply_sql(db, SCHEMA)
    return db


def reference_comp3(
    value: str,
    digits: int,
    scale: int = 0,
    sign: int = 0xF,
) -> bytes:
    number = Decimal(value).copy_abs().quantize(Decimal(1).scaleb(-scale))
    scaled = int(number.scaleb(scale))
    body = [int(ch) for ch in f"{scaled:0{digits}d}"] + [sign]
    if len(body) % 2:
        body.insert(0, 0)
    return bytes((body[i] << 4) | body[i + 1] for i in range(0, len(body), 2))


def reference_record(
    *,
    movement_id: str = "MOVE00000001",
    sequence: int = 1,
    type_code: str = "R",
    item_id: str = "SKU00001",
    source: str | None = None,
    destination: str | None = "W01",
    quantity: str = "1.000",
    unit_cost: str = "10.00",
    effective_date: str = "20260815",
    reason: str = "PO",
    attr_values: tuple[str, ...] = (),
) -> bytes:
    attrs = b"".join(value.ljust(4)[:4].encode("ascii") for value in attr_values)
    return b"".join(
        [
            movement_id.ljust(12)[:12].encode("ascii"),
            reference_comp3(str(sequence), 6),
            type_code.encode("ascii"),
            item_id.ljust(8)[:8].encode("ascii"),
            (source or "").ljust(3)[:3].encode("ascii"),
            (destination or "").ljust(3)[:3].encode("ascii"),
            reference_comp3(quantity, 10, 3),
            reference_comp3(unit_cost, 9, 2),
            effective_date.ljust(8)[:8].encode("ascii"),
            reason.ljust(6)[:6].encode("ascii"),
            reference_comp3(str(len(attr_values)), 1),
            attrs,
        ]
    )


def reference_receipt_record() -> bytes:
    return reference_record()


def write_controls(
    path: Path,
    *,
    processed: str = "1",
    accepted: str = "1",
    rejected: str = "0",
    effects: str = "1",
    quantity: str = "1.000",
    value: str = "10.00",
) -> None:
    path.write_text(
        "\n".join(
            [
                f"processed_count={processed}",
                f"accepted_count={accepted}",
                f"rejected_count={rejected}",
                f"effect_count={effects}",
                f"net_quantity={quantity}",
                f"net_value={value}",
                "",
            ]
        ),
        encoding="utf-8",
    )


def passing_reconciliation(gid: str = "g") -> ReconciliationResult:
    return ReconciliationResult(
        gid,
        [ReconciliationControl("ok", Decimal("1"), Decimal("1"))],
    )


def failing_reconciliation(gid: str = "g") -> ReconciliationResult:
    return ReconciliationResult(
        gid,
        [ReconciliationControl("bad", Decimal("1"), Decimal("0"))],
    )


def must_reject(action: Callable[[], object]) -> None:
    try:
        action()
    except Exception:
        return
    pytest.fail("invalid operation was accepted")


def file_digest(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(65536), b""):
            digest.update(block)
    return digest.hexdigest()


def cli(*args: object) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT)
    return subprocess.run(
        [sys.executable, str(ROOT / "bin" / "equiv-eval"), *[str(arg) for arg in args]],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )


def parse_stdout(result: subprocess.CompletedProcess[str]) -> dict[str, object]:
    assert result.stdout.strip()
    payload = json.loads(result.stdout)
    assert isinstance(payload, dict)
    return payload


def parse_stderr(result: subprocess.CompletedProcess[str]) -> dict[str, object]:
    assert result.stderr.strip()
    payload = json.loads(result.stderr)
    assert isinstance(payload, dict)
    return payload


def run_arguments(
    db_path: Path,
    source: Path,
    layout: Path,
    controls: Path,
    report_dir: Path,
    publish_dir: Path,
) -> list[str]:
    return [
        "--db",
        str(db_path),
        "--source",
        str(source),
        "--layout",
        str(layout),
        "--business-date",
        "20260815",
        "--legacy-controls",
        str(controls),
        "--report-dir",
        str(report_dir),
        "--publish-dir",
        str(publish_dir),
    ]



def write_alternate_layout(tmp_path: Path) -> Path:
    alternate = json.loads(DEFAULT_LAYOUT.read_text(encoding="utf-8"))
    alternate["layout_id"] = "ALT-CALLER-LAYOUT"
    alternate["version"] = 91
    alternate["fields"].append({"name": "CALLER-TRAILER", "picture": "X(1)"})
    path = tmp_path / "alternate-layout.json"
    path.write_text(json.dumps(alternate), encoding="utf-8")
    return path


def visible_generation_dirs(root: Path) -> list[Path]:
    if not root.exists():
        return []
    return sorted(
        path for path in root.iterdir()
        if path.is_dir() and not path.name.startswith(".")
    )


def nested_mappings(value: object):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from nested_mappings(child)
    elif isinstance(value, list):
        for child in value:
            yield from nested_mappings(child)


def find_publication_manifest(target: Path, generation_id_value: str) -> Path:
    files = [path for path in target.iterdir() if path.is_file()]
    digests = {path: file_digest(path) for path in files}
    for candidate in files:
        if candidate.suffix.lower() != ".json":
            continue
        try:
            payload = json.loads(candidate.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        rendered = json.dumps(payload, sort_keys=True, default=str)
        if generation_id_value not in rendered:
            continue
        if any(
            digest in rendered
            for path, digest in digests.items()
            if path != candidate
        ):
            return candidate
    pytest.fail("publication lacks independently discoverable generation/integrity manifest")


def persisted_reject_code(
    tmp_path: Path,
    raw: bytes,
    prepare: Callable[[sqlite3.Connection], None] | None = None,
) -> str:
    db = fresh_db(tmp_path)
    seed_inventory(db, warehouse_count=2, item_count=2)
    if prepare is not None:
        prepare(db)
    db.commit()
    db.close()
    db_path = tmp_path / "state.db"
    source = tmp_path / "source.dat"
    source.write_bytes(raw)
    controls = tmp_path / "legacy.controls"
    write_controls(
        controls,
        processed="1",
        accepted="0",
        rejected="1",
        effects="0",
        quantity="0",
        value="0",
    )
    report_dir = tmp_path / "ops" / "reports"
    result = cli(
        "run",
        *run_arguments(
            db_path,
            source,
            DEFAULT_LAYOUT,
            controls,
            report_dir,
            tmp_path / "published",
        ),
    )
    assert result.returncode == 0
    db = connect(db_path)
    row = db.execute("SELECT code FROM rejects ORDER BY id").fetchone()
    db.close()
    assert row is not None
    persisted = str(row[0])
    csv_blob = "\n".join(
        path.read_text(encoding="utf-8")
        for path in report_dir.rglob("*.csv")
    )
    assert persisted in csv_blob
    return persisted


def assert_publication_contract(
    target: Path,
    generation_id_value: str,
    expected_files: dict[str, Path],
) -> None:
    assert target.is_dir()
    manifest = find_publication_manifest(target, generation_id_value)
    manifest_text = manifest.read_text(encoding="utf-8")
    assert generation_id_value in manifest_text
    published_files = [
        path for path in target.iterdir()
        if path.is_file() and path != manifest
    ]
    for source in expected_files.values():
        assert any(path.read_bytes() == source.read_bytes() for path in published_files)
        assert file_digest(source) in manifest_text

def test_f2p_nonzero_comp3_padding_is_rejected() -> None:
    must_reject(lambda: unpack(bytes.fromhex("11234c"), PackedSpec(4, 0, True)))


def test_f2p_invalid_comp3_digit_nibble_a_is_rejected() -> None:
    must_reject(lambda: unpack(bytes.fromhex("012a3c"), PackedSpec(4, 0, True)))


def test_f2p_signed_comp3_rejects_unsigned_f_sign() -> None:
    must_reject(lambda: unpack(bytes.fromhex("01234f"), PackedSpec(4, 0, True)))


def test_f2p_unsigned_comp3_rejects_signed_c_sign() -> None:
    must_reject(lambda: unpack(bytes.fromhex("01234c"), PackedSpec(4, 0, False)))


def test_f2p_unsigned_pack_uses_f_and_rejects_negative() -> None:
    spec = PackedSpec(4, 0, False)
    assert pack(Decimal("1234"), spec)[-1] & 0x0F == 0x0F
    must_reject(lambda: pack(Decimal("-1"), spec))


def test_f2p_signed_negative_pack_uses_d_sign() -> None:
    encoded = pack(Decimal("-1234"), PackedSpec(4, 0, True))
    assert encoded[-1] & 0x0F == 0x0D


def test_f2p_redefines_does_not_increase_static_storage() -> None:
    layout = Layout(
        "R",
        [
            Field("A", "X(4)"),
            Field("B", "X(4)", redefines="A"),
            Field("C", "X(2)"),
        ],
    )
    assert layout.static_min_length() == 6



def test_f2p_caller_supplied_layout_path_is_honored(tmp_path: Path) -> None:
    layout_path = write_alternate_layout(tmp_path)
    db = fresh_db(tmp_path)
    seed_inventory(db, warehouse_count=2, item_count=2)
    apply_sql(db, SEED)
    db.close()
    db_path = tmp_path / "state.db"
    source = tmp_path / "caller-source.dat"
    source.write_bytes(reference_receipt_record() + b"Z")
    second_source = tmp_path / "caller-source-2.dat"
    second_source.write_bytes(reference_record(movement_id="MOVE00000002") + b"Z")
    controls = tmp_path / "legacy.controls"
    write_controls(controls)
    report_dir = tmp_path / "ops" / "reports"
    publish_dir = tmp_path / "published"

    described = cli("describe-layout", "--layout", layout_path)
    baseline_description = cli("describe-layout", "--layout", DEFAULT_LAYOUT)
    assert described.returncode == baseline_description.returncode == 0
    assert parse_stdout(described) != parse_stdout(baseline_description)

    identified = cli(
        "identity",
        "--source", source,
        "--layout", layout_path,
        "--business-date", "20260815",
    )
    other_layout = cli(
        "identity",
        "--source", source,
        "--layout", DEFAULT_LAYOUT,
        "--business-date", "20260815",
    )
    other_source = cli(
        "identity",
        "--source", second_source,
        "--layout", layout_path,
        "--business-date", "20260815",
    )
    assert identified.returncode == other_layout.returncode == other_source.returncode == 0
    assert parse_stdout(identified) != parse_stdout(other_layout)
    assert parse_stdout(identified) != parse_stdout(other_source)

    preflight = cli(
        "preflight",
        *run_arguments(db_path, source, layout_path, controls, report_dir, publish_dir),
        "--schema", SCHEMA,
        "--seed", SEED,
    )
    assert preflight.returncode == 0
    assert parse_stdout(preflight).get("passed") is True

    empty_catalog_db = tmp_path / "empty-catalog.db"
    shutil.copyfile(db_path, empty_catalog_db)
    catalog_db = connect(empty_catalog_db)
    catalog_db.execute("DELETE FROM inventory_positions")
    catalog_db.execute("DELETE FROM items")
    catalog_db.execute("DELETE FROM warehouses")
    catalog_db.commit()
    catalog_db.close()
    unhealthy_catalog = cli(
        "preflight",
        *run_arguments(
            empty_catalog_db, source, layout_path, controls, report_dir, publish_dir
        ),
        "--schema", SCHEMA,
        "--seed", SEED,
    )
    assert unhealthy_catalog.returncode == 2
    assert parse_stdout(unhealthy_catalog).get("passed") is False

    schema_bad_db = tmp_path / "schema-bad.db"
    shutil.copyfile(db_path, schema_bad_db)
    schema_state = sqlite3.connect(schema_bad_db)
    schema_state.executescript(
        """
        DROP TABLE rejects;
        CREATE TABLE rejects(
          id INTEGER PRIMARY KEY AUTOINCREMENT, generation_id TEXT NOT NULL,
          sequence INTEGER NOT NULL, movement_id TEXT NOT NULL, code TEXT NOT NULL,
          message TEXT NOT NULL, byte_offset INTEGER NOT NULL, byte_length INTEGER NOT NULL
        );
        """
    )
    schema_state.commit()
    schema_state.close()
    unhealthy_schema = cli(
        "preflight",
        *run_arguments(
            schema_bad_db, source, layout_path, controls, report_dir, publish_dir
        ),
        "--schema", SCHEMA,
        "--seed", SEED,
    )
    assert unhealthy_schema.returncode == 2
    assert parse_stdout(unhealthy_schema).get("passed") is False

    framing_source = tmp_path / "framing-bad.dat"
    framing_source.write_bytes(reference_receipt_record() + b"ZZ")
    unhealthy_source = cli(
        "preflight",
        *run_arguments(
            db_path, framing_source, layout_path, controls, report_dir, publish_dir
        ),
        "--schema", SCHEMA,
        "--seed", SEED,
    )
    assert unhealthy_source.returncode == 2
    assert parse_stdout(unhealthy_source).get("passed") is False

    window_arguments = run_arguments(
        db_path, source, layout_path, controls, report_dir, publish_dir
    )
    window_arguments[window_arguments.index("--business-date") + 1] = "20991231"
    window_probe = cli(
        "preflight",
        *window_arguments,
        "--schema", SCHEMA,
        "--seed", SEED,
    )
    assert window_probe.returncode in {0, 2}
    assert parse_stdout(window_probe) != parse_stdout(preflight)

    safety_state_db = tmp_path / "safety-state.db"
    shutil.copyfile(db_path, safety_state_db)
    safety_db = connect(safety_state_db)
    safety_gid = build_identity(source, layout_path, "20260815").generation_id
    safety_db.execute(
        "INSERT INTO runs(generation_id,state) VALUES(?,?)",
        (safety_gid, "PUBLISHED"),
    )
    safety_db.commit()
    safety_db.close()
    safety_probe = cli(
        "preflight",
        *run_arguments(
            safety_state_db, source, layout_path, controls, report_dir, publish_dir
        ),
        "--schema", SCHEMA,
        "--seed", SEED,
    )
    assert safety_probe.returncode in {0, 2}
    assert parse_stdout(safety_probe) != parse_stdout(preflight)

    blocked_recovery_db = tmp_path / "blocked-recovery.db"
    shutil.copyfile(db_path, blocked_recovery_db)
    recovery_db = connect(blocked_recovery_db)
    gid = build_identity(source, layout_path, "20260815").generation_id
    recovery_db.execute(
        "INSERT INTO runs(generation_id,state) VALUES(?,?)",
        (gid, "PROCESSING"),
    )
    recovery_db.execute(
        "INSERT INTO checkpoints"
        "(generation_id,last_sequence,byte_offset,source_fingerprint,updated_at)"
        " VALUES(?,?,?,?,?)",
        (gid, 1, 0, "mismatched:fingerprint", "now"),
    )
    recovery_db.commit()
    recovery_db.close()
    blocked_recovery = cli(
        "preflight",
        *run_arguments(
            blocked_recovery_db, source, layout_path, controls, report_dir, publish_dir
        ),
        "--schema", SCHEMA,
        "--seed", SEED,
    )
    assert blocked_recovery.returncode == 2
    assert parse_stdout(blocked_recovery).get("passed") is False

    missing_layout = cli("describe-layout", "--layout", tmp_path / "missing-layout.json")
    assert missing_layout.returncode == 2
    assert missing_layout.stdout == ""
    assert isinstance(parse_stderr(missing_layout).get("error"), dict)

    run = cli(
        "run",
        *run_arguments(db_path, source, layout_path, controls, report_dir, publish_dir),
    )
    assert run.returncode == 0
    run_db = connect(db_path)
    assert run_db.execute("SELECT COUNT(*) FROM processed_movements").fetchone()[0] == 1
    run_db.close()
    assert len(visible_generation_dirs(publish_dir)) == 1

    operator_root = tmp_path / "operator-workflows"
    operator_root.mkdir()
    exercise_adjudicated_operator_workflows(operator_root)


def test_f2p_odo_count_above_declared_maximum_is_rejected() -> None:
    layout = Layout(
        "ODO",
        [
            Field("N", "9(1)", usage="COMP-3"),
            Field("ATTR", "X(2)", occurs=3, depending_on="N"),
            Field("TAIL", "X(1)"),
        ],
    )
    decoded = decode_record(
        layout,
        reference_comp3("2", 1) + b"AABB" + b"Z",
    )
    assert decoded.values["N"] == Decimal("2")
    assert decoded.values["ATTR"] == ["AA", "BB"]
    assert decoded.values["TAIL"] == "Z"

    too_many = reference_comp3("4", 1) + b"AABBCCDD" + b"Z"
    must_reject(lambda: decode_record(layout, too_many))
    must_reject(
        lambda: active_occurs(
            Field("ATTR", "X(2)", occurs=3, depending_on="N"),
            {"N": Decimal("-1")},
        )
    )


def test_f2p_redefines_offset_overlaps_target_without_cursor_advance() -> None:
    layout = Layout(
        "R",
        [
            Field("A", "X(4)"),
            Field("B", "X(4)", redefines="A"),
            Field("C", "X(2)"),
        ],
    )
    offsets = resolve_offsets(layout)
    assert offsets["A"] == (0, 4)
    assert offsets["B"] == (0, 4)
    assert offsets["C"] == (4, 2)


def test_f2p_complete_malformed_record_reports_full_boundary() -> None:
    layout = Layout("M", [Field("N", "9(2)", usage="COMP-3"), Field("TAIL", "X(4)")])
    raw = bytes.fromhex("0a1f") + b"TAIL"
    try:
        decode_record(layout, raw, 10)
    except RecordDecodeError as caught:
        assert caught.offset == 10
        assert caught.length == 6
    else:
        pytest.fail("malformed complete record was accepted")

    indeterminate_layout = Layout(
        "I",
        [
            Field("N", "9(1)", usage="COMP-3"),
            Field("ATTR", "X(2)", occurs=3, depending_on="N"),
            Field("TAIL", "X(1)"),
        ],
    )
    rows = list(iter_records(indeterminate_layout, reference_comp3("2", 1)))
    assert len(rows) == 1
    assert isinstance(rows[0], RecordDecodeError)
    assert rows[0].offset == 0
    assert rows[0].length == 0


def test_f2p_generation_id_binds_layout_digest() -> None:
    baseline = generation_id("source-a", "layout-a", "20260815")
    assert baseline != generation_id("source-a", "layout-b", "20260815")
    assert baseline != generation_id("source-b", "layout-a", "20260815")
    assert baseline != generation_id("source-a", "layout-a", "20260816")


def test_f2p_resume_rejects_layout_change() -> None:
    must_reject(
        lambda: assert_resume_compatible(
            identity(gid="same", layout="layout-a"),
            identity(gid="same", layout="layout-b"),
        )
    )
    must_reject(
        lambda: assert_resume_compatible(
            identity(gid="same", source="source-a"),
            identity(gid="same", source="source-b"),
        )
    )
    must_reject(
        lambda: assert_resume_compatible(
            identity(gid="same", date="20260815"),
            identity(gid="same", date="20260816"),
        )
    )


def test_f2p_checkpoint_fingerprint_mismatch_is_rejected() -> None:
    ident = identity(gid="g1", source="s1", layout="l1")
    must_reject(
        lambda: validate_checkpoint(
            ident,
            Checkpoint("g1", 2, 100, "wrong:fingerprint", "now"),
        )
    )


def test_f2p_resume_starts_after_last_durable_sequence() -> None:
    ident = identity(gid="g1")
    cp = Checkpoint("g1", 7, 100, ident.fingerprint(), "now")
    assert resume_sequence(ident, cp) == 8



def test_f2p_pipeline_restart_does_not_reapply_last_movement(tmp_path: Path) -> None:
    db = fresh_db(tmp_path)
    seed_inventory(db, warehouse_count=2, item_count=2)
    source = tmp_path / "source.dat"
    source.write_bytes(reference_receipt_record())
    controls = tmp_path / "legacy.controls"
    write_controls(controls)
    publish_root = tmp_path / "published"
    cfg = PipelineConfig(
        source,
        DEFAULT_LAYOUT,
        "20260815",
        controls,
        tmp_path / "reports",
        publish_root,
    )
    process(db, cfg)
    gid = db.execute("SELECT generation_id FROM runs").fetchone()[0]
    assert (publish_root / gid).is_dir()
    process(db, cfg)
    assert db.execute(
        "SELECT COUNT(*) FROM processed_movements WHERE generation_id=?",
        (gid,),
    ).fetchone()[0] == 1
    assert db.execute(
        "SELECT COUNT(*) FROM inventory_effects WHERE generation_id=?",
        (gid,),
    ).fetchone()[0] == 1
    assert (publish_root / gid).is_dir()


def test_f2p_zero_quantity_is_rejected(tmp_path: Path) -> None:
    assert persisted_reject_code(
        tmp_path,
        reference_record(quantity="0.000"),
    ) == "QUANTITY"
    assert validate_shape(movement(reason="SALE"))


def test_f2p_same_warehouse_transfer_is_rejected(tmp_path: Path) -> None:
    assert persisted_reject_code(
        tmp_path,
        reference_record(
            type_code="T",
            source="W01",
            destination="W01",
            reason="MOVE",
        ),
    ) == "TRANSFER_LOOP"


def test_f2p_inactive_item_is_rejected(tmp_path: Path) -> None:
    def disable_item(db: sqlite3.Connection) -> None:
        db.execute("UPDATE items SET active=0 WHERE item_id='SKU00001'")

    assert persisted_reject_code(
        tmp_path,
        reference_receipt_record(),
        disable_item,
    ) == "ITEM_INACTIVE"


def test_f2p_inactive_warehouse_is_rejected(tmp_path: Path) -> None:
    def disable_warehouse(db: sqlite3.Connection) -> None:
        db.execute("UPDATE warehouses SET active=0 WHERE warehouse_id='W01'")

    assert persisted_reject_code(
        tmp_path,
        reference_receipt_record(),
        disable_warehouse,
    ) == "WAREHOUSE_INACTIVE"


def test_f2p_issue_requires_full_available_quantity(tmp_path: Path) -> None:
    m = movement(
        movement_type=MovementType.ISSUE,
        source="W01",
        destination=None,
        quantity="6",
        reason="SALE",
    )
    must_reject(
        lambda: issue_effect(
            m,
            InventoryPosition("W01", "SKU00001", Decimal("5"), Decimal("25")),
        )
    )

    db = fresh_db(tmp_path)
    seed_inventory(db, warehouse_count=2, item_count=2)
    source = tmp_path / "issue.dat"
    source.write_bytes(
        reference_record(
            type_code="I",
            source="W01",
            destination=None,
            quantity="103.000",
            unit_cost="10.00",
            reason="SALE",
        )
    )
    controls = tmp_path / "legacy.controls"
    write_controls(
        controls,
        processed="0",
        accepted="0",
        rejected="0",
        effects="0",
        quantity="0",
        value="0",
    )
    process(
        db,
        PipelineConfig(
            source,
            DEFAULT_LAYOUT,
            "20260815",
            controls,
            tmp_path / "reports",
            tmp_path / "published",
        ),
    )
    row = db.execute("SELECT code FROM rejects ORDER BY id").fetchone()
    assert row is not None
    assert row[0] == "ACCOUNTING"


def test_f2p_issue_uses_weighted_source_unit_cost() -> None:
    m = movement(
        movement_type=MovementType.ISSUE,
        source="W01",
        destination=None,
        quantity="2",
        unit_cost="99",
        reason="SALE",
    )
    effect = issue_effect(
        m,
        InventoryPosition("W01", "SKU00001", Decimal("10"), Decimal("50")),
    )[0]
    assert effect.value_delta == Decimal("-10.00")


def test_f2p_transfer_preserves_source_value_across_warehouses() -> None:
    m = movement(
        movement_type=MovementType.TRANSFER,
        source="W01",
        destination="W02",
        quantity="2",
        unit_cost="99",
        reason="MOVE",
    )
    effects = transfer_effect(
        m,
        InventoryPosition("W01", "SKU00001", Decimal("10"), Decimal("50")),
    )
    assert sum((e.value_delta for e in effects), Decimal("0")) == Decimal("0")


def test_f2p_effect_application_rejects_negative_inventory() -> None:
    pos = InventoryPosition(
        "W01",
        "SKU00001",
        Decimal("1"),
        Decimal("10"),
    )
    effect = InventoryEffect(
        "M",
        "W01",
        "SKU00001",
        Decimal("-2"),
        Decimal("-20"),
        "ISSUE",
        1,
    )
    must_reject(lambda: apply_effect(pos, effect))


def test_f2p_reconciliation_checks_legacy_effect_count(tmp_path: Path) -> None:
    db = fresh_db(tmp_path)
    db.execute(
        "INSERT INTO processed_movements"
        "(generation_id,movement_id,sequence,status,item_id,movement_type,quantity,unit_cost)"
        " VALUES('g','m1',1,'ACCEPTED','SKU00001','RECEIPT','1','10')"
    )
    db.execute(
        "INSERT INTO inventory_effects"
        "(generation_id,movement_id,sequence,warehouse_id,item_id,quantity_delta,value_delta,effect_kind)"
        " VALUES('g','m1',1,'W01','SKU00001','1','10','RECEIPT')"
    )
    db.commit()
    exact = {
        "processed_count": Decimal("1"),
        "accepted_count": Decimal("1"),
        "rejected_count": Decimal("0"),
        "effect_count": Decimal("1"),
        "net_quantity": Decimal("1"),
        "net_value": Decimal("10"),
    }
    assert reconcile(db, "g", exact).passed

    mismatches = {
        "processed_count": Decimal("2"),
        "accepted_count": Decimal("2"),
        "rejected_count": Decimal("1"),
        "effect_count": Decimal("2"),
        "net_quantity": Decimal("1.0002"),
        "net_value": Decimal("10.02"),
    }
    for name, wrong in mismatches.items():
        expected = dict(exact)
        expected[name] = wrong
        result = reconcile(db, "g", expected)
        control = next(row for row in result.controls if row.name == name)
        assert not result.passed
        assert not control.passed

    within_quantity = dict(exact)
    within_quantity["net_quantity"] = Decimal("1.00005")
    assert reconcile(db, "g", within_quantity).passed
    within_value = dict(exact)
    within_value["net_value"] = Decimal("10.005")
    assert reconcile(db, "g", within_value).passed


def test_f2p_reconciliation_rejects_unbalanced_transfer(tmp_path: Path) -> None:
    db = fresh_db(tmp_path)
    db.execute(
        "INSERT INTO processed_movements"
        "(generation_id,movement_id,sequence,status,item_id,movement_type,quantity,unit_cost)"
        " VALUES('g','m',1,'ACCEPTED','SKU00001','TRANSFER','1','10')"
    )
    db.execute(
        "INSERT INTO inventory_effects"
        "(generation_id,movement_id,sequence,warehouse_id,item_id,quantity_delta,value_delta,effect_kind)"
        " VALUES('g','m',1,'W01','SKU00001','-1','-10','TRANSFER_OUT')"
    )
    db.execute(
        "INSERT INTO inventory_effects"
        "(generation_id,movement_id,sequence,warehouse_id,item_id,quantity_delta,value_delta,effect_kind)"
        " VALUES('g','m',1,'W02','SKU00001','1','9','TRANSFER_IN')"
    )
    db.commit()
    legacy = {
        "processed_count": Decimal("1"),
        "accepted_count": Decimal("1"),
        "rejected_count": Decimal("0"),
        "effect_count": Decimal("2"),
        "net_quantity": Decimal("0"),
        "net_value": Decimal("-1"),
    }
    result = reconcile(db, "g", legacy)
    assert not result.passed
    assert any(
        row.expected == Decimal("0") and row.actual != Decimal("0")
        for row in result.controls
    )
    assert reconciliation_findings(db, "g")

    permissive = sqlite3.connect(":memory:")
    permissive.executescript(
        """
        CREATE TABLE processed_movements(
          generation_id TEXT,movement_id TEXT,sequence INTEGER,status TEXT,
          item_id TEXT,movement_type TEXT,quantity TEXT,unit_cost TEXT
        );
        CREATE TABLE inventory_effects(
          id INTEGER PRIMARY KEY AUTOINCREMENT,generation_id TEXT,movement_id TEXT,
          sequence INTEGER,warehouse_id TEXT,item_id TEXT,quantity_delta TEXT,
          value_delta TEXT,effect_kind TEXT
        );
        CREATE TABLE rejects(
          id INTEGER PRIMARY KEY AUTOINCREMENT,generation_id TEXT,sequence INTEGER,
          movement_id TEXT,code TEXT,message TEXT,byte_offset INTEGER,byte_length INTEGER
        );
        CREATE TABLE inventory_positions(
          warehouse_id TEXT,item_id TEXT,quantity TEXT,value TEXT,version INTEGER
        );
        """
    )
    permissive.execute(
        "INSERT INTO processed_movements VALUES"
        "('g','dup',1,'ACCEPTED','SKU00001','RECEIPT','1','10')"
    )
    permissive.execute(
        "INSERT INTO processed_movements VALUES"
        "('g','dup',2,'ACCEPTED','SKU00001','RECEIPT','1','10')"
    )
    permissive.execute(
        "INSERT INTO inventory_effects"
        "(generation_id,movement_id,sequence,warehouse_id,item_id,quantity_delta,value_delta,effect_kind)"
        " VALUES('g','orphan',3,'W01','SKU00001','1','10','RECEIPT')"
    )
    permissive.commit()
    permissive_legacy = {
        "processed_count": Decimal("2"),
        "accepted_count": Decimal("2"),
        "rejected_count": Decimal("0"),
        "effect_count": Decimal("1"),
        "net_quantity": Decimal("1"),
        "net_value": Decimal("10"),
    }
    safety_result = reconcile(permissive, "g", permissive_legacy)
    assert not safety_result.passed
    failed_safety = [
        row
        for row in safety_result.controls
        if row.expected == Decimal("0") and row.actual != Decimal("0")
    ]
    assert len(failed_safety) >= 2
    assert reconciliation_findings(permissive, "g")



def test_f2p_failed_reconciliation_cannot_publish(tmp_path: Path) -> None:
    mismatch_root = tmp_path / "legacy-mismatch"
    mismatch_root.mkdir()
    db = fresh_db(mismatch_root)
    seed_inventory(db, warehouse_count=2, item_count=2)
    db.close()
    source = mismatch_root / "source.dat"
    source.write_bytes(reference_receipt_record())
    controls = mismatch_root / "legacy.controls"
    write_controls(controls, effects="2")
    report_dir = mismatch_root / "ops" / "reports"
    publish_dir = mismatch_root / "published"
    result = cli(
        "run",
        *run_arguments(
            mismatch_root / "state.db",
            source,
            DEFAULT_LAYOUT,
            controls,
            report_dir,
            publish_dir,
        ),
    )
    assert result.returncode == 2
    assert visible_generation_dirs(publish_dir) == []
    mismatch_db = connect(mismatch_root / "state.db")
    gid = mismatch_db.execute("SELECT generation_id FROM runs").fetchone()[0]
    mismatch_db.close()
    assert all(
        gid not in path.read_text(encoding="utf-8")
        for path in mismatch_root.rglob("*.jsonl")
    )

    detail_root = tmp_path / "detail-mismatch"
    detail_root.mkdir()
    detail_db = fresh_db(detail_root)
    seed_inventory(detail_db, warehouse_count=2, item_count=2)
    detail_db.execute(
        "CREATE TRIGGER delete_effect_after_insert "
        "AFTER INSERT ON inventory_effects BEGIN "
        "DELETE FROM inventory_effects WHERE id=NEW.id; END"
    )
    detail_db.commit()
    detail_db.close()
    detail_source = detail_root / "source.dat"
    detail_source.write_bytes(reference_receipt_record())
    detail_controls = detail_root / "legacy.controls"
    write_controls(
        detail_controls,
        processed="1",
        accepted="1",
        rejected="0",
        effects="0",
        quantity="0",
        value="0",
    )
    detail_publish = detail_root / "published"
    detailed = cli(
        "run",
        *run_arguments(
            detail_root / "state.db",
            detail_source,
            DEFAULT_LAYOUT,
            detail_controls,
            detail_root / "ops" / "reports",
            detail_publish,
        ),
    )
    assert detailed.returncode == 2
    assert visible_generation_dirs(detail_publish) == []
    detail_db = connect(detail_root / "state.db")
    detail_gid = detail_db.execute("SELECT generation_id FROM runs").fetchone()[0]
    assert detail_db.execute(
        "SELECT COUNT(*) FROM processed_movements "
        "WHERE generation_id=? AND status='ACCEPTED'",
        (detail_gid,),
    ).fetchone()[0] == 1
    assert detail_db.execute(
        "SELECT COUNT(*) FROM inventory_effects WHERE generation_id=?",
        (detail_gid,),
    ).fetchone()[0] == 0
    detail_db.close()


def test_f2p_repeat_publication_of_same_generation_is_idempotent(
    tmp_path: Path,
) -> None:
    report = tmp_path / "summary.json"
    extra = tmp_path / "effects.csv"
    report.write_text('{"ok":true}\n', encoding="utf-8")
    extra.write_text("movement_id\nM1\n", encoding="utf-8")
    files = {"summary": report, "effects": extra}
    destination = tmp_path / "published"

    first = atomic_publish("g", files, passing_reconciliation(), destination)
    assert_publication_contract(first, "g", files)
    second = atomic_publish("g", files, passing_reconciliation(), destination)
    assert second == first
    assert_publication_contract(second, "g", files)

    manifest = find_publication_manifest(first, "g")
    published_copy = next(
        path for path in first.iterdir()
        if path.is_file() and path != manifest and path.read_bytes() == report.read_bytes()
    )
    published_copy.write_text("corrupt\n", encoding="utf-8")
    must_reject(
        lambda: atomic_publish(
            "g",
            files,
            passing_reconciliation(),
            destination,
        )
    )

    atomic_destination = tmp_path / "atomic-published"
    atomic_target = atomic_destination / "g2"
    missing_input = tmp_path / "missing-publication-input"
    partial_inputs = {"summary": report, "missing": missing_input}
    must_reject(
        lambda: atomic_publish(
            "g2",
            partial_inputs,
            passing_reconciliation("g2"),
            atomic_destination,
        )
    )
    assert not atomic_target.exists()
    assert visible_generation_dirs(atomic_destination) == []

def test_f2p_database_rejects_duplicate_generation_sequence(tmp_path: Path) -> None:
    db = fresh_db(tmp_path)
    db.execute(
        "INSERT INTO processed_movements VALUES(?,?,?,?,?,?,?,?)",
        ("g", "m1", 1, "ACCEPTED", "SKU00001", "RECEIPT", "1", "10"),
    )
    must_reject(
        lambda: db.execute(
            "INSERT INTO processed_movements VALUES(?,?,?,?,?,?,?,?)",
            ("g", "m2", 1, "ACCEPTED", "SKU00001", "RECEIPT", "1", "10"),
        )
    )
    must_reject(
        lambda: db.execute(
            "INSERT INTO processed_movements VALUES(?,?,?,?,?,?,?,?)",
            ("g", "m1", 2, "ACCEPTED", "SKU00001", "RECEIPT", "1", "10"),
        )
    )
    db.execute(
        "INSERT INTO processed_movements VALUES(?,?,?,?,?,?,?,?)",
        ("other", "m1", 1, "ACCEPTED", "SKU00001", "RECEIPT", "1", "10"),
    )
    assert db.execute(
        "SELECT COUNT(*) FROM processed_movements WHERE movement_id='m1'"
    ).fetchone()[0] == 2


def test_f2p_database_rejects_duplicate_reject_sequence(tmp_path: Path) -> None:
    db = fresh_db(tmp_path)
    db.execute(
        "INSERT INTO rejects"
        "(generation_id,sequence,movement_id,code,message,byte_offset,byte_length)"
        " VALUES('g',1,'m1','X','x',0,1)"
    )
    must_reject(
        lambda: db.execute(
            "INSERT INTO rejects"
            "(generation_id,sequence,movement_id,code,message,byte_offset,byte_length)"
            " VALUES('g',1,'m2','Y','y',1,1)"
        )
    )


def test_p2p_valid_positive_signed_comp3_roundtrip_is_preserved() -> None:
    spec = PackedSpec(5, 2, True)
    assert unpack(pack(Decimal("123.45"), spec), spec) == Decimal("123.45")



def test_p2p_active_receipt_policy_remains_valid() -> None:
    valid = [
        movement(reason="PO"),
        movement(reason="RETURN"),
        movement(
            movement_type=MovementType.ISSUE,
            source="W01",
            destination=None,
            reason="SALE",
        ),
        movement(
            movement_type=MovementType.TRANSFER,
            source="W01",
            destination="W02",
            reason="MOVE",
        ),
        movement(
            movement_type=MovementType.ADJUSTMENT,
            source="W01",
            destination=None,
            reason="COUNT",
        ),
        movement(
            movement_type=MovementType.ADJUSTMENT,
            source="W01",
            destination=None,
            reason="DAMAGE",
        ),
        movement(
            movement_type=MovementType.ADJUSTMENT,
            source="W01",
            destination=None,
            reason="RETURN",
        ),
    ]
    assert all(validate_shape(candidate) == [] for candidate in valid)

    invalid = [
        movement(reason="SALE"),
        movement(
            movement_type=MovementType.ISSUE,
            source="W01",
            destination=None,
            reason="PO",
        ),
        movement(
            movement_type=MovementType.TRANSFER,
            source="W01",
            destination="W02",
            reason="RETURN",
        ),
        movement(
            movement_type=MovementType.ADJUSTMENT,
            source="W01",
            destination=None,
            reason="PO",
        ),
    ]
    assert all(validate_shape(candidate) for candidate in invalid)

    m = movement()
    assert validate_item(m, ItemPolicy("SKU00001", True)) == []
    assert validate_warehouses(m, {"W01": WarehousePolicy("W01", True)}) == []

def test_p2p_matching_reconciliation_controls_pass(tmp_path: Path) -> None:
    legacy = {
        "processed_count": Decimal("0"),
        "accepted_count": Decimal("0"),
        "rejected_count": Decimal("0"),
        "effect_count": Decimal("0"),
        "net_quantity": Decimal("0"),
        "net_value": Decimal("0"),
    }
    assert reconcile(fresh_db(tmp_path), "g", legacy).passed


def test_p2p_first_successful_publication_is_verifiable(tmp_path: Path) -> None:
    report = tmp_path / "summary.json"
    report.write_text('{"ok":true}\n', encoding="utf-8")
    files = {"summary": report}
    target = atomic_publish(
        "g",
        files,
        passing_reconciliation(),
        tmp_path / "published",
    )
    assert_publication_contract(target, "g", files)




def test_p2p_cli_success_and_failure_json_contract(tmp_path: Path) -> None:
    described = cli("describe-layout", "--layout", DEFAULT_LAYOUT)
    assert described.returncode == 0
    assert described.stderr == ""
    assert isinstance(parse_stdout(described), dict)

    source = tmp_path / "source.dat"
    source.write_bytes(reference_receipt_record())
    identified = cli(
        "identity",
        "--source", source,
        "--layout", DEFAULT_LAYOUT,
        "--business-date", "20260815",
    )
    assert identified.returncode == 0
    assert identified.stderr == ""
    assert isinstance(parse_stdout(identified), dict)

    init_db_path = tmp_path / "initialized.db"
    initialized = cli(
        "init-db",
        "--db", init_db_path,
        "--schema", SCHEMA,
        "--seed", SEED,
    )
    assert initialized.returncode == 0
    assert initialized.stderr == ""
    assert isinstance(parse_stdout(initialized), dict)
    db = connect(init_db_path)
    tables = {
        row[0]
        for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")
    }
    db.close()
    assert {"processed_movements", "rejects", "checkpoints"} <= tables


def test_p2p_preflight_uses_historical_baseline(tmp_path: Path) -> None:
    db = fresh_db(tmp_path)
    seed_inventory(db, warehouse_count=2, item_count=2)
    apply_sql(db, SEED)
    db.close()
    db_path = tmp_path / "state.db"
    source = tmp_path / "source.dat"
    source.write_bytes(reference_receipt_record())
    controls = tmp_path / "legacy.controls"
    write_controls(controls)
    report_dir = tmp_path / "ops" / "reports"
    publish_dir = tmp_path / "published"

    first = cli(
        "preflight",
        *run_arguments(db_path, source, DEFAULT_LAYOUT, controls, report_dir, publish_dir),
        "--schema", SCHEMA,
        "--seed", SEED,
    )
    first_payload = parse_stdout(first)
    first_rendered = json.dumps(first_payload, sort_keys=True)
    assert "15000" in first_rendered

    db = connect(db_path)
    db.execute("DELETE FROM historical_movements")
    db.commit()
    db.close()
    second = cli(
        "preflight",
        *run_arguments(db_path, source, DEFAULT_LAYOUT, controls, report_dir, publish_dir),
        "--schema", SCHEMA,
        "--seed", SEED,
    )
    assert second.returncode == 2
    second_payload = parse_stdout(second)
    assert second_payload.get("passed") is False
    assert second_payload != first_payload
    assert "15000" not in json.dumps(second_payload, sort_keys=True)

def exercise_adjudicated_operator_workflows(tmp_path: Path) -> None:
    layout_path = write_alternate_layout(tmp_path)
    db = fresh_db(tmp_path)
    seed_inventory(db, warehouse_count=2, item_count=2)
    db.close()
    db_path = tmp_path / "state.db"
    source = tmp_path / "source.dat"
    source.write_bytes(reference_receipt_record() + b"Z")
    controls = tmp_path / "legacy.controls"
    write_controls(controls)
    operational_root = tmp_path / "ops"
    report_dir = operational_root / "reports"
    publish_dir = tmp_path / "published"
    registry = operational_root / "publication-registry.jsonl"
    quarantine = operational_root / "quarantine" / "records.jsonl"

    run = cli(
        "run",
        *run_arguments(
            db_path, source, layout_path, controls, report_dir, publish_dir
        ),
    )
    assert run.returncode == 0
    parse_stdout(run)

    def audit_path(path: Path) -> subprocess.CompletedProcess[str]:
        return cli(
            "audit",
            "--db", path,
            "--source", source,
            "--layout", layout_path,
            "--business-date", "20260815",
            "--expected-records", "1",
            "--quarantine", quarantine,
            "--registry", registry,
        )

    audited = audit_path(db_path)
    assert audited.returncode == 0
    assert parse_stdout(audited).get("passed") is True


    healthy_payload = parse_stdout(audited)
    gid_for_audit = build_identity(source, layout_path, "20260815").generation_id

    recovery_bad = tmp_path / "audit-recovery-bad.db"
    shutil.copyfile(db_path, recovery_bad)
    changed = connect(recovery_bad)
    changed.execute(
        "UPDATE runs SET state='PROCESSING' WHERE generation_id=?",
        (gid_for_audit,),
    )
    changed.execute(
        "UPDATE checkpoints SET source_fingerprint='mismatched:fingerprint' "
        "WHERE generation_id=?",
        (gid_for_audit,),
    )
    changed.commit()
    changed.close()
    recovery_audit = audit_path(recovery_bad)
    assert recovery_audit.returncode == 2
    assert parse_stdout(recovery_audit).get("passed") is False

    control_bad = tmp_path / "audit-control-bad.db"
    shutil.copyfile(db_path, control_bad)
    changed = sqlite3.connect(control_bad)
    changed.execute(
        "INSERT INTO inventory_effects"
        "(generation_id,movement_id,sequence,warehouse_id,item_id,quantity_delta,value_delta,effect_kind)"
        " VALUES(?,?,?,?,?,?,?,?)",
        (gid_for_audit, "ORPHAN", 999, "W01", "SKU00001", "1", "1", "RECEIPT"),
    )
    changed.commit()
    changed.close()
    control_audit = audit_path(control_bad)
    assert control_audit.returncode == 2
    assert parse_stdout(control_audit).get("passed") is False

    published_for_registry = visible_generation_dirs(publish_dir)
    assert len(published_for_registry) == 1
    registry_manifest = find_publication_manifest(published_for_registry[0], gid_for_audit)
    registry_member = next(
        path for path in published_for_registry[0].iterdir()
        if path.is_file() and path != registry_manifest
    )
    registry_member_bytes = registry_member.read_bytes()
    registry_member.write_bytes(b"registry-health-corruption")
    try:
        registry_audit = audit_path(db_path)
        assert registry_audit.returncode == 2
        assert parse_stdout(registry_audit).get("passed") is False
    finally:
        registry_member.write_bytes(registry_member_bytes)

    metric_audit = cli(
        "audit",
        "--db", db_path,
        "--source", source,
        "--layout", layout_path,
        "--business-date", "20260815",
        "--expected-records", "2",
        "--quarantine", quarantine,
        "--registry", registry,
    )
    assert parse_stdout(metric_audit) != healthy_payload

    settlement_bad = tmp_path / "settlement-bad.db"
    shutil.copyfile(db_path, settlement_bad)
    changed = connect(settlement_bad)
    changed.execute("DELETE FROM inventory_effects")
    changed.commit()
    changed.close()
    settlement_audit = audit_path(settlement_bad)
    assert settlement_audit.returncode == 2
    assert parse_stdout(settlement_audit).get("passed") is False

    checkpoint_bad = tmp_path / "checkpoint-bad.db"
    shutil.copyfile(db_path, checkpoint_bad)
    changed = connect(checkpoint_bad)
    changed.execute("UPDATE checkpoints SET last_sequence=last_sequence+10")
    changed.commit()
    changed.close()
    checkpoint_audit = audit_path(checkpoint_bad)
    assert checkpoint_audit.returncode == 2
    assert parse_stdout(checkpoint_audit).get("passed") is False

    inventory_bad = tmp_path / "inventory-bad.db"
    shutil.copyfile(db_path, inventory_bad)
    changed = connect(inventory_bad)
    changed.execute(
        "UPDATE inventory_positions SET quantity='-1' "
        "WHERE warehouse_id='W01' AND item_id='SKU00001'"
    )
    changed.commit()
    changed.close()
    inventory_audit = audit_path(inventory_bad)
    assert inventory_audit.returncode == 2
    assert parse_stdout(inventory_audit).get("passed") is False

    journal_bad = tmp_path / "journal-bad.db"
    shutil.copyfile(db_path, journal_bad)
    changed = connect(journal_bad)
    changed.execute(
        "UPDATE event_journal SET payload_json='{}' "
        "WHERE event_id=(SELECT MIN(event_id) FROM event_journal)"
    )
    changed.commit()
    changed.close()
    journal_audit = audit_path(journal_bad)
    assert journal_audit.returncode == 2
    assert parse_stdout(journal_audit).get("passed") is False


    gid_for_quarantine = build_identity(source, layout_path, "20260815").generation_id
    quarantine.parent.mkdir(parents=True, exist_ok=True)
    quarantine.write_text(
        json.dumps(
            {
                "generation_id": gid_for_quarantine,
                "sequence": 999,
                "byte_offset": 0,
                "byte_length": 1,
                "error_code": "DECODE",
                "error_message": "corrupt quarantine evidence",
                "raw_sha256": "not-a-real-digest",
                "raw_hex": "00",
                "captured_at": "2026-08-16T00:00:00+00:00",
            }
        ) + "\n",
        encoding="utf-8",
    )
    quarantine_audit = audit_path(db_path)
    assert quarantine_audit.returncode == 2
    assert parse_stdout(quarantine_audit).get("passed") is False
    quarantine.unlink()

    db = connect(db_path)
    gid = db.execute("SELECT generation_id FROM runs").fetchone()[0]
    before_event = db.execute(
        "SELECT COALESCE(MAX(event_id),0) FROM event_journal"
    ).fetchone()[0]
    db.close()
    published_dirs = visible_generation_dirs(publish_dir)
    assert len(published_dirs) == 1
    published_root = published_dirs[0]
    manifest = find_publication_manifest(published_root, gid)
    manifest_digest = file_digest(manifest)
    live_files = {
        path: file_digest(path)
        for root in (report_dir, publish_dir)
        for path in root.rglob("*")
        if path.is_file()
    }

    archive_root = tmp_path / "archive"
    archive_registry = operational_root / "archive-registry-evidence"
    assert not archive_registry.exists()
    archived = cli(
        "archive",
        "--db", db_path,
        "--source", source,
        "--layout", layout_path,
        "--business-date", "20260815",
        "--report-dir", report_dir,
        "--publish-dir", publish_dir,
        "--archive-dir", archive_root,
        "--registry", archive_registry,
    )
    assert archived.returncode == 0
    archive_payload = parse_stdout(archived)
    assert archive_payload.get("passed") is True

    archive_dirs = visible_generation_dirs(archive_root)
    assert len(archive_dirs) == 1
    archive_files = [
        path for path in archive_dirs[0].rglob("*") if path.is_file()
    ]
    assert archive_files
    archive_blob = b"\n".join(path.read_bytes() for path in archive_files)
    for control_name in (
        "processed_count",
        "accepted_count",
        "rejected_count",
        "effect_count",
        "net_quantity",
        "net_value",
    ):
        assert control_name.encode() in archive_blob
    assert b"W01" in archive_blob
    assert b"SKU00001" in archive_blob
    for expected in (
        gid,
        file_digest(source),
        file_digest(layout_path),
        manifest_digest,
    ):
        assert expected.encode() in archive_blob

    archive_registry_bytes = archive_registry.read_bytes()
    assert archive_registry_bytes
    assert gid.encode() in archive_registry_bytes
    assert manifest_digest.encode() in archive_registry_bytes
    registry_audit = cli(
        "audit",
        "--db", db_path,
        "--source", source,
        "--layout", layout_path,
        "--business-date", "20260815",
        "--expected-records", "1",
        "--quarantine", quarantine,
        "--registry", archive_registry,
    )
    assert registry_audit.returncode == 0
    assert parse_stdout(registry_audit).get("passed") is True

    db = connect(db_path)
    new_events = db.execute(
        "SELECT event_type,subject,payload_json FROM event_journal "
        "WHERE event_id>? ORDER BY event_id",
        (before_event,),
    ).fetchall()
    db.close()
    assert new_events
    journal_evidence = "\n".join(str(value) for row in new_events for value in row)
    assert manifest_digest in journal_evidence
    assert str(archive_dirs[0]) in journal_evidence

    retention_categories = {"report", "publication", "audit", "quarantine"}
    assert any(
        retention_categories <= set(mapping)
        and all(
            isinstance(mapping[name], int) and mapping[name] > 0
            for name in retention_categories
        )
        for mapping in nested_mappings(archive_payload)
    )

    for path, digest in live_files.items():
        assert path.is_file()
        assert file_digest(path) == digest

def test_p2p_audit_and_archive_operator_workflows_are_reachable(tmp_path: Path) -> None:
    db = fresh_db(tmp_path)
    seed_inventory(db, warehouse_count=2, item_count=2)
    db.close()
    db_path = tmp_path / "state.db"
    source = tmp_path / "source.dat"
    source.write_bytes(reference_receipt_record())
    controls = tmp_path / "legacy.controls"
    write_controls(controls)
    operational_root = tmp_path / "ops"
    report_dir = operational_root / "reports"
    publish_dir = tmp_path / "published"
    registry = operational_root / "publication-registry.jsonl"
    quarantine = operational_root / "quarantine" / "records.jsonl"

    run = cli(
        "run",
        *run_arguments(db_path, source, DEFAULT_LAYOUT, controls, report_dir, publish_dir),
    )
    assert run.returncode == 0
    assert isinstance(parse_stdout(run), dict)

    audited = cli(
        "audit",
        "--db", db_path,
        "--source", source,
        "--layout", DEFAULT_LAYOUT,
        "--business-date", "20260815",
        "--expected-records", "1",
        "--quarantine", quarantine,
        "--registry", registry,
    )
    assert audited.returncode == 0
    assert parse_stdout(audited).get("passed") is True

    archived = cli(
        "archive",
        "--db", db_path,
        "--source", source,
        "--layout", DEFAULT_LAYOUT,
        "--business-date", "20260815",
        "--report-dir", report_dir,
        "--publish-dir", publish_dir,
        "--archive-dir", tmp_path / "archive",
        "--registry", registry,
    )
    assert archived.returncode == 0
    assert parse_stdout(archived).get("passed") is True

def test_p2p_accepted_movement_transaction_rolls_back_on_failure(tmp_path: Path) -> None:
    db = fresh_db(tmp_path)
    seed_inventory(db, warehouse_count=2, item_count=2)
    ensure_journal_table(db)
    db.execute(
        """
        CREATE TRIGGER fail_accept_event
        BEFORE INSERT ON event_journal
        WHEN NEW.event_type='ACCEPT'
        BEGIN
          SELECT RAISE(ABORT,'injected');
        END
        """
    )
    db.commit()
    before = db.execute(
        "SELECT quantity,value,version FROM inventory_positions "
        "WHERE warehouse_id='W01' AND item_id='SKU00001'"
    ).fetchone()
    source = tmp_path / "source.dat"
    source.write_bytes(reference_receipt_record())
    controls = tmp_path / "legacy.controls"
    write_controls(controls)
    cfg = PipelineConfig(
        source,
        DEFAULT_LAYOUT,
        "20260815",
        controls,
        tmp_path / "reports",
        tmp_path / "published",
    )
    gid = build_identity(source, DEFAULT_LAYOUT, "20260815").generation_id
    must_reject(lambda: process(db, cfg))
    assert db.execute(
        "SELECT COUNT(*) FROM processed_movements WHERE generation_id=?",
        (gid,),
    ).fetchone()[0] == 0
    assert db.execute(
        "SELECT COUNT(*) FROM inventory_effects WHERE generation_id=?",
        (gid,),
    ).fetchone()[0] == 0
    assert db.execute(
        "SELECT COUNT(*) FROM checkpoints WHERE generation_id=?",
        (gid,),
    ).fetchone()[0] == 0
    assert db.execute(
        "SELECT COUNT(*) FROM event_journal WHERE generation_id=?",
        (gid,),
    ).fetchone()[0] == 0
    after = db.execute(
        "SELECT quantity,value,version FROM inventory_positions "
        "WHERE warehouse_id='W01' AND item_id='SKU00001'"
    ).fetchone()
    assert tuple(after) == tuple(before)


def test_p2p_rejected_movement_transaction_rolls_back_on_failure(tmp_path: Path) -> None:
    db = fresh_db(tmp_path)
    seed_inventory(db, warehouse_count=2, item_count=2)
    ensure_journal_table(db)
    db.execute(
        """
        CREATE TRIGGER fail_reject_event
        BEFORE INSERT ON event_journal
        WHEN NEW.event_type='REJECT'
        BEGIN
          SELECT RAISE(ABORT,'injected');
        END
        """
    )
    db.commit()
    source = tmp_path / "source.dat"
    source.write_bytes(reference_record(reason="SALE"))
    controls = tmp_path / "legacy.controls"
    write_controls(controls)
    cfg = PipelineConfig(
        source,
        DEFAULT_LAYOUT,
        "20260815",
        controls,
        tmp_path / "reports",
        tmp_path / "published",
    )
    gid = build_identity(source, DEFAULT_LAYOUT, "20260815").generation_id
    must_reject(lambda: process(db, cfg))
    assert db.execute(
        "SELECT COUNT(*) FROM rejects WHERE generation_id=?",
        (gid,),
    ).fetchone()[0] == 0
    assert db.execute(
        "SELECT COUNT(*) FROM processed_movements WHERE generation_id=?",
        (gid,),
    ).fetchone()[0] == 0
    assert db.execute(
        "SELECT COUNT(*) FROM checkpoints WHERE generation_id=?",
        (gid,),
    ).fetchone()[0] == 0
    assert db.execute(
        "SELECT COUNT(*) FROM event_journal WHERE generation_id=?",
        (gid,),
    ).fetchone()[0] == 0


def test_p2p_decode_and_transform_reject_codes_are_stable(tmp_path: Path) -> None:
    cases = [
        ("decode", b"MOVE", "DECODE"),
        (
            "transform",
            reference_record(type_code="Z"),
            "TRANSFORM",
        ),
    ]
    for name, raw, expected_code in cases:
        root = tmp_path / name
        root.mkdir()
        db = fresh_db(root)
        seed_inventory(db, warehouse_count=2, item_count=2)
        source = root / "source.dat"
        source.write_bytes(raw)
        controls = root / "legacy.controls"
        write_controls(
            controls,
            processed="0",
            accepted="0",
            rejected="0",
            effects="0",
            quantity="0",
            value="0",
        )
        process(
            db,
            PipelineConfig(
                source,
                DEFAULT_LAYOUT,
                "20260815",
                controls,
                root / "reports",
                root / "published",
            ),
        )
        reject = db.execute(
            "SELECT code,byte_offset,byte_length FROM rejects ORDER BY id"
        ).fetchone()
        assert reject is not None
        assert reject[0] == expected_code
        assert reject[1] == 0
        if expected_code == "DECODE":
            assert reject[2] == 0
