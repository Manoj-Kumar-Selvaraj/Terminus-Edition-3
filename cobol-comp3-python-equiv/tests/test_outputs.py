from __future__ import annotations

from decimal import Decimal
import json
import os
from pathlib import Path
import sqlite3
import sys

import pytest

ROOT = Path(os.environ.get("EQUIV_ROOT", "/app/equiv"))
sys.path.insert(0, str(ROOT))

from src.accounting import apply_effect, issue_effect, transfer_effect
from src.checkpoint import resume_sequence, validate_checkpoint
from src.comp3 import PackedSpec, pack, unpack
from src.database import apply_sql, connect, seed_inventory
from src.framing import RecordDecodeError, decode_record
from src.generation import assert_resume_compatible, generation_id
from src.layout import Field, Layout, active_occurs, load_layout, resolve_offsets
from src.models import Checkpoint, GenerationIdentity, InventoryEffect, InventoryPosition, Movement, MovementType, ReconciliationControl, ReconciliationResult
from src.pipeline import PipelineConfig, process
from src.policy import ItemPolicy, WarehousePolicy, validate_item, validate_shape, validate_warehouses
from src.publication import atomic_publish, verify_publication
from src.reconciliation import reconcile

SCHEMA = ROOT / "sql" / "schema.sql"
DEFAULT_LAYOUT = ROOT / "config" / "movement.layout.json"


def identity(*, gid: str = "g", source: str = "s", layout: str = "l", date: str = "2026-08-15") -> GenerationIdentity:
    return GenerationIdentity(gid, "source.dat", 10, source, layout, date)


def movement(*, movement_id: str = "MOVE00000001", sequence: int = 1, movement_type: MovementType = MovementType.RECEIPT, item_id: str = "SKU00001", source: str | None = None, destination: str | None = "W01", quantity: str = "1.000", unit_cost: str = "10.00", reason: str = "PO", gid: str = "g") -> Movement:
    return Movement(movement_id, sequence, movement_type, item_id, source, destination, Decimal(quantity), Decimal(unit_cost), "20260815", reason, gid)


def fresh_db(tmp_path: Path) -> sqlite3.Connection:
    db = connect(tmp_path / "state.db")
    apply_sql(db, SCHEMA)
    return db


def reference_comp3(value: str, digits: int, scale: int = 0, sign: int = 0xF) -> bytes:
    number = Decimal(value).copy_abs().quantize(Decimal(1).scaleb(-scale))
    scaled = int(number.scaleb(scale))
    body = [int(ch) for ch in f"{scaled:0{digits}d}"] + [sign]
    if len(body) % 2:
        body.insert(0, 0)
    return bytes((body[i] << 4) | body[i + 1] for i in range(0, len(body), 2))


def reference_receipt_record() -> bytes:
    return b"".join([b"MOVE00000001", reference_comp3("1", 6), b"R", b"SKU00001", b"   ", b"W01", reference_comp3("1.000", 10, 3), reference_comp3("10.00", 9, 2), b"20260815", b"PO    ", reference_comp3("0", 1)])


def passing_reconciliation(gid: str = "g") -> ReconciliationResult:
    return ReconciliationResult(gid, [ReconciliationControl("ok", Decimal("1"), Decimal("1"))])


def failing_reconciliation(gid: str = "g") -> ReconciliationResult:
    return ReconciliationResult(gid, [ReconciliationControl("bad", Decimal("1"), Decimal("0"))])


def test_f2p_nonzero_comp3_padding_is_rejected() -> None:
    with pytest.raises(ValueError, match="padding"):
        unpack(bytes.fromhex("11234c"), PackedSpec(4, 0, True))


def test_f2p_invalid_comp3_digit_nibble_a_is_rejected() -> None:
    with pytest.raises(ValueError, match="digit"):
        unpack(bytes.fromhex("012a3c"), PackedSpec(4, 0, True))


def test_f2p_signed_comp3_rejects_unsigned_f_sign() -> None:
    with pytest.raises(ValueError, match="sign"):
        unpack(bytes.fromhex("01234f"), PackedSpec(4, 0, True))


def test_f2p_unsigned_comp3_rejects_signed_c_sign() -> None:
    with pytest.raises(ValueError, match="sign"):
        unpack(bytes.fromhex("01234c"), PackedSpec(4, 0, False))


def test_f2p_unsigned_pack_uses_f_and_rejects_negative() -> None:
    spec = PackedSpec(4, 0, False)
    assert pack(Decimal("1234"), spec)[-1] & 0x0F == 0x0F
    with pytest.raises(ValueError, match="negative"):
        pack(Decimal("-1"), spec)


def test_f2p_signed_negative_pack_uses_d_sign() -> None:
    encoded = pack(Decimal("-1234"), PackedSpec(4, 0, True))
    assert encoded[-1] & 0x0F == 0x0D


def test_f2p_redefines_does_not_increase_static_storage() -> None:
    layout = Layout("R", [Field("A", "X(4)"), Field("B", "X(4)", redefines="A"), Field("C", "X(2)")])
    assert layout.static_min_length() == 6


def test_f2p_caller_supplied_layout_path_is_honored(tmp_path: Path) -> None:
    path = tmp_path / "alternate-layout.json"
    path.write_text(json.dumps({"layout_id": "ALT-SEMANTIC", "version": 7, "fields": [{"name": "CODE", "picture": "X(2)"}]}))
    loaded = load_layout(path)
    assert loaded.layout_id == "ALT-SEMANTIC"
    assert loaded.static_min_length() == 2


def test_f2p_odo_count_above_declared_maximum_is_rejected() -> None:
    field = Field("ATTR", "X(2)", occurs=3, depending_on="N")
    with pytest.raises(ValueError, match="outside"):
        active_occurs(field, {"N": 4})


def test_f2p_redefines_offset_overlaps_target_without_cursor_advance() -> None:
    layout = Layout("R", [Field("A", "X(4)"), Field("B", "X(4)", redefines="A"), Field("C", "X(2)")])
    offsets = resolve_offsets(layout)
    assert offsets["A"] == (0, 4)
    assert offsets["B"] == (0, 4)
    assert offsets["C"] == (4, 2)


def test_f2p_complete_malformed_record_reports_full_boundary() -> None:
    layout = Layout("M", [Field("N", "9(2)", usage="COMP-3"), Field("TAIL", "X(4)")])
    raw = bytes.fromhex("0a1f") + b"TAIL"
    with pytest.raises(RecordDecodeError) as caught:
        decode_record(layout, raw, 10)
    assert caught.value.offset == 10
    assert caught.value.length == 6


def test_f2p_generation_id_binds_layout_digest() -> None:
    assert generation_id("source", "layout-a", "2026-08-15") != generation_id("source", "layout-b", "2026-08-15")


def test_f2p_resume_rejects_layout_change() -> None:
    with pytest.raises(ValueError, match="layout"):
        assert_resume_compatible(identity(gid="same", layout="layout-a"), identity(gid="same", layout="layout-b"))


def test_f2p_checkpoint_fingerprint_mismatch_is_rejected() -> None:
    ident = identity(gid="g1", source="s1", layout="l1")
    with pytest.raises(ValueError, match="fingerprint"):
        validate_checkpoint(ident, Checkpoint("g1", 2, 100, "wrong:fingerprint", "now"))


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
    controls.write_text("processed_count=1\naccepted_count=1\nrejected_count=0\neffect_count=1\nnet_quantity=1.000\nnet_value=10.00\n")
    cfg = PipelineConfig(source, DEFAULT_LAYOUT, "2026-08-15", controls, tmp_path / "reports", tmp_path / "published")
    first = process(db, cfg)
    assert first.state.value == "PUBLISHED"
    second = process(db, cfg)
    assert second.state.value == "PUBLISHED"
    gid = first.generation_id
    assert db.execute("SELECT COUNT(*) FROM processed_movements WHERE generation_id=?", (gid,)).fetchone()[0] == 1
    assert db.execute("SELECT COUNT(*) FROM inventory_effects WHERE generation_id=?", (gid,)).fetchone()[0] == 1


def test_f2p_zero_quantity_is_rejected() -> None:
    assert any(issue.code == "QUANTITY" for issue in validate_shape(movement(quantity="0")))


def test_f2p_same_warehouse_transfer_is_rejected() -> None:
    m = movement(movement_type=MovementType.TRANSFER, source="W01", destination="W01", reason="MOVE")
    assert any(issue.code == "TRANSFER_LOOP" for issue in validate_shape(m))


def test_f2p_inactive_item_is_rejected() -> None:
    assert any(issue.code == "ITEM_INACTIVE" for issue in validate_item(movement(), ItemPolicy("SKU00001", False)))


def test_f2p_inactive_warehouse_is_rejected() -> None:
    assert any(issue.code == "WAREHOUSE_INACTIVE" for issue in validate_warehouses(movement(), {"W01": WarehousePolicy("W01", False)}))


def test_f2p_issue_requires_full_available_quantity() -> None:
    m = movement(movement_type=MovementType.ISSUE, source="W01", destination=None, quantity="6", reason="SALE")
    with pytest.raises(ValueError, match="insufficient"):
        issue_effect(m, InventoryPosition("W01", "SKU00001", Decimal("5"), Decimal("25")))


def test_f2p_issue_uses_weighted_source_unit_cost() -> None:
    m = movement(movement_type=MovementType.ISSUE, source="W01", destination=None, quantity="2", unit_cost="99", reason="SALE")
    effect = issue_effect(m, InventoryPosition("W01", "SKU00001", Decimal("10"), Decimal("50")))[0]
    assert effect.value_delta == Decimal("-10.00")


def test_f2p_transfer_preserves_source_value_across_warehouses() -> None:
    m = movement(movement_type=MovementType.TRANSFER, source="W01", destination="W02", quantity="2", unit_cost="99", reason="MOVE")
    effects = transfer_effect(m, InventoryPosition("W01", "SKU00001", Decimal("10"), Decimal("50")))
    assert sum((e.value_delta for e in effects), Decimal("0")) == Decimal("0")


def test_f2p_effect_application_rejects_negative_inventory() -> None:
    pos = InventoryPosition("W01", "SKU00001", Decimal("1"), Decimal("10"))
    effect = InventoryEffect("M", "W01", "SKU00001", Decimal("-2"), Decimal("-20"), "ISSUE", 1)
    with pytest.raises(ValueError, match="negative inventory"):
        apply_effect(pos, effect)


def test_f2p_reconciliation_checks_legacy_effect_count(tmp_path: Path) -> None:
    result = reconcile(fresh_db(tmp_path), "g", {"processed_count": Decimal("0"), "accepted_count": Decimal("0"), "rejected_count": Decimal("0"), "effect_count": Decimal("1"), "net_quantity": Decimal("0"), "net_value": Decimal("0")})
    assert not result.passed
    assert any(c.name == "effect_count" and not c.passed for c in result.controls)


def test_f2p_reconciliation_rejects_unbalanced_transfer(tmp_path: Path) -> None:
    db = fresh_db(tmp_path)
    db.execute("INSERT INTO processed_movements(generation_id,movement_id,sequence,status,item_id,movement_type,quantity,unit_cost) VALUES('g','m',1,'ACCEPTED','SKU00001','TRANSFER','1','10')")
    db.execute("INSERT INTO inventory_effects(generation_id,movement_id,sequence,warehouse_id,item_id,quantity_delta,value_delta,effect_kind) VALUES('g','m',1,'W01','SKU00001','-1','-10','TRANSFER_OUT')")
    db.execute("INSERT INTO inventory_effects(generation_id,movement_id,sequence,warehouse_id,item_id,quantity_delta,value_delta,effect_kind) VALUES('g','m',1,'W02','SKU00001','1','9','TRANSFER_IN')")
    db.commit()
    legacy = {"processed_count": Decimal("1"), "accepted_count": Decimal("1"), "rejected_count": Decimal("0"), "effect_count": Decimal("2"), "net_quantity": Decimal("0"), "net_value": Decimal("-1")}
    result = reconcile(db, "g", legacy)
    assert not result.passed
    assert any(c.name == "unbalanced_transfers" and not c.passed for c in result.controls)


def test_f2p_failed_reconciliation_cannot_publish(tmp_path: Path) -> None:
    report = tmp_path / "summary.json"
    report.write_text("{}")
    with pytest.raises(ValueError, match="failed reconciliation"):
        atomic_publish("g", {"summary": report}, failing_reconciliation(), tmp_path / "published")


def test_f2p_repeat_publication_of_same_generation_is_idempotent(tmp_path: Path) -> None:
    report = tmp_path / "summary.json"
    report.write_text('{"ok":true}\n')
    destination = tmp_path / "published"
    first = atomic_publish("g", {"summary": report}, passing_reconciliation(), destination)
    second = atomic_publish("g", {"summary": report}, passing_reconciliation(), destination)
    assert first == second
    assert verify_publication(second)


def test_f2p_database_rejects_duplicate_generation_sequence(tmp_path: Path) -> None:
    db = fresh_db(tmp_path)
    db.execute("INSERT INTO processed_movements VALUES(?,?,?,?,?,?,?,?)", ("g", "m1", 1, "ACCEPTED", "SKU00001", "RECEIPT", "1", "10"))
    with pytest.raises(sqlite3.IntegrityError):
        db.execute("INSERT INTO processed_movements VALUES(?,?,?,?,?,?,?,?)", ("g", "m2", 1, "ACCEPTED", "SKU00001", "RECEIPT", "1", "10"))


def test_f2p_database_rejects_duplicate_reject_sequence(tmp_path: Path) -> None:
    db = fresh_db(tmp_path)
    db.execute("INSERT INTO rejects(generation_id,sequence,movement_id,code,message,byte_offset,byte_length) VALUES('g',1,'m1','X','x',0,1)")
    with pytest.raises(sqlite3.IntegrityError):
        db.execute("INSERT INTO rejects(generation_id,sequence,movement_id,code,message,byte_offset,byte_length) VALUES('g',1,'m2','Y','y',1,1)")


def test_p2p_valid_positive_signed_comp3_roundtrip_is_preserved() -> None:
    spec = PackedSpec(5, 2, True)
    assert unpack(pack(Decimal("123.45"), spec), spec) == Decimal("123.45")


def test_p2p_active_receipt_policy_remains_valid() -> None:
    m = movement()
    assert validate_shape(m) == []
    assert validate_item(m, ItemPolicy("SKU00001", True)) == []
    assert validate_warehouses(m, {"W01": WarehousePolicy("W01", True)}) == []


def test_p2p_matching_reconciliation_controls_pass(tmp_path: Path) -> None:
    legacy = {"processed_count": Decimal("0"), "accepted_count": Decimal("0"), "rejected_count": Decimal("0"), "effect_count": Decimal("0"), "net_quantity": Decimal("0"), "net_value": Decimal("0")}
    assert reconcile(fresh_db(tmp_path), "g", legacy).passed


def test_p2p_first_successful_publication_is_verifiable(tmp_path: Path) -> None:
    report = tmp_path / "summary.json"
    report.write_text('{"ok":true}\n')
    target = atomic_publish("g", {"summary": report}, passing_reconciliation(), tmp_path / "published")
    assert verify_publication(target)
