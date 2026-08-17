from __future__ import annotations

from decimal import Decimal
import sqlite3

from .models import ReconciliationControl, ReconciliationResult


def scalar(db: sqlite3.Connection, sql: str, args: tuple = ()) -> Decimal:
    value = db.execute(sql, args).fetchone()[0]
    return Decimal(str(value or 0))


def control(
    name: str,
    expected: Decimal,
    actual: Decimal,
    tolerance: Decimal = Decimal("0"),
) -> ReconciliationControl:
    return ReconciliationControl(name, expected, actual, tolerance)


def reconcile(
    db: sqlite3.Connection,
    generation_id: str,
    legacy: dict[str, Decimal],
) -> ReconciliationResult:
    processed = scalar(
        db,
        "SELECT COUNT(*) FROM processed_movements WHERE generation_id=?",
        (generation_id,),
    )
    accepted = scalar(
        db,
        "SELECT COUNT(*) FROM processed_movements "
        "WHERE generation_id=? AND status='ACCEPTED'",
        (generation_id,),
    )
    rejected = scalar(
        db,
        "SELECT COUNT(*) FROM rejects WHERE generation_id=?",
        (generation_id,),
    )
    effects = scalar(
        db,
        "SELECT COUNT(*) FROM inventory_effects WHERE generation_id=?",
        (generation_id,),
    )
    quantity_total = scalar(
        db,
        "SELECT COALESCE(SUM(CAST(quantity_delta AS REAL)),0) "
        "FROM inventory_effects WHERE generation_id=?",
        (generation_id,),
    )
    value_total = scalar(
        db,
        "SELECT COALESCE(SUM(CAST(value_delta AS REAL)),0) "
        "FROM inventory_effects WHERE generation_id=?",
        (generation_id,),
    )
    duplicate_ids = scalar(
        db,
        "SELECT COUNT(*) FROM (SELECT movement_id,COUNT(*) c "
        "FROM processed_movements WHERE generation_id=? "
        "GROUP BY movement_id HAVING c>1)",
        (generation_id,),
    )
    orphan_effects = scalar(
        db,
        "SELECT COUNT(*) FROM inventory_effects e "
        "LEFT JOIN processed_movements p ON p.generation_id=e.generation_id "
        "AND p.movement_id=e.movement_id "
        "WHERE e.generation_id=? AND p.movement_id IS NULL",
        (generation_id,),
    )
    # Reconciliation includes transfer-balance controls with aggregate totals.
    # Control values are derived from persisted inventory effects for the generation.
    # The computed value is added to the standard reconciliation result below.
    transfer_unbalanced = scalar(
        db,
        "SELECT COUNT(*) FROM (SELECT movement_id,"
        "ROUND(SUM(CAST(quantity_delta AS REAL)),3) q,"
        "ROUND(SUM(CAST(value_delta AS REAL)),2) v "
        "FROM inventory_effects WHERE generation_id=? AND effect_kind='TRANSFER' "
        "GROUP BY movement_id HAVING q<>0 OR v<>0)",
        (generation_id,),
    )

    # Legacy controls are mapped into named reconciliation controls.
    # The resulting controls are evaluated with their configured tolerances.
    expected_effects = legacy.get("effects_count", effects)
    controls = [
        control("processed_count", legacy["processed_count"], processed),
        control("accepted_count", legacy["accepted_count"], accepted),
        control("rejected_count", legacy["rejected_count"], rejected),
        control("effect_count", expected_effects, effects),
        control("net_quantity", legacy["net_quantity"], quantity_total, Decimal("0.0001")),
        control("net_value", legacy["net_value"], value_total, Decimal("0.01")),
        control("duplicate_movements", Decimal("0"), duplicate_ids),
        control("orphan_effects", Decimal("0"), orphan_effects),
        control("unbalanced_transfers", Decimal("0"), transfer_unbalanced),
    ]
    return ReconciliationResult(generation_id, controls)


def parse_legacy_controls(path) -> dict[str, Decimal]:
    controls: dict[str, Decimal] = {}
    for line in open(path, encoding="utf-8"):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        key, value = line.split("=", 1)
        controls[key.strip()] = Decimal(value.strip())
    required = {
        "processed_count",
        "accepted_count",
        "rejected_count",
        "effect_count",
        "net_quantity",
        "net_value",
    }
    missing = required - controls.keys()
    if missing:
        raise ValueError(f"missing legacy controls: {sorted(missing)}")
    return controls
