from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
import sqlite3

from .models import MovementType


@dataclass(frozen=True)
class StockSnapshot:
    warehouse_id: str
    item_id: str
    quantity: Decimal
    value: Decimal
    accepted_movements: int
    rejected_movements: int


@dataclass(frozen=True)
class MovementAudit:
    movement_id: str
    generation_id: str
    status: str
    effect_count: int
    quantity_delta: Decimal
    value_delta: Decimal


def stock_snapshot(db: sqlite3.Connection, warehouse_id: str, item_id: str) -> StockSnapshot:
    pos = db.execute(
        "SELECT quantity,value FROM inventory_positions WHERE warehouse_id=? AND item_id=?",
        (warehouse_id, item_id),
    ).fetchone()
    quantity = Decimal(pos[0]) if pos else Decimal("0")
    value = Decimal(pos[1]) if pos else Decimal("0")
    accepted = db.execute(
        "SELECT COUNT(*) FROM processed_movements p "
        "JOIN inventory_effects e ON e.generation_id=p.generation_id "
        "AND e.movement_id=p.movement_id "
        "WHERE p.status='ACCEPTED' AND e.warehouse_id=? AND e.item_id=?",
        (warehouse_id, item_id),
    ).fetchone()[0]
    rejected = db.execute(
        "SELECT COUNT(*) FROM processed_movements WHERE status='REJECTED' AND item_id=?",
        (item_id,),
    ).fetchone()[0]
    return StockSnapshot(
        warehouse_id,
        item_id,
        quantity,
        value,
        int(accepted),
        int(rejected),
    )


def movement_audit(
    db: sqlite3.Connection, generation_id: str, movement_id: str
) -> MovementAudit | None:
    processed = db.execute(
        "SELECT status FROM processed_movements WHERE generation_id=? AND movement_id=?",
        (generation_id, movement_id),
    ).fetchone()
    if processed is None:
        return None
    row = db.execute(
        "SELECT COUNT(*),COALESCE(SUM(CAST(quantity_delta AS REAL)),0),"
        "COALESCE(SUM(CAST(value_delta AS REAL)),0) "
        "FROM inventory_effects WHERE generation_id=? AND movement_id=?",
        (generation_id, movement_id),
    ).fetchone()
    return MovementAudit(
        movement_id,
        generation_id,
        processed[0],
        int(row[0]),
        Decimal(str(row[1])),
        Decimal(str(row[2])),
    )


def warehouse_totals(db: sqlite3.Connection) -> dict[str, tuple[Decimal, Decimal]]:
    result: dict[str, tuple[Decimal, Decimal]] = {}
    for row in db.execute(
        "SELECT warehouse_id,SUM(CAST(quantity AS REAL)),SUM(CAST(value AS REAL)) "
        "FROM inventory_positions GROUP BY warehouse_id"
    ):
        result[row[0]] = (Decimal(str(row[1] or 0)), Decimal(str(row[2] or 0)))
    return result


def item_totals(db: sqlite3.Connection) -> dict[str, tuple[Decimal, Decimal]]:
    result: dict[str, tuple[Decimal, Decimal]] = {}
    for row in db.execute(
        "SELECT item_id,SUM(CAST(quantity AS REAL)),SUM(CAST(value AS REAL)) "
        "FROM inventory_positions GROUP BY item_id"
    ):
        result[row[0]] = (Decimal(str(row[1] or 0)), Decimal(str(row[2] or 0)))
    return result


def generation_status_counts(db: sqlite3.Connection, generation_id: str) -> dict[str, int]:
    return {
        row[0]: int(row[1])
        for row in db.execute(
            "SELECT status,COUNT(*) FROM processed_movements "
            "WHERE generation_id=? GROUP BY status",
            (generation_id,),
        )
    }


def generation_type_counts(db: sqlite3.Connection, generation_id: str) -> dict[str, int]:
    return {
        row[0]: int(row[1])
        for row in db.execute(
            "SELECT movement_type,COUNT(*) FROM processed_movements "
            "WHERE generation_id=? GROUP BY movement_type",
            (generation_id,),
        )
    }


def valuation_drift(db: sqlite3.Connection, warehouse_id: str, item_id: str) -> Decimal:
    pos = db.execute(
        "SELECT quantity,value FROM inventory_positions WHERE warehouse_id=? AND item_id=?",
        (warehouse_id, item_id),
    ).fetchone()
    if not pos:
        return Decimal("0")
    effect_total = db.execute(
        "SELECT COALESCE(SUM(CAST(value_delta AS REAL)),0) FROM inventory_effects "
        "WHERE warehouse_id=? AND item_id=?",
        (warehouse_id, item_id),
    ).fetchone()[0]
    return Decimal(pos[1]) - Decimal(str(effect_total or 0))


def accepted_without_effects(db: sqlite3.Connection, generation_id: str) -> list[str]:
    return [
        row[0]
        for row in db.execute(
            "SELECT p.movement_id FROM processed_movements p "
            "LEFT JOIN inventory_effects e ON e.generation_id=p.generation_id "
            "AND e.movement_id=p.movement_id "
            "WHERE p.generation_id=? AND p.status='ACCEPTED' "
            "GROUP BY p.movement_id HAVING COUNT(e.id)=0",
            (generation_id,),
        )
    ]


def duplicate_effect_kinds(
    db: sqlite3.Connection, generation_id: str
) -> list[tuple[str, str]]:
    return [
        (row[0], row[1])
        for row in db.execute(
            "SELECT movement_id,effect_kind FROM inventory_effects "
            "WHERE generation_id=? GROUP BY movement_id,effect_kind HAVING COUNT(*)>1",
            (generation_id,),
        )
    ]


def transfer_shape_errors(db: sqlite3.Connection, generation_id: str) -> list[str]:
    return [
        row[0]
        for row in db.execute(
            "SELECT p.movement_id FROM processed_movements p "
            "LEFT JOIN inventory_effects e ON e.generation_id=p.generation_id "
            "AND e.movement_id=p.movement_id "
            "WHERE p.generation_id=? AND p.movement_type=? AND p.status='ACCEPTED' "
            "GROUP BY p.movement_id HAVING COUNT(e.id)<>2",
            (generation_id, MovementType.TRANSFER.value),
        )
    ]


def sequence_gaps(db: sqlite3.Connection, generation_id: str) -> list[int]:
    sequences = [
        int(row[0])
        for row in db.execute(
            "SELECT sequence FROM processed_movements WHERE generation_id=? ORDER BY sequence",
            (generation_id,),
        )
    ]
    if not sequences:
        return []
    expected = set(range(min(sequences), max(sequences) + 1))
    return sorted(expected - set(sequences))


def checkpoint_ahead_of_data(db: sqlite3.Connection, generation_id: str) -> bool:
    checkpoint = db.execute(
        "SELECT last_sequence FROM checkpoints WHERE generation_id=?",
        (generation_id,),
    ).fetchone()
    if not checkpoint:
        return False
    maximum = db.execute(
        "SELECT COALESCE(MAX(sequence),0) FROM processed_movements WHERE generation_id=?",
        (generation_id,),
    ).fetchone()[0]
    return int(checkpoint[0]) > int(maximum)


def publication_eligible(db: sqlite3.Connection, generation_id: str) -> bool:
    state = db.execute(
        "SELECT state FROM runs WHERE generation_id=?",
        (generation_id,),
    ).fetchone()
    if not state or state[0] not in {"READY", "PUBLISHED"}:
        return False
    if accepted_without_effects(db, generation_id):
        return False
    if transfer_shape_errors(db, generation_id):
        return False
    if duplicate_effect_kinds(db, generation_id):
        return False
    if checkpoint_ahead_of_data(db, generation_id):
        return False
    return True
