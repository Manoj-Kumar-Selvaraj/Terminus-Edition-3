"""Behavioral checks for the catalog plane public CLI and durable state."""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import sqlite3
import subprocess
from pathlib import Path

import pytest

APP = Path("/app/catalog")
CTL = APP / "bin" / "catalogctl"
FIXTURES = Path("/tests/fixtures")
WAREHOUSE = APP / "warehouse" / "inventory.sqlite"


def _copy_home(tmp_path: Path) -> Path:
    dest = tmp_path / "catalog"
    dest.mkdir()
    for name in ("data", "sql", "config", "warehouse", "docs", "notes", "logs"):
        src = APP / name
        if src.is_dir():
            shutil.copytree(src, dest / name)
    (dest / "out").mkdir(parents=True, exist_ok=True)
    return dest


def run_ctl(home: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["CATALOG_ROOT"] = str(home)
    return subprocess.run(
        [str(CTL), *args],
        cwd=str(home),
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )


def wal_bytes(home: Path) -> bytes:
    path = home / "data" / "wal.jsonl"
    return path.read_bytes() if path.is_file() else b""


def slot(home: Path) -> dict:
    return json.loads((home / "data" / "replica_slot.json").read_text(encoding="utf-8"))


def health(home: Path) -> dict:
    return json.loads((home / "out" / "health.json").read_text(encoding="utf-8"))


def warehouse_digest() -> str:
    return hashlib.sha256(WAREHOUSE.read_bytes()).hexdigest()


def install_pending_sentinel(home: Path) -> None:
    """Install a local uncommitted heap row so inspect/empty-check cannot quietly recover."""
    engine = sqlite3.connect(str(home / "data" / "engine.sqlite"))
    engine.execute(
        "INSERT INTO row_version(table_name, pk, xmin, xmax, committed, lsn, payload) VALUES (?,?,?,?,?,?,?)",
        (
            "sku",
            "s-test-pending",
            9_999_999,
            None,
            0,
            9_999_999,
            '{"sku_id":"s-test-pending","tenant_id":"t00","sku_code":"PENDTEST"}',
        ),
    )
    engine.commit()
    engine.close()


def pending_sentinel_count(home: Path) -> int:
    engine = sqlite3.connect(str(home / "data" / "engine.sqlite"))
    count = engine.execute(
        "SELECT COUNT(*) FROM row_version WHERE pk = 's-test-pending'"
    ).fetchone()[0]
    engine.close()
    return int(count)


def fingerprint_state(home: Path) -> dict:
    data = home / "data"
    return {
        "wal": wal_bytes(home),
        "slot": (data / "replica_slot.json").read_bytes(),
        "indexes": (data / "indexes.json").read_bytes() if (data / "indexes.json").is_file() else b"",
        "replica": (data / "replica.sqlite").read_bytes(),
        "pending": pending_sentinel_count(home),
    }


def wal_records(home: Path) -> list[dict]:
    text = (home / "data" / "wal.jsonl").read_text(encoding="utf-8")
    return [json.loads(line) for line in text.splitlines() if line.strip()]


@pytest.fixture()
def home(tmp_path: Path) -> Path:
    return _copy_home(tmp_path)


def test_f2p_unknown_flag_leaves_wal(home: Path) -> None:
    """Unknown flags exit 2 before appending WAL."""
    before = wal_bytes(home)
    proc = run_ctl(home, "--not-a-flag")
    assert proc.returncode == 2
    assert wal_bytes(home) == before


def test_f2p_missing_commit_input_leaves_wal(home: Path) -> None:
    """commit without --input exits 2 and does not open a transaction."""
    before = wal_bytes(home)
    proc = run_ctl(home, "commit")
    assert proc.returncode == 2
    assert wal_bytes(home) == before


def test_f2p_reset_output_does_not_truncate_wal(home: Path) -> None:
    """--reset-output may clear out/ but not WAL."""
    before = wal_bytes(home)
    proc = run_ctl(home, "--reset-output", "empty-check")
    assert proc.returncode == 0
    assert wal_bytes(home) == before


def test_f2p_empty_check_does_not_bump_epoch(home: Path) -> None:
    """empty-check rewrites health without recover, apply, WAL append, or epoch bump."""
    install_pending_sentinel(home)
    before = fingerprint_state(home)
    before_epoch = slot(home)["epoch"]
    assert before["pending"] == 1
    proc = run_ctl(home, "empty-check")
    assert proc.returncode == 0
    assert slot(home)["epoch"] == before_epoch
    after = fingerprint_state(home)
    assert after["wal"] == before["wal"]
    assert after["slot"] == before["slot"]
    assert after["indexes"] == before["indexes"]
    assert after["replica"] == before["replica"]
    assert after["pending"] == 1
    body = health(home)
    assert body["cdc_source"] == "wal"
    assert isinstance(body["heap_visible_count"], int)


def test_f2p_inspect_does_not_recover(home: Path) -> None:
    """inspect rewrites health without recover, decode-apply, WAL append, or epoch bump."""
    install_pending_sentinel(home)
    before = fingerprint_state(home)
    before_epoch = slot(home)["epoch"]
    assert before["pending"] == 1
    proc = run_ctl(home, "inspect")
    assert proc.returncode == 0
    assert wal_bytes(home) == before["wal"]
    assert slot(home)["epoch"] == before_epoch
    after = fingerprint_state(home)
    assert after["slot"] == before["slot"]
    assert after["indexes"] == before["indexes"]
    assert after["replica"] == before["replica"]
    assert after["pending"] == 1
    body = health(home)
    assert body["cdc_source"] == "wal"


def test_p2p_commit_insert_sku(home: Path) -> None:
    """A valid sku insert still installs a committed-visible heap row when accepted."""
    proc = run_ctl(home, "commit", "--input", str(FIXTURES / "insert_sku.jsonl"))
    assert proc.returncode == 0
    engine = sqlite3.connect(str(home / "data" / "engine.sqlite"))
    row = engine.execute(
        "SELECT COUNT(*) FROM row_version WHERE pk = 's-t00-new' AND xmax IS NULL AND committed = 1"
    ).fetchone()
    engine.close()
    assert row[0] == 1
    body = health(home)
    assert body["cdc_source"] == "wal"
    assert isinstance(body["durable_lsn"], int)
    assert body["durable_lsn"] > 0


def test_f2p_health_rewrite_after_decode_apply(home: Path) -> None:
    """Successful decode and apply rewrite health.json from observed state."""
    run_ctl(home, "recover")
    health_path = home / "out" / "health.json"
    if health_path.is_file():
        health_path.unlink()
    proc = run_ctl(home, "decode")
    assert proc.returncode == 0
    assert health_path.is_file()
    decoded = health(home)
    assert decoded["cdc_source"] == "wal"
    assert isinstance(decoded["durable_lsn"], int)
    health_path.unlink()
    proc = run_ctl(home, "apply")
    assert proc.returncode == 0
    assert health_path.is_file()
    applied = health(home)
    assert applied["cdc_source"] == "wal"
    assert isinstance(applied["epoch"], int)
    assert applied["epoch"] == slot(home)["epoch"]


def test_p2p_checkpoint_lsn_not_zero_after_checkpoint(home: Path) -> None:
    """checkpoint stores the durable WAL lsn and does not change replica epoch."""
    before_epoch = slot(home)["epoch"]
    proc = run_ctl(home, "checkpoint")
    assert proc.returncode == 0
    payload = json.loads((home / "data" / "checkpoint.json").read_text(encoding="utf-8"))
    assert int(payload["lsn"]) == health(home)["durable_lsn"]
    assert int(payload["lsn"]) > 0
    assert slot(home)["epoch"] == before_epoch
    body = health(home)
    assert body["epoch"] == before_epoch
    assert body["cdc_source"] == "wal"


def test_f2p_duplicate_sku_code_rejects(home: Path) -> None:
    """Duplicate visible (tenant_id, sku_code) is UNIQUE_CONFLICT with WAL ABORT."""
    before_len = len(wal_records(home))
    proc = run_ctl(home, "commit", "--input", str(FIXTURES / "dup_sku.jsonl"))
    assert proc.returncode == 0
    lines = (home / "out" / "rejects.jsonl").read_text(encoding="utf-8").strip().splitlines()
    assert lines
    body = json.loads(lines[-1])
    assert body["code"] == "UNIQUE_CONFLICT"
    assert "txn_id" in body and "table" in body and "pk" in body and "detail" in body
    recs = wal_records(home)
    assert len(recs) > before_len
    aborts = [r for r in recs if r.get("kind") == "ABORT"]
    assert aborts
    assert any(r.get("txn_id") == body["txn_id"] for r in aborts)


def test_f2p_missing_offer_fk_rejects(home: Path) -> None:
    """A hold against a missing offer is FK_MISSING."""
    proc = run_ctl(home, "commit", "--input", str(FIXTURES / "fk_hold.jsonl"))
    assert proc.returncode == 0
    body = json.loads((home / "out" / "rejects.jsonl").read_text(encoding="utf-8").strip().splitlines()[-1])
    assert body["code"] == "FK_MISSING"


def test_f2p_frozen_tenant_rejects_offer(home: Path) -> None:
    """FROZEN tenants reject new offers."""
    proc = run_ctl(home, "commit", "--input", str(FIXTURES / "frozen_offer.jsonl"))
    assert proc.returncode == 0
    body = json.loads((home / "out" / "rejects.jsonl").read_text(encoding="utf-8").strip().splitlines()[-1])
    assert body["code"] == "FROZEN_TENANT"


def test_f2p_hold_qty_rejects(home: Path) -> None:
    """Hold qty that exceeds offer on-hand is HOLD_QTY."""
    proc = run_ctl(home, "commit", "--input", str(FIXTURES / "hold_qty.jsonl"))
    assert proc.returncode == 0
    body = json.loads((home / "out" / "rejects.jsonl").read_text(encoding="utf-8").strip().splitlines()[-1])
    assert body["code"] == "HOLD_QTY"


def test_f2p_same_txn_parent_then_child(home: Path) -> None:
    """Writer snapshot plus write set allows offer+sku in one commit regardless of file order."""
    proc = run_ctl(home, "commit", "--input", str(FIXTURES / "parent_child.jsonl"))
    assert proc.returncode == 0
    rejects = home / "out" / "rejects.jsonl"
    assert not rejects.is_file() or rejects.stat().st_size == 0
    engine = sqlite3.connect(str(home / "data" / "engine.sqlite"))
    sku = engine.execute(
        "SELECT COUNT(*) FROM row_version WHERE pk = 's-t00-new2' AND committed = 1 AND xmax IS NULL"
    ).fetchone()[0]
    offer = engine.execute(
        "SELECT COUNT(*) FROM row_version WHERE pk = 'o-child' AND committed = 1 AND xmax IS NULL"
    ).fetchone()[0]
    engine.close()
    assert sku == 1 and offer == 1


def test_f2p_recover_skips_uncommitted(home: Path) -> None:
    """Crash INSERT without COMMIT must not remain on the heap after recover."""
    proc = run_ctl(home, "recover")
    assert proc.returncode == 0
    engine = sqlite3.connect(str(home / "data" / "engine.sqlite"))
    count = engine.execute(
        "SELECT COUNT(*) FROM row_version WHERE pk = 's-crash-pending'"
    ).fetchone()[0]
    engine.close()
    assert count == 0


def test_f2p_recover_does_not_bump_epoch(home: Path) -> None:
    """recover must keep the replica slot epoch."""
    before = slot(home)["epoch"]
    proc = run_ctl(home, "recover")
    assert proc.returncode == 0
    assert slot(home)["epoch"] == before


def test_f2p_decode_skips_uncommitted(home: Path) -> None:
    """CDC decode must not emit the crash pending sku."""
    run_ctl(home, "recover")
    proc = run_ctl(home, "decode")
    assert proc.returncode == 0
    text = (home / "out" / "cdc.jsonl").read_text(encoding="utf-8")
    assert "s-crash-pending" not in text
    assert "CRASH" not in text


def test_f2p_recover_redoes_committed_after_checkpoint(home: Path) -> None:
    """Recover must redo a committed WAL mutation recorded after checkpoint.lsn."""
    proc = run_ctl(home, "commit", "--input", str(FIXTURES / "insert_sku.jsonl"))
    assert proc.returncode == 0
    engine = sqlite3.connect(str(home / "data" / "engine.sqlite"))
    engine.execute("DELETE FROM row_version WHERE pk = 's-t00-new'")
    engine.commit()
    engine.close()
    proc = run_ctl(home, "recover")
    assert proc.returncode == 0
    engine = sqlite3.connect(str(home / "data" / "engine.sqlite"))
    count = engine.execute(
        "SELECT COUNT(*) FROM row_version WHERE pk = 's-t00-new' AND committed = 1 AND xmax IS NULL"
    ).fetchone()[0]
    engine.close()
    assert count == 1
    indexes = json.loads((home / "data" / "indexes.json").read_text(encoding="utf-8"))
    assert indexes["sku_code"].get("t00\0NEW00") == "s-t00-new"


def test_f2p_decode_does_not_apply(home: Path) -> None:
    """decode must not change replica bytes or the replica slot."""
    before_slot = (home / "data" / "replica_slot.json").read_bytes()
    before_replica = (home / "data" / "replica.sqlite").read_bytes()
    proc = run_ctl(home, "decode")
    assert proc.returncode == 0
    assert (home / "data" / "replica_slot.json").read_bytes() == before_slot
    assert (home / "data" / "replica.sqlite").read_bytes() == before_replica


def test_f2p_decode_uses_wal_lsn(home: Path) -> None:
    """CDC lsn/pk pairs match committed WAL mutations, not heap row numbers."""
    run_ctl(home, "recover")
    proc = run_ctl(home, "decode")
    assert proc.returncode == 0
    wal = wal_records(home)
    committed = {r["txn_id"] for r in wal if r.get("kind") == "COMMIT"}
    wal_mut = {
        (int(r["lsn"]), r.get("pk"))
        for r in wal
        if r.get("kind") in {"INSERT", "UPDATE", "DELETE"} and r.get("txn_id") in committed
    }
    lines = [
        json.loads(line)
        for line in (home / "out" / "cdc.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert lines
    confirmed = slot(home)["confirmed_lsn"]
    for item in lines:
        assert (int(item["lsn"]), item["pk"]) in wal_mut
        assert int(item["lsn"]) > confirmed
    lsns = [item["lsn"] for item in lines]
    assert lsns == sorted(lsns)


def test_f2p_apply_is_monotonic(home: Path) -> None:
    """First apply of lagged CDC advances confirmed_lsn; a second apply only skips."""
    run_ctl(home, "recover")
    run_ctl(home, "decode")
    before = slot(home)["confirmed_lsn"]
    first = run_ctl(home, "apply")
    assert first.returncode == 0
    report1 = json.loads((home / "out" / "apply-report.json").read_text(encoding="utf-8"))
    confirmed = slot(home)["confirmed_lsn"]
    assert report1["applied"] >= 1
    assert confirmed > before
    second = run_ctl(home, "apply")
    assert second.returncode == 0
    report = json.loads((home / "out" / "apply-report.json").read_text(encoding="utf-8"))
    assert slot(home)["confirmed_lsn"] == confirmed
    assert report["confirmed_lsn"] == confirmed
    assert report["skipped"] >= 1
    assert report["applied"] == 0


def test_f2p_stale_epoch_rejects_batch(home: Path) -> None:
    """A CDC batch with the wrong epoch applies nothing and does not advance confirmed_lsn."""
    before = slot(home)["confirmed_lsn"]
    cdc = home / "out" / "cdc.jsonl"
    cdc.parent.mkdir(parents=True, exist_ok=True)
    cdc.write_text(
        json.dumps(
            {
                "lsn": before + 10,
                "txn_id": 1,
                "epoch": before + 99,
                "table": "sku",
                "op": "insert",
                "pk": "s-stale",
                "before": None,
                "after": {"sku_id": "s-stale", "tenant_id": "t00", "sku_code": "STALE"},
            }
        )
        + "\n",
        encoding="utf-8",
    )
    proc = run_ctl(home, "apply", "--cdc", str(cdc))
    assert proc.returncode == 0
    report = json.loads((home / "out" / "apply-report.json").read_text(encoding="utf-8"))
    assert report["rejected"] >= 1
    assert report["applied"] == 0
    assert slot(home)["confirmed_lsn"] == before
    replica = sqlite3.connect(str(home / "data" / "replica.sqlite"))
    count = replica.execute("SELECT COUNT(*) FROM sku WHERE sku_id = 's-stale'").fetchone()[0]
    replica.close()
    assert count == 0


def test_f2p_apply_fk_order(home: Path) -> None:
    """Records that share a txn apply parent sku before child offer."""
    run_ctl(home, "recover")
    run_ctl(home, "commit", "--input", str(FIXTURES / "parent_child.jsonl"))
    run_ctl(home, "decode")
    proc = run_ctl(home, "apply")
    assert proc.returncode == 0
    replica = sqlite3.connect(str(home / "data" / "replica.sqlite"))
    sku = replica.execute("SELECT COUNT(*) FROM sku WHERE sku_id = 's-t00-new2'").fetchone()[0]
    offer = replica.execute("SELECT COUNT(*) FROM offer WHERE offer_id = 'o-child'").fetchone()[0]
    replica.close()
    assert sku == 1 and offer == 1


def test_f2p_indexes_match_after_commit(home: Path) -> None:
    """sku_code index contains the committed insert and not rejects."""
    run_ctl(home, "commit", "--input", str(FIXTURES / "insert_sku.jsonl"))
    indexes = json.loads((home / "data" / "indexes.json").read_text(encoding="utf-8"))
    key = "t00\0NEW00"
    assert indexes["sku_code"].get(key) == "s-t00-new"


def test_p2p_health_schema(home: Path) -> None:
    """Successful inspect writes the contracted health fields."""
    proc = run_ctl(home, "inspect")
    assert proc.returncode == 0
    body = health(home)
    for key in (
        "generated_at",
        "epoch",
        "durable_lsn",
        "checkpoint_lsn",
        "replica_confirmed_lsn",
        "replica_epoch",
        "heap_visible_count",
        "cdc_source",
        "index_ok",
        "visibility_ok",
        "constraints_ok",
        "replica_ok",
        "recovery_ok",
        "healthy",
    ):
        assert key in body
    assert body["cdc_source"] == "wal"
    assert isinstance(body["epoch"], int)
    assert isinstance(body["durable_lsn"], int)


def test_f2p_decode_update_has_before(home: Path) -> None:
    """Committed offer updates in WAL decode with op=update and a before image."""
    run_ctl(home, "recover")
    proc = run_ctl(home, "decode")
    assert proc.returncode == 0
    updates = [
        json.loads(line)
        for line in (home / "out" / "cdc.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip() and json.loads(line).get("op") == "update"
    ]
    assert updates
    assert updates[0]["before"] is not None
    assert updates[0]["after"] is not None


def test_p2p_ctl_exists() -> None:
    """Public operator binary is present and executable."""
    assert CTL.is_file()
    assert os.access(CTL, os.X_OK)


def test_p2p_contract_exists() -> None:
    """Binding contract is present on the transferred tree."""
    assert (APP / "docs" / "catalog-contract.md").is_file()


def test_f2p_unknown_command_leaves_wal(home: Path) -> None:
    """Unknown commands exit 2 before appending WAL."""
    before = wal_bytes(home)
    proc = run_ctl(home, "not-a-command")
    assert proc.returncode == 2
    assert wal_bytes(home) == before


def test_f2p_reject_does_not_install_row(home: Path) -> None:
    """A unique conflict aborts without installing the conflicting pk."""
    proc = run_ctl(home, "commit", "--input", str(FIXTURES / "dup_sku.jsonl"))
    assert proc.returncode == 0
    engine = sqlite3.connect(str(home / "data" / "engine.sqlite"))
    count = engine.execute(
        "SELECT COUNT(*) FROM row_version WHERE pk = 's-t00-dup'"
    ).fetchone()[0]
    engine.close()
    assert count == 0


def test_f2p_recovery_ok_after_recover(home: Path) -> None:
    """After recover, health.recovery_ok is true because uncommitted WAL is not on the heap."""
    proc = run_ctl(home, "recover")
    assert proc.returncode == 0
    body = health(home)
    assert body["recovery_ok"] is True


def test_p2p_apply_report_integers(home: Path) -> None:
    """apply-report fields are integers including epoch."""
    run_ctl(home, "recover")
    run_ctl(home, "decode")
    proc = run_ctl(home, "apply")
    assert proc.returncode == 0
    report = json.loads((home / "out" / "apply-report.json").read_text(encoding="utf-8"))
    for key in ("applied", "skipped", "rejected", "confirmed_lsn", "epoch"):
        assert isinstance(report[key], int)


def test_p2p_health_replica_epoch_matches_slot(home: Path) -> None:
    """health.epoch and replica_epoch equal the slot epoch."""
    proc = run_ctl(home, "inspect")
    assert proc.returncode == 0
    body = health(home)
    assert body["epoch"] == slot(home)["epoch"]
    assert body["replica_epoch"] == slot(home)["epoch"]


def test_f2p_indexes_rebuild_after_recover(home: Path) -> None:
    """recover rebuilds sku_code from committed-visible rows, not the crash pk."""
    proc = run_ctl(home, "recover")
    assert proc.returncode == 0
    indexes = json.loads((home / "data" / "indexes.json").read_text(encoding="utf-8"))
    assert "s-crash-pending" not in indexes["sku_code"].values()
    assert indexes["sku_code"]


def test_f2p_visibility_ok_after_recover(home: Path) -> None:
    """After recover, health.visibility_ok is true because uncommitted rows are gone."""
    proc = run_ctl(home, "recover")
    assert proc.returncode == 0
    body = health(home)
    assert body["visibility_ok"] is True


def test_f2p_index_ok_after_recover(home: Path) -> None:
    """After recover, health.index_ok matches committed-visible secondary indexes."""
    proc = run_ctl(home, "recover")
    assert proc.returncode == 0
    body = health(home)
    assert body["index_ok"] is True


def test_p2p_warehouse_untouched(home: Path) -> None:
    """Commit/decode/apply leave the warehouse dump bytes unchanged."""
    before = warehouse_digest()
    run_ctl(home, "commit", "--input", str(FIXTURES / "insert_sku.jsonl"))
    run_ctl(home, "decode")
    run_ctl(home, "apply")
    assert hashlib.sha256((home / "warehouse" / "inventory.sqlite").read_bytes()).hexdigest() == before
    assert warehouse_digest() == before


def test_p2p_go_module() -> None:
    """catalogctl is a built Go binary and the catalog module stays on the tree."""
    assert CTL.is_file()
    assert os.access(CTL, os.X_OK)
    assert not CTL.read_bytes().startswith(b"#!")
    gomod = APP / "go.mod"
    assert gomod.is_file()
    assert "module catalog" in gomod.read_text(encoding="utf-8")
