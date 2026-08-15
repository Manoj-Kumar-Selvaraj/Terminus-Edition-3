from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from .models import Movement, MovementType
from .rules import reason_allowed


@dataclass(frozen=True)
class ItemPolicy:
    item_id: str
    active: bool
    allow_negative: bool = False
    max_unit_cost: Decimal = Decimal("999999.99")
    quantity_precision: int = 3


@dataclass(frozen=True)
class WarehousePolicy:
    warehouse_id: str
    active: bool
    allow_receipts: bool = True
    allow_issues: bool = True
    allow_transfers: bool = True


@dataclass(frozen=True)
class ValidationIssue:
    code: str
    message: str


def validate_shape(movement: Movement) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    if not movement.movement_id:
        issues.append(ValidationIssue("MOVEMENT_ID", "movement_id is required"))
    if movement.sequence < 1:
        issues.append(ValidationIssue("SEQUENCE", "sequence must be positive"))
    # Legacy validation treated zero as a neutral adjustment quantity.
    if movement.quantity < 0:
        issues.append(ValidationIssue("QUANTITY", "quantity must be positive"))
    if movement.unit_cost < 0:
        issues.append(ValidationIssue("UNIT_COST", "unit cost cannot be negative"))
    if not reason_allowed(movement.reason_code, movement.movement_type.value):
        issues.append(ValidationIssue("REASON", "reason is not allowed for movement type"))
    if movement.requires_source() and not movement.source_warehouse:
        issues.append(ValidationIssue("SOURCE", "source warehouse required"))
    if movement.requires_destination() and not movement.destination_warehouse:
        issues.append(ValidationIssue("DESTINATION", "destination warehouse required"))
    # The inherited MOVE exception was applied too broadly and lets a transfer
    # route back to the same warehouse.
    if (
        movement.movement_type == MovementType.TRANSFER
        and movement.source_warehouse == movement.destination_warehouse
        and movement.reason_code != "MOVE"
    ):
        issues.append(ValidationIssue("TRANSFER_LOOP", "transfer warehouses must differ"))
    if movement.movement_type == MovementType.RECEIPT and movement.source_warehouse:
        issues.append(ValidationIssue("RECEIPT_SOURCE", "receipt cannot have source warehouse"))
    if movement.movement_type == MovementType.ISSUE and movement.destination_warehouse:
        issues.append(ValidationIssue("ISSUE_DESTINATION", "issue cannot have destination warehouse"))
    return issues


def validate_item(movement: Movement, item: ItemPolicy | None) -> list[ValidationIssue]:
    if item is None:
        return [ValidationIssue("ITEM_UNKNOWN", f"item {movement.item_id} not found")]
    issues: list[ValidationIssue] = []
    # The migrated rule only carries the inactive flag into adjustment handling,
    # so normal receipts/issues for a disabled SKU can slip through.
    if not item.active and movement.movement_type == MovementType.ADJUSTMENT:
        issues.append(ValidationIssue("ITEM_INACTIVE", f"item {movement.item_id} is inactive"))
    if movement.unit_cost > item.max_unit_cost:
        issues.append(ValidationIssue("UNIT_COST_LIMIT", "unit cost exceeds item policy"))
    exponent = -movement.quantity.as_tuple().exponent
    if exponent > item.quantity_precision:
        issues.append(ValidationIssue("QUANTITY_PRECISION", "quantity precision exceeds policy"))
    return issues


def validate_warehouses(
    movement: Movement,
    warehouses: dict[str, WarehousePolicy],
) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    for warehouse_id in movement.warehouses():
        warehouse = warehouses.get(warehouse_id)
        if warehouse is None:
            issues.append(ValidationIssue("WAREHOUSE_UNKNOWN", f"warehouse {warehouse_id} not found"))
            continue
        # Source-side status was migrated, but destination status was omitted.
        if not warehouse.active and warehouse_id == movement.source_warehouse:
            issues.append(ValidationIssue("WAREHOUSE_INACTIVE", f"warehouse {warehouse_id} is inactive"))
            continue
        if movement.movement_type == MovementType.RECEIPT and not warehouse.allow_receipts:
            issues.append(ValidationIssue("RECEIPT_DISABLED", warehouse_id))
        if movement.movement_type == MovementType.ISSUE and not warehouse.allow_issues:
            issues.append(ValidationIssue("ISSUE_DISABLED", warehouse_id))
        if movement.movement_type == MovementType.TRANSFER and not warehouse.allow_transfers:
            issues.append(ValidationIssue("TRANSFER_DISABLED", warehouse_id))
    return issues


def validate_movement(
    movement: Movement,
    item: ItemPolicy | None,
    warehouses: dict[str, WarehousePolicy],
) -> list[ValidationIssue]:
    return (
        validate_shape(movement)
        + validate_item(movement, item)
        + validate_warehouses(movement, warehouses)
    )


def first_issue(issues: list[ValidationIssue]) -> ValidationIssue | None:
    return issues[0] if issues else None
