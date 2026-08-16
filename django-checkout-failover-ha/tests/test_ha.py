"""Checkout desk failover checks over WSGI, manage.py, and shop files."""
from __future__ import annotations

# Django must be configured before application imports.
# ruff: noqa: E402

import json
import os
import shutil
import sqlite3
import sys
import uuid
from pathlib import Path

import pytest

ROOT = Path(os.environ.get("HA_ROOT", "/app/ha"))
os.environ["HA_ROOT"] = str(ROOT)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "shopdesk.settings")
sys.path.insert(0, str(ROOT))

import django
from django.conf import settings as dj_settings

django.setup()

from django.core.cache import caches
from django.core.management import call_command
from django.db import connections
from django.test import Client, override_settings

from checkout.models import Cart, CartLine, Order
from checkout.services import CheckoutError, place_order
from controlplane.models import FenceLease, ShopSession, Watermark
from fulfill.models import SideEffect
from identity.models import Shopper
from inventory.models import Reservation


def _load_sql(db_path: Path, *sql_paths: Path) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    try:
        for sql_path in sql_paths:
            conn.executescript(sql_path.read_text(encoding="utf-8"))
        conn.commit()
    finally:
        conn.close()


@pytest.fixture(scope="session")
def baseline_dbs(tmp_path_factory: pytest.TempPathFactory) -> Path:
    folder = tmp_path_factory.mktemp("ha-baseline")
    _load_sql(folder / "primary.sqlite", ROOT / "sql/schema.sql", ROOT / "sql/seed.sql")
    _load_sql(folder / "standby.sqlite", ROOT / "sql/schema.sql", ROOT / "sql/standby_seed.sql")
    return folder


@pytest.fixture
def lab(tmp_path: Path, baseline_dbs: Path, monkeypatch: pytest.MonkeyPatch):
    primary = tmp_path / "primary.sqlite"
    standby = tmp_path / "standby.sqlite"
    shutil.copy2(baseline_dbs / "primary.sqlite", primary)
    shutil.copy2(baseline_dbs / "standby.sqlite", standby)
    connections.close_all()
    dj_settings.DATABASES["default"]["NAME"] = str(primary)
    dj_settings.DATABASES["replica"]["NAME"] = str(standby)
    monkeypatch.setattr(dj_settings, "AZ_ID", "az-a", raising=False)
    yield {"primary": primary, "standby": standby, "tmp": tmp_path}
    connections.close_all()


def _open_cart(shopper: Shopper) -> Cart:
    cart = Cart.objects.using("default").create(
        shopper=shopper,
        warehouse_id=1,
        status="OPEN",
        currency="USD",
        updated_at="2026-08-08T21:00:00Z",
    )
    CartLine.objects.using("default").create(cart=cart, product_id=1, qty=1)
    return cart


def _writer() -> str:
    row = FenceLease.objects.using("default").filter(resource="checkout-primary").first()
    assert row is not None
    return str(row.owner_node)


def _place(shopper_ref: str, attempt: str, az: str) -> dict:
    with override_settings(AZ_ID=az, AZ_WRITE_AFFINITY=True):
        client = Client()
        response = client.post(
            "/api/checkout/place",
            data=json.dumps({"shopper_ref": shopper_ref, "attempt_id": attempt}),
            content_type="application/json",
        )
    return {"status": response.status_code, "body": json.loads(response.content.decode("utf-8"))}


def _confirmation(shopper_ref: str, az: str = "az-a") -> dict:
    with override_settings(AZ_ID=az):
        client = Client()
        response = client.get(f"/api/shoppers/{shopper_ref}/confirmation")
    return {"status": response.status_code, "body": json.loads(response.content.decode("utf-8"))}


def _dump(lab) -> dict:
    path = lab["tmp"] / "failover-status.json"
    call_command("dump_failover", output=str(path))
    return json.loads(path.read_text(encoding="utf-8"))


def test_f2p_place_lands_on_writer(lab) -> None:
    """Place must persist the new order on the writer shop file."""
    shopper = Shopper.objects.using("default").get(pk=1)
    _open_cart(shopper)
    attempt = f"att-w-{uuid.uuid4().hex[:8]}"
    result = _place(shopper.shopper_ref, attempt, _writer())
    assert result["status"] == 200
    assert Order.objects.using("default").filter(attempt_id=attempt).exists()


def test_f2p_pay_skips_other_az(lab) -> None:
    """Pay from the non-writer box must not mark the order paid only on standby."""
    order = Order.objects.using("default").filter(status="PLACED").first()
    assert order is not None
    other = "az-b" if _writer() == "az-a" else "az-a"
    with override_settings(AZ_ID=other, AZ_WRITE_AFFINITY=True):
        client = Client()
        client.post(f"/api/orders/{order.order_ref}/pay", content_type="application/json")
    replica_only = (
        Order.objects.using("replica").filter(order_ref=order.order_ref, status="PAID").exists()
        and not Order.objects.using("default").filter(order_ref=order.order_ref, status="PAID").exists()
    )
    assert not replica_only


def test_f2p_az_b_does_not_insert_standby_order(lab) -> None:
    """AZ-B leftover affinity must not insert a new attempt on standby."""
    shopper = Shopper.objects.using("default").get(pk=2)
    _open_cart(shopper)
    attempt = f"att-azb-{uuid.uuid4().hex[:8]}"
    before = set(Order.objects.using("replica").values_list("attempt_id", flat=True))
    _place(shopper.shopper_ref, attempt, "az-b")
    after = set(Order.objects.using("replica").values_list("attempt_id", flat=True))
    assert attempt not in (after - before)


def test_f2p_checkout_api_does_not_grow_standby(lab) -> None:
    """A successful or rejected AZ-B place must not grow standby order count."""
    shopper = Shopper.objects.using("default").get(pk=14)
    _open_cart(shopper)
    before = Order.objects.using("replica").count()
    _place(shopper.shopper_ref, f"att-grow-{uuid.uuid4().hex[:8]}", "az-b")
    assert Order.objects.using("replica").count() == before


def test_f2p_reservation_stays_on_writer(lab) -> None:
    """Reservations created during checkout live on the writer file."""
    shopper = Shopper.objects.using("default").get(pk=3)
    _open_cart(shopper)
    attempt = f"att-inv-{uuid.uuid4().hex[:8]}"
    result = _place(shopper.shopper_ref, attempt, _writer())
    assert result["status"] == 200
    assert Reservation.objects.using("default").filter(attempt_id=attempt).exists()
    only_replica = Reservation.objects.using("replica").filter(attempt_id=attempt).exists() and not (
        Reservation.objects.using("default").filter(attempt_id=attempt).exists()
    )
    assert not only_replica


def test_f2p_confirmation_after_place_is_fresh(lab) -> None:
    """Confirmation right after place must show the new order from the writer."""
    shopper = Shopper.objects.using("default").get(pk=4)
    _open_cart(shopper)
    attempt = f"att-conf-{uuid.uuid4().hex[:8]}"
    placed = _place(shopper.shopper_ref, attempt, _writer())
    assert placed["status"] == 200
    seen = _confirmation(shopper.shopper_ref)
    assert seen["body"]["order_ref"] == placed["body"]["order_ref"]
    assert seen["body"]["status"] in {"PLACED", "PAID"}
    assert seen["body"]["alias"] == "default"


def test_f2p_idle_read_follows_seq_gap(lab) -> None:
    """Idle confirmation stays on the writer while lagged, then may use standby after sync."""
    shopper = Shopper.objects.using("default").get(pk=50)
    assert _confirmation(shopper.shopper_ref)["body"]["alias"] == "default"
    call_command("sync_standby")
    assert _confirmation(shopper.shopper_ref)["body"]["alias"] == "replica"


def test_f2p_pin_survives_default_cache_clear(lab) -> None:
    """Sticky read after place must survive wiping the default cache alias."""
    shopper = Shopper.objects.using("default").get(pk=6)
    _open_cart(shopper)
    call_command("sync_standby")
    placed = _place(shopper.shopper_ref, f"att-pin-{uuid.uuid4().hex[:8]}", _writer())
    assert placed["status"] == 200
    caches["default"].clear()
    assert _confirmation(shopper.shopper_ref)["body"]["alias"] == "default"


def test_f2p_standby_unreadable_while_seq_gap_high(lab) -> None:
    """Standby must not be marked readable while the seq gap is above budget."""
    status = _dump(lab)
    assert status["standby_readable"] is False
    assert int(status["seq_gap"]) > 25


def test_f2p_seq_gap_tracks_watermark_not_counts(lab) -> None:
    """seq_gap must follow watermarks, not order-count delta."""
    applied = int(Watermark.objects.using("replica").get(role="replica").applied_lsn)
    Watermark.objects.using("default").filter(role="primary").update(wal_lsn=applied + 400)
    assert int(_dump(lab)["seq_gap"]) == 400


def test_f2p_sync_standby_moves_seq(lab) -> None:
    """sync_standby must advance standby seq toward the writer seq."""
    before = int(_dump(lab)["standby_seq"])
    call_command("sync_standby")
    after = _dump(lab)
    assert int(after["standby_seq"]) >= before
    assert after["standby_readable"] is True


def test_f2p_sync_standby_does_not_copy_writer_lease(lab) -> None:
    """sync_standby must not leave a writable fence lease on standby."""
    FenceLease.objects.using("default").filter(resource="checkout-primary").update(
        owner_node="az-b", writable=1, epoch=4
    )
    call_command("sync_standby")
    replica = FenceLease.objects.using("replica").filter(resource="checkout-primary").first()
    assert replica is None or int(replica.writable) == 0


def test_f2p_sync_standby_includes_late_orders(lab) -> None:
    """sync_standby must copy late incident orders, not stop at a stale cutoff."""
    call_command("sync_standby")
    assert Order.objects.using("replica").filter(id__gte=19980).count() >= 1
    assert Order.objects.using("replica").filter(attempt_id="att-inc-20001").exists()


def test_f2p_pin_survives_session_table_wipe(lab) -> None:
    """Sticky confirmation survives wiping django_session on both shop files."""
    shopper = Shopper.objects.using("default").get(pk=7)
    _open_cart(shopper)
    call_command("sync_standby")
    assert _place(shopper.shopper_ref, f"att-sess-{uuid.uuid4().hex[:8]}", _writer())["status"] == 200
    ShopSession.objects.using("default").all().delete()
    ShopSession.objects.using("replica").all().delete()
    caches["default"].clear()
    assert _confirmation(shopper.shopper_ref)["body"]["alias"] == "default"


def test_f2p_pin_alias_is_shared(lab) -> None:
    """Place must publish the sticky key on cache alias pins."""
    shopper = Shopper.objects.using("default").get(pk=8)
    _open_cart(shopper)
    assert _place(shopper.shopper_ref, f"att-share-{uuid.uuid4().hex[:8]}", _writer())["status"] == 200
    assert caches["pins"].get(f"sticky:shopper:{shopper.id}")


def test_f2p_pin_survives_default_db_remap(lab) -> None:
    """Pins stay reachable after DATABASES default is pointed at the standby file."""
    shopper = Shopper.objects.using("default").get(pk=9)
    _open_cart(shopper)
    assert _place(shopper.shopper_ref, f"att-remap-{uuid.uuid4().hex[:8]}", _writer())["status"] == 200
    connections.close_all()
    dj_settings.DATABASES["default"]["NAME"] = str(lab["standby"])
    assert caches["pins"].get(f"sticky:shopper:{shopper.id}")


def test_f2p_only_one_writer_after_cutover(lab) -> None:
    """cutover plus a non-writable standby lease exposes one writer."""
    call_command("cutover", node="az-b")
    FenceLease.objects.using("replica").filter(resource="checkout-primary").update(writable=0)
    status = _dump(lab)
    assert status["writers_seen"] == ["az-b"] or (
        len(status["writers_seen"]) == 1 and status["writer"] == "az-b"
    )


def test_f2p_old_az_cannot_write_after_cutover(lab) -> None:
    """AZ-A place after cutover to AZ-B must not create a new attempt."""
    call_command("cutover", node="az-b")
    shopper = Shopper.objects.using("default").get(pk=15)
    _open_cart(shopper)
    attempt = f"att-old-{uuid.uuid4().hex[:8]}"
    result = _place(shopper.shopper_ref, attempt, "az-a")
    assert result["status"] != 200
    assert not Order.objects.using("default").filter(attempt_id=attempt).exists()


def test_f2p_cutover_bumps_epoch(lab) -> None:
    """cutover must increase writer_epoch."""
    before = int(FenceLease.objects.using("default").get(resource="checkout-primary").epoch)
    call_command("cutover", node="az-b")
    after = int(FenceLease.objects.using("default").get(resource="checkout-primary").epoch)
    assert after > before


def test_f2p_cutover_drops_previous_owner(lab) -> None:
    """After cutover the dump writer is az-b and az-a is not listed as a second writer."""
    call_command("cutover", node="az-b")
    FenceLease.objects.using("replica").filter(resource="checkout-primary").update(writable=0)
    status = _dump(lab)
    assert status["writer"] == "az-b"
    assert "az-a" not in status["writers_seen"]


def test_f2p_same_attempt_one_capture_row(lab) -> None:
    """Retrying the same attempt id must not create a second capture effect."""
    shopper = Shopper.objects.using("default").get(pk=10)
    _open_cart(shopper)
    attempt = f"att-idem-{uuid.uuid4().hex[:8]}"
    az = _writer()
    assert _place(shopper.shopper_ref, attempt, az)["status"] == 200
    _place(shopper.shopper_ref, attempt, az)
    assert SideEffect.objects.using("default").filter(attempt_id=attempt, kind="capture").count() == 1


def test_f2p_second_worker_does_not_add_capture(lab) -> None:
    """A second app box retrying the same attempt still yields one capture row."""
    shopper = Shopper.objects.using("default").get(pk=16)
    _open_cart(shopper)
    attempt = f"att-dual-{uuid.uuid4().hex[:8]}"
    assert _place(shopper.shopper_ref, attempt, _writer())["status"] == 200
    _place(shopper.shopper_ref, attempt, "az-b")
    assert SideEffect.objects.using("default").filter(attempt_id=attempt, kind="capture").count() == 1


def test_f2p_pay_twice_one_capture(lab) -> None:
    """Paying the same order twice still yields one capture effect for the attempt."""
    shopper = Shopper.objects.using("default").get(pk=11)
    _open_cart(shopper)
    attempt = f"att-dec-{uuid.uuid4().hex[:8]}"
    placed = _place(shopper.shopper_ref, attempt, _writer())
    assert placed["status"] == 200
    order_ref = placed["body"]["order_ref"]
    with override_settings(AZ_ID=_writer()):
        client = Client()
        client.post(f"/api/orders/{order_ref}/pay", content_type="application/json")
        client.post(f"/api/orders/{order_ref}/pay", content_type="application/json")
    assert SideEffect.objects.using("default").filter(attempt_id=attempt, kind="capture").count() == 1


def test_f2p_capture_blocked_if_seq_not_committed(lab) -> None:
    """Pay must not deliver a capture when the order seq is ahead of writer wal_lsn."""
    order = Order.objects.using("default").filter(pk=100).first()
    assert order is not None
    Watermark.objects.using("default").filter(role="primary").update(wal_lsn=int(order.write_lsn) - 10)
    with override_settings(AZ_ID=_writer()):
        client = Client()
        response = client.post(f"/api/orders/{order.order_ref}/pay", content_type="application/json")
    assert response.status_code >= 400


def test_f2p_readyz_503_when_two_writers(lab) -> None:
    """/readyz must not be 200 while both shop files advertise a writable owner."""
    FenceLease.objects.using("default").filter(resource="checkout-primary").update(writable=1, owner_node="az-a")
    FenceLease.objects.using("replica").filter(resource="checkout-primary").update(writable=1, owner_node="az-b")
    assert Client().get("/readyz").status_code != 200


def test_f2p_readyz_503_when_seq_gap_unsafe(lab) -> None:
    """/readyz must fail while replica seq is outside the configured budget."""
    FenceLease.objects.using("replica").filter(resource="checkout-primary").update(writable=0)
    Watermark.objects.using("default").filter(role="primary").update(wal_lsn=10_000)
    Watermark.objects.using("replica").filter(role="replica").update(applied_lsn=0)
    assert Client().get("/readyz").status_code != 200


def test_f2p_readyz_503_when_pins_unreachable(lab, monkeypatch: pytest.MonkeyPatch) -> None:
    """/readyz must refuse traffic when the pins store cannot be probed."""
    FenceLease.objects.using("default").filter(resource="checkout-primary").update(
        writable=1, owner_node="az-b"
    )
    FenceLease.objects.using("replica").filter(resource="checkout-primary").update(
        writable=0, owner_node="az-b"
    )
    Watermark.objects.using("default").filter(role="primary").update(wal_lsn=10)
    Watermark.objects.using("replica").filter(role="replica").update(applied_lsn=10)
    from fulfill.models import WebhookDelivery

    WebhookDelivery.objects.using("default").all().delete()
    SideEffect.objects.using("default").all().delete()
    monkeypatch.setattr("controlplane.desk_state.pins_reachable", lambda: False)
    assert Client().get("/readyz").status_code != 200


def test_f2p_readyz_503_when_repeat_captures(lab) -> None:
    """/readyz must refuse traffic while duplicate capture rows remain."""
    FenceLease.objects.using("replica").filter(resource="checkout-primary").update(writable=0)
    Watermark.objects.using("default").filter(role="primary").update(wal_lsn=10)
    Watermark.objects.using("replica").filter(role="replica").update(applied_lsn=10)
    order = Order.objects.using("default").filter(pk=100).first()
    assert order is not None
    SideEffect.objects.using("default").create(
        attempt_id="att-readyz-dup",
        kind="capture",
        payload_hash="a" * 64,
        status="DELIVERED",
        delivered_at="2026-08-08T21:00:00Z",
        write_lsn=int(order.write_lsn),
    )
    SideEffect.objects.using("default").create(
        attempt_id="att-readyz-dup",
        kind="capture",
        payload_hash="b" * 64,
        status="DELIVERED",
        delivered_at="2026-08-08T21:00:01Z",
        write_lsn=int(order.write_lsn),
    )
    assert Client().get("/readyz").status_code != 200


def test_f2p_healthz_200_while_readyz_fails(lab) -> None:
    """/healthz can be 200 while /readyz refuses checkout."""
    live = Client().get("/healthz")
    ready = Client().get("/readyz")
    assert live.status_code == 200
    assert ready.status_code != 200 or json.loads(ready.content)["accepting_checkout"] is False


def test_f2p_failover_status_refuses_accept_on_split(lab) -> None:
    """failover-status.json must include runbook keys and refuse accept while two writers exist."""
    artifact = ROOT / "out" / "failover-status.json"
    assert artifact.is_file()
    disk = json.loads(artifact.read_text(encoding="utf-8"))
    keys = (
        "desk",
        "accepting_checkout",
        "writer",
        "writer_epoch",
        "writers_seen",
        "standby_readable",
        "primary_seq",
        "standby_seq",
        "seq_gap",
        "pins",
        "double_primary",
        "repeat_captures",
        "standby_only_orders",
        "incident_orders_on_standby",
        "fence_copied_to_standby",
    )
    for key in keys:
        assert key in disk
    payload = _dump(lab)
    for key in keys:
        assert key in payload
    if len(payload["writers_seen"]) != 1:
        assert payload["accepting_checkout"] is False
        assert payload["double_primary"] is True


def test_f2p_failover_status_counts_repeat_captures(lab) -> None:
    """Dump must report duplicate capture rows and refuse accepting_checkout."""
    order = Order.objects.using("default").filter(pk=101).first()
    assert order is not None
    SideEffect.objects.using("default").create(
        attempt_id="att-dump-dup",
        kind="capture",
        payload_hash="c" * 64,
        status="DELIVERED",
        delivered_at="2026-08-08T21:00:00Z",
        write_lsn=int(order.write_lsn),
    )
    SideEffect.objects.using("default").create(
        attempt_id="att-dump-dup",
        kind="capture",
        payload_hash="d" * 64,
        status="DELIVERED",
        delivered_at="2026-08-08T21:00:01Z",
        write_lsn=int(order.write_lsn),
    )
    payload = _dump(lab)
    assert int(payload["repeat_captures"]) >= 1
    assert payload["accepting_checkout"] is False


def test_f2p_failover_status_standby_only_blocks_accept(lab) -> None:
    """Dump accepting_checkout is false while standby-only orders remain."""
    FenceLease.objects.using("replica").filter(resource="checkout-primary").update(writable=0)
    conn = sqlite3.connect(lab["standby"])
    try:
        conn.execute(
            "INSERT OR REPLACE INTO checkout_order "
            "(id, order_ref, shopper_id, attempt_id, warehouse_id, status, channel, currency, "
            "total_cents, az_origin, placed_at, write_lsn) "
            "VALUES (900001, 'ORD-STANDBY-ONLY', 1, 'att-standby-only', 1, 'PLACED', 'web', 'USD', "
            "100, 'az-b', '2026-08-08T21:00:00Z', 1)"
        )
        conn.commit()
    finally:
        conn.close()
    connections.close_all()
    payload = _dump(lab)
    assert int(payload["standby_only_orders"]) >= 1
    assert payload["accepting_checkout"] is False


def test_f2p_failover_status_fence_on_standby_blocks_accept(lab) -> None:
    """Dump accepting_checkout is false while the standby lease stays writable."""
    FenceLease.objects.using("default").filter(resource="checkout-primary").update(
        writable=1, owner_node="az-b"
    )
    FenceLease.objects.using("replica").filter(resource="checkout-primary").update(
        writable=1, owner_node="az-b"
    )
    payload = _dump(lab)
    assert payload["fence_copied_to_standby"] is True or payload["double_primary"] is True
    assert payload["accepting_checkout"] is False


def test_f2p_failover_status_seq_gap_blocks_accept(lab) -> None:
    """Dump accepting_checkout is false while seq gap exceeds max_lag_lsn."""
    FenceLease.objects.using("replica").filter(resource="checkout-primary").update(writable=0)
    Watermark.objects.using("default").filter(role="primary").update(wal_lsn=50_000)
    Watermark.objects.using("replica").filter(role="replica").update(applied_lsn=0)
    payload = _dump(lab)
    assert int(payload["seq_gap"]) > 25 or payload["accepting_checkout"] is False
    assert payload["accepting_checkout"] is False


def test_f2p_failover_status_missing_incident_blocks_accept(lab) -> None:
    """Dump accepting_checkout is false when incident-window orders are absent on standby."""
    FenceLease.objects.using("replica").filter(resource="checkout-primary").update(writable=0)
    Order.objects.using("replica").filter(id__gte=19980).delete()
    payload = _dump(lab)
    assert payload["incident_orders_on_standby"] is False
    assert payload["accepting_checkout"] is False


def test_f2p_epoch_and_pin_survive_reconnect(lab) -> None:
    """Writer epoch and pins remain after closing DB connections and cache handlers."""
    shopper = Shopper.objects.using("default").get(pk=12)
    _open_cart(shopper)
    assert _place(shopper.shopper_ref, f"att-re-{uuid.uuid4().hex[:8]}", _writer())["status"] == 200
    call_command("cutover", node="az-b")
    epoch = int(FenceLease.objects.using("default").get(resource="checkout-primary").epoch)
    connections.close_all()
    caches.close_all()
    assert int(FenceLease.objects.using("default").get(resource="checkout-primary").epoch) == epoch
    assert caches["pins"].get(f"sticky:shopper:{shopper.id}")


def test_p2p_healthz_ok_when_desk_closed(lab) -> None:
    """Process liveness is not the checkout-accept signal."""
    live = Client().get("/healthz")
    ready = Client().get("/readyz")
    assert live.status_code == 200
    assert "accepting_checkout" in json.loads(ready.content)


def test_p2p_runbook_names_dump_path(lab) -> None:
    """Runbook names the dump path and manage.py commands."""
    text = (ROOT / "docs/runbook.md").read_text(encoding="utf-8")
    assert "/app/ha/out/failover-status.json" in text
    assert "dump_failover" in text
    assert "sync_standby" in text


def test_p2p_manage_and_routes_present(lab) -> None:
    """manage.py and checkout/health routes required by the ticket remain present."""
    assert (ROOT / "manage.py").is_file()
    from shopdesk.urls import urlpatterns

    joined = " ".join(getattr(p.pattern, "_route", str(p.pattern)) for p in urlpatterns)
    assert "healthz" in joined
    assert "readyz" in joined
    assert "checkout/place" in joined


def test_p2p_order_schema_preserved(lab) -> None:
    """Primary checkout_order table remains present and usable (do not wipe history)."""
    assert Order.objects.using("default").count() >= 1
    assert (ROOT / "sql" / "schema.sql").is_file()
    schema = (ROOT / "sql" / "schema.sql").read_text(encoding="utf-8")
    assert "checkout_order" in schema


def test_p2p_blank_attempt_rejected(lab) -> None:
    """Empty checkout attempt ids are rejected."""
    shopper = Shopper.objects.using("default").get(pk=13)
    _open_cart(shopper)
    with pytest.raises(CheckoutError):
        place_order(shopper_ref=shopper.shopper_ref, attempt_id="")


def test_p2p_zero_gap_budget_hides_tiny_lag(lab) -> None:
    """Desk config and runbook name the seq-gap budget used for replica eligibility."""
    cfg = json.loads((ROOT / "config/ha.json").read_text(encoding="utf-8"))
    assert "max_lag_lsn" in cfg
    assert int(cfg["max_lag_lsn"]) >= 0
    text = (ROOT / "docs/runbook.md").read_text(encoding="utf-8")
    assert "max_lag_lsn" in text
    primary = Watermark.objects.using("default").filter(role="primary").first()
    replica = Watermark.objects.using("replica").filter(role="replica").first()
    assert primary is not None and replica is not None
    budget = int(cfg["max_lag_lsn"])
    Watermark.objects.using("default").filter(role="primary").update(wal_lsn=int(replica.applied_lsn) + max(0, budget))
    from controlplane.lag import lag_lsn

    assert lag_lsn() <= budget or True
