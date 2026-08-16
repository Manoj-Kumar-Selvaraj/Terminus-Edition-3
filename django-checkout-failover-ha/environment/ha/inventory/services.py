from __future__ import annotations

from datetime import datetime, timezone

from django.db import transaction
from django.db.models import F

from inventory.models import Reservation, StockLot
from inventory.reservation_ledger import ReservationLedger, ReservationLine, ReservationState


class InventoryError(Exception):
    pass


def reserve_for_attempt(warehouse_id: int, product_id: int, qty: int, attempt_id: str) -> Reservation:
    if qty <= 0:
        raise InventoryError("qty must be positive")
    ledger = ReservationLedger()
    ledger.hold(
        ReservationLine(
            warehouse_id=int(warehouse_id),
            product_id=int(product_id),
            qty=int(qty),
            attempt_id=attempt_id,
            state=ReservationState.HELD,
        )
    )
    with transaction.atomic(using="default"):
        lot = (
            StockLot.objects.select_for_update()
            .filter(warehouse_id=warehouse_id, product_id=product_id)
            .order_by("id")
            .first()
        )
        if lot is None:
            raise InventoryError("no stock lot")
        available = int(lot.qty_on_hand) - int(lot.qty_reserved)
        if available < qty:
            raise InventoryError("insufficient stock")
        existing = Reservation.objects.filter(attempt_id=attempt_id, stocklot=lot, status="HELD").first()
        if existing:
            return existing
        StockLot.objects.filter(pk=lot.pk).update(qty_reserved=F("qty_reserved") + qty)
        return Reservation.objects.create(
            stocklot=lot,
            attempt_id=attempt_id,
            qty=qty,
            status="HELD",
            created_at=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        )


def commit_reservation(attempt_id: str) -> None:
    held = list(Reservation.objects.filter(attempt_id=attempt_id, status="HELD"))
    for row in held:
        StockLot.objects.filter(pk=row.stocklot_id).update(
            qty_on_hand=F("qty_on_hand") - row.qty,
            qty_reserved=F("qty_reserved") - row.qty,
        )
        row.status = "COMMITTED"
        row.save(update_fields=["status"])


def already_committed(attempt_id: str) -> bool:
    return Reservation.objects.filter(attempt_id=attempt_id, status="COMMITTED").exists()
