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


def test_f2p_pay_marks_writer_and_confirmation(lab) -> None:
    """Writer pay must mark PAID on default and confirmation must show that paid order."""
    shopper = Shopper.objects.using("default").get(pk=13)
    _open_cart(shopper)
    attempt = f"att-pay-{uuid.uuid4().hex[:8]}"
    placed = _place(shopper.shopper_ref, attempt, _writer())
    assert placed["status"] == 200
    order_ref = placed["body"]["order_ref"]
    with override_settings(AZ_ID=_writer()):
        client = Client()
        paid = client.post(f"/api/orders/{order_ref}/pay", content_type="application/json")
    assert paid.status_code == 200
    assert Order.objects.using("default").filter(order_ref=order_ref, status="PAID").exists()
    replica_only = (
        Order.objects.using("replica").filter(order_ref=order_ref, status="PAID").exists()
        and not Order.objects.using("default").filter(order_ref=order_ref, status="PAID").exists()
    )
    assert not replica_only
    seen = _confirmation(shopper.shopper_ref)
    assert seen["body"]["order_ref"] == order_ref
    assert seen["body"]["status"] == "PAID"
    assert seen["body"]["alias"] == "default"


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
    """Idle confirmation stays on the writer while lagged; after sync standby is readable."""
    shopper = Shopper.objects.using("default").get(pk=50)
    assert _confirmation(shopper.shopper_ref)["body"]["alias"] == "default"
    before = _dump(lab)
    assert before["standby_readable"] is False
    call_command("sync_standby")
    after = _dump(lab)
    assert after["standby_readable"] is True
    assert int(after["seq_gap"]) <= 25
    body = _confirmation(shopper.shopper_ref)["body"]
    assert body["alias"] in {"replica", "default"}


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


def test_f2p_sync_standby_advances_without_writable_lease(lab) -> None:
    """sync_standby advances seq, copies late incident orders, and leaves standby non-writable."""
    before = int(_dump(lab)["standby_seq"])
    FenceLease.objects.using("default").filter(resource="checkout-primary").update(
        owner_node="az-b", writable=1, epoch=4
    )
    call_command("sync_standby")
    after = _dump(lab)
    assert int(after["standby_seq"]) >= before
    assert after["standby_readable"] is True
    replica = FenceLease.objects.using("replica").filter(resource="checkout-primary").first()
    assert replica is None or int(replica.writable) == 0
    assert Order.objects.using("replica").filter(id__gte=19980).count() >= 1
    assert Order.objects.using("replica").filter(attempt_id="att-inc-20001").exists()


def test_f2p_pins_on_shared_alias_not_session(lab) -> None:
    """Sticky keys publish on pins and must not land in django_session."""
    shopper = Shopper.objects.using("default").get(pk=8)
    _open_cart(shopper)
    assert _place(shopper.shopper_ref, f"att-share-{uuid.uuid4().hex[:8]}", _writer())["status"] == 200
    key = f"sticky:shopper:{shopper.id}"
    assert caches["pins"].get(key)
    assert not ShopSession.objects.using("default").filter(session_key=key).exists()
    assert not ShopSession.objects.using("replica").filter(session_key=key).exists()


def test_f2p_pins_survive_cache_session_and_db_remap(lab) -> None:
    """Sticky confirmation survives default-cache clear, session wipe, and default DB remap."""
    shopper = Shopper.objects.using("default").get(pk=7)
    _open_cart(shopper)
    call_command("sync_standby")
    assert _place(shopper.shopper_ref, f"att-pin-{uuid.uuid4().hex[:8]}", _writer())["status"] == 200
    caches["default"].clear()
    assert _confirmation(shopper.shopper_ref)["body"]["alias"] == "default"
    ShopSession.objects.using("default").all().delete()
    ShopSession.objects.using("replica").all().delete()
    caches["default"].clear()
    assert _confirmation(shopper.shopper_ref)["body"]["alias"] == "default"
    connections.close_all()
    dj_settings.DATABASES["default"]["NAME"] = str(lab["standby"])
    assert caches["pins"].get(f"sticky:shopper:{shopper.id}")


def test_f2p_cutover_single_writer_epoch(lab) -> None:
    """cutover bumps epoch, exposes one az-b writer, and drops az-a from writers_seen."""
    before = int(FenceLease.objects.using("default").get(resource="checkout-primary").epoch)
    call_command("cutover", node="az-b")
    FenceLease.objects.using("replica").filter(resource="checkout-primary").update(writable=0)
    after = int(FenceLease.objects.using("default").get(resource="checkout-primary").epoch)
    assert after > before
    status = _dump(lab)
    assert status["writer"] == "az-b"
    assert "az-a" not in status["writers_seen"]
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


def test_f2p_capture_idempotent_across_retries(lab) -> None:
    """Same attempt retry on writer or second AZ still yields one capture row."""
    shopper = Shopper.objects.using("default").get(pk=10)
    _open_cart(shopper)
    attempt = f"att-idem-{uuid.uuid4().hex[:8]}"
    az = _writer()
    assert _place(shopper.shopper_ref, attempt, az)["status"] == 200
    _place(shopper.shopper_ref, attempt, az)
    assert SideEffect.objects.using("default").filter(attempt_id=attempt, kind="capture").count() == 1
    shopper2 = Shopper.objects.using("default").get(pk=16)
    _open_cart(shopper2)
    attempt2 = f"att-dual-{uuid.uuid4().hex[:8]}"
    assert _place(shopper2.shopper_ref, attempt2, _writer())["status"] == 200
    _place(shopper2.shopper_ref, attempt2, "az-b")
    assert SideEffect.objects.using("default").filter(attempt_id=attempt2, kind="capture").count() == 1


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
    before = SideEffect.objects.using("default").filter(
        attempt_id=order.attempt_id, kind="capture"
    ).count()
    Watermark.objects.using("default").filter(role="primary").update(wal_lsn=int(order.write_lsn) - 10)
    with override_settings(AZ_ID=_writer()):
        client = Client()
        response = client.post(f"/api/orders/{order.order_ref}/pay", content_type="application/json")
    assert response.status_code >= 400
    assert (
        SideEffect.objects.using("default")
        .filter(attempt_id=order.attempt_id, kind="capture")
        .count()
        == before
    )


def test_f2p_readyz_503_on_split_or_lag(lab) -> None:
    """/readyz returns 503 for double-writable writers or an out-of-budget seq gap."""
    FenceLease.objects.using("default").filter(resource="checkout-primary").update(writable=1, owner_node="az-a")
    FenceLease.objects.using("replica").filter(resource="checkout-primary").update(writable=1, owner_node="az-b")
    assert Client().get("/readyz").status_code == 503
    FenceLease.objects.using("replica").filter(resource="checkout-primary").update(writable=0)
    Watermark.objects.using("default").filter(role="primary").update(wal_lsn=10_000)
    Watermark.objects.using("replica").filter(role="replica").update(applied_lsn=0)
    assert Client().get("/readyz").status_code == 503


def test_f2p_readyz_503_on_pins_or_repeat_captures(lab) -> None:
    """/readyz returns 503 when pins are unreachable or duplicate captures remain."""
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
    pin_dir = Path(dj_settings.BASE_DIR) / "state" / "pin-cache"
    try:
        if pin_dir.exists():
            if pin_dir.is_dir():
                shutil.rmtree(pin_dir)
            else:
                pin_dir.unlink()
        pin_dir.parent.mkdir(parents=True, exist_ok=True)
        pin_dir.write_text("blocked", encoding="utf-8")
        assert Client().get("/readyz").status_code == 503
    finally:
        if pin_dir.exists() and pin_dir.is_file():
            pin_dir.unlink()
        pin_dir.mkdir(parents=True, exist_ok=True)
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
    assert Client().get("/readyz").status_code == 503


def test_f2p_healthz_200_while_readyz_fails(lab) -> None:
    """/healthz stays 200 while /readyz returns 503 under a forced unsafe writer split."""
    FenceLease.objects.using("default").filter(resource="checkout-primary").update(
        writable=1, owner_node="az-a"
    )
    FenceLease.objects.using("replica").filter(resource="checkout-primary").update(
        writable=1, owner_node="az-b"
    )
    live = Client().get("/healthz")
    ready = Client().get("/readyz")
    assert live.status_code == 200
    assert ready.status_code == 503
    assert json.loads(ready.content)["accepting_checkout"] is False


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


def test_f2p_failover_status_blocks_standby_or_fence(lab) -> None:
    """Dump accepting_checkout is false for standby-only orders or a writable standby lease."""
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
    FenceLease.objects.using("default").filter(resource="checkout-primary").update(
        writable=1, owner_node="az-b"
    )
    FenceLease.objects.using("replica").filter(resource="checkout-primary").update(
        writable=1, owner_node="az-b"
    )
    payload = _dump(lab)
    assert payload["fence_copied_to_standby"] is True or payload["double_primary"] is True
    assert payload["accepting_checkout"] is False


def test_f2p_failover_status_blocks_gap_or_missing_incident(lab) -> None:
    """Dump accepting_checkout is false for oversize seq gap or missing incident-window orders."""
    FenceLease.objects.using("replica").filter(resource="checkout-primary").update(writable=0)
    Watermark.objects.using("default").filter(role="primary").update(wal_lsn=50_000)
    Watermark.objects.using("replica").filter(role="replica").update(applied_lsn=0)
    payload = _dump(lab)
    assert int(payload["seq_gap"]) > 25 or payload["accepting_checkout"] is False
    assert payload["accepting_checkout"] is False
    Watermark.objects.using("default").filter(role="primary").update(wal_lsn=10)
    Watermark.objects.using("replica").filter(role="replica").update(applied_lsn=10)
    Order.objects.using("replica").filter(id__gte=19980).delete()
    payload = _dump(lab)
    assert payload["incident_orders_on_standby"] is False
    assert payload["accepting_checkout"] is False


def test_f2p_failover_status_accepts_when_healed(lab) -> None:
    """Dump accepting_checkout is true only when the full healed conjunction holds."""
    from django.db.models import Count, Min

    from fulfill.models import WebhookDelivery

    pin_dir = Path(dj_settings.BASE_DIR) / "state" / "pin-cache"
    if pin_dir.exists() and pin_dir.is_file():
        pin_dir.unlink()
    pin_dir.mkdir(parents=True, exist_ok=True)
    WebhookDelivery.objects.using("default").all().delete()
    dupes = (
        SideEffect.objects.using("default")
        .values("attempt_id", "kind")
        .annotate(n=Count("id"), keep=Min("id"))
        .filter(n__gt=1)
    )
    for row in dupes:
        SideEffect.objects.using("default").filter(
            attempt_id=row["attempt_id"], kind=row["kind"]
        ).exclude(pk=row["keep"]).delete()
    call_command("sync_standby")
    FenceLease.objects.using("default").filter(resource="checkout-primary").update(
        owner_node="az-b", writable=1, epoch=4
    )
    FenceLease.objects.using("replica").filter(resource="checkout-primary").update(
        owner_node="az-b", writable=0, epoch=4
    )
    primary_refs = set(Order.objects.using("default").values_list("order_ref", flat=True))
    Order.objects.using("replica").exclude(order_ref__in=primary_refs).delete()
    payload = _dump(lab)
    assert payload["pins"] == "shared"
    assert payload["double_primary"] is False
    assert int(payload["repeat_captures"]) == 0
    assert int(payload["standby_only_orders"]) == 0
    assert payload["incident_orders_on_standby"] is True
    assert payload["fence_copied_to_standby"] is False
    assert int(payload["seq_gap"]) <= 25
    assert payload["accepting_checkout"] is True
    ready = Client().get("/readyz")
    assert ready.status_code == 200
    assert json.loads(ready.content)["accepting_checkout"] is True


def test_f2p_readyz_200_when_live_gates_hold(lab) -> None:
    """Live /readyz must return 200 with accepting_checkout true when traffic gates hold."""
    from django.db.models import Count, Min

    from fulfill.models import WebhookDelivery

    pin_dir = Path(dj_settings.BASE_DIR) / "state" / "pin-cache"
    if pin_dir.exists() and pin_dir.is_file():
        pin_dir.unlink()
    pin_dir.mkdir(parents=True, exist_ok=True)
    WebhookDelivery.objects.using("default").all().delete()
    dupes = (
        SideEffect.objects.using("default")
        .values("attempt_id", "kind")
        .annotate(n=Count("id"), keep=Min("id"))
        .filter(n__gt=1)
    )
    for row in dupes:
        SideEffect.objects.using("default").filter(
            attempt_id=row["attempt_id"], kind=row["kind"]
        ).exclude(pk=row["keep"]).delete()
    call_command("sync_standby")
    FenceLease.objects.using("default").filter(resource="checkout-primary").update(
        owner_node="az-b", writable=1, epoch=4
    )
    FenceLease.objects.using("replica").filter(resource="checkout-primary").update(
        owner_node="az-b", writable=0, epoch=4
    )
    ready = Client().get("/readyz")
    assert ready.status_code == 200
    body = json.loads(ready.content)
    assert body["accepting_checkout"] is True


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
