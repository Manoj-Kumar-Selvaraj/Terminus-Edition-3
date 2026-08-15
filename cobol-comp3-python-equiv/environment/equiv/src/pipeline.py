from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sqlite3

from .accounting import effects_for
from .authorization import require as require_authorized, system_principal
from .catalog import Catalog
from .checkpoint import load_validated, persist, resume_sequence
from .cycle_close import authorize as authorize_close
from .database import (
    count_processed,
    count_rejects,
    effect_rows,
    insert_effect,
    insert_processed,
    insert_reject,
    reject_rows,
    set_run_state,
    transaction,
)
from .event_journal import append as append_event
from .framing import RecordDecodeError, read_records
from .generation import build_identity
from .inventory_service import InventoryService
from .layout import load_layout
from .models import Reject, RunState, RunSummary
from .policy import validate_movement
from .publication import atomic_publish
from .publication_registry import PublicationRegistry
from .reconciliation import parse_legacy_controls, reconcile
from .reconciliation_detail import require_none as require_no_reconciliation_findings
from .replay_guard import ReplayGuard
from .reporting import (
    report_paths,
    write_effects,
    write_reconciliation,
    write_rejects,
    write_summary,
)
from .settlement import calculate as calculate_settlement
from .transform import movement_from_record, normalized


@dataclass(frozen=True)
class PipelineConfig:
    source_path: Path
    layout_path: Path
    business_date: str
    legacy_controls: Path
    report_dir: Path
    publish_dir: Path
    stop_after: int | None = None


def _reject(
    generation_id: str,
    sequence: int,
    movement_id: str,
    code: str,
    message: str,
    offset: int,
    length: int,
) -> Reject:
    return Reject(
        generation_id,
        sequence,
        movement_id,
        code,
        message,
        offset,
        length,
    )


def _journal_reject(
    db: sqlite3.Connection,
    generation_id: str,
    sequence: int,
    code: str,
    movement_id: str,
) -> None:
    append_event(
        db,
        generation_id,
        sequence,
        "REJECT",
        movement_id or f"sequence:{sequence}",
        {"code": code},
    )


def process(db: sqlite3.Connection, config: PipelineConfig) -> RunSummary:
    layout = load_layout(config.layout_path)
    identity = build_identity(
        config.source_path,
        config.layout_path,
        config.business_date,
    )
    checkpoint = load_validated(db, identity)
    start = resume_sequence(identity, checkpoint)
    summary = RunSummary(identity.generation_id, RunState.PROCESSING)
    set_run_state(db, identity.generation_id, RunState.PROCESSING)
    db.commit()

    catalog = Catalog(db)
    warehouses = catalog.all_warehouse_policies()
    inventory = InventoryService(db)
    replay = ReplayGuard(db)
    seen_count = 0

    for decoded in read_records(layout, config.source_path):
        seen_count += 1
        if isinstance(decoded, RecordDecodeError):
            sequence = seen_count
            if sequence < start:
                continue
            rejected = _reject(
                identity.generation_id,
                sequence,
                "",
                "DECODE",
                str(decoded),
                decoded.offset,
                decoded.length,
            )
            with transaction(db):
                insert_reject(db, rejected)
                persist(db, identity, sequence, decoded.offset + decoded.length)
                _journal_reject(db, identity.generation_id, sequence, "DECODE", "")
            summary.record_reject()
            continue

        try:
            movement = normalized(
                movement_from_record(decoded, identity.generation_id)
            )
        except Exception as exc:
            sequence = seen_count
            if sequence < start:
                continue
            with transaction(db):
                insert_reject(
                    db,
                    _reject(
                        identity.generation_id,
                        sequence,
                        "",
                        "TRANSFORM",
                        str(exc),
                        decoded.offset,
                        decoded.length,
                    ),
                )
                persist(db, identity, sequence, decoded.offset + decoded.length)
                _journal_reject(db, identity.generation_id, sequence, "TRANSFORM", "")
            summary.record_reject()
            continue

        if movement.sequence < start:
            continue
        replay_decision = replay.decision(
            identity.generation_id,
            movement.movement_id,
        )
        # The inherited restart path only suppresses an exact replay when the
        # decoded sequence is already behind the resume cursor.  At the cursor
        # boundary the same durable movement is incorrectly treated as work.
        if replay_decision.duplicate and movement.sequence < start:
            continue

        issues = validate_movement(
            movement,
            catalog.item_policy(movement.item_id),
            warehouses,
        )
        if issues:
            first = issues[0]
            with transaction(db):
                insert_reject(
                    db,
                    _reject(
                        identity.generation_id,
                        movement.sequence,
                        movement.movement_id,
                        first.code,
                        first.message,
                        decoded.offset,
                        decoded.length,
                    ),
                )
                insert_processed(db, movement, "REJECTED")
                persist(
                    db,
                    identity,
                    movement.sequence,
                    decoded.offset + decoded.length,
                )
                _journal_reject(
                    db,
                    identity.generation_id,
                    movement.sequence,
                    first.code,
                    movement.movement_id,
                )
            summary.record_reject()
        else:
            positions = {
                (warehouse_id, movement.item_id): inventory.position(
                    warehouse_id, movement.item_id
                )
                for warehouse_id in movement.warehouses()
            }
            try:
                effects = effects_for(movement, positions)
            except ValueError as exc:
                with transaction(db):
                    insert_reject(
                        db,
                        _reject(
                            identity.generation_id,
                            movement.sequence,
                            movement.movement_id,
                            "ACCOUNTING",
                            str(exc),
                            decoded.offset,
                            decoded.length,
                        ),
                    )
                    insert_processed(db, movement, "REJECTED")
                    persist(
                        db,
                        identity,
                        movement.sequence,
                        decoded.offset + decoded.length,
                    )
                    _journal_reject(
                        db,
                        identity.generation_id,
                        movement.sequence,
                        "ACCOUNTING",
                        movement.movement_id,
                    )
                summary.record_reject()
                continue

            with transaction(db):
                insert_processed(db, movement, "ACCEPTED")
                for effect in effects:
                    insert_effect(db, effect, identity.generation_id)
                    inventory.apply(effect)
                persist(
                    db,
                    identity,
                    movement.sequence,
                    decoded.offset + decoded.length,
                )
                append_event(
                    db,
                    identity.generation_id,
                    movement.sequence,
                    "ACCEPT",
                    movement.movement_id,
                    {
                        "movement_type": movement.movement_type.value,
                        "effect_count": len(effects),
                    },
                )
            summary.record_accept(effects)

        if config.stop_after is not None and summary.processed >= config.stop_after:
            return summary

    set_run_state(db, identity.generation_id, RunState.RECONCILING)
    db.commit()
    legacy = parse_legacy_controls(config.legacy_controls)
    result = reconcile(db, identity.generation_id, legacy)
    summary.state = RunState.READY if result.passed else RunState.HELD
    set_run_state(db, identity.generation_id, summary.state)
    db.commit()

    paths = report_paths(config.report_dir / identity.generation_id)
    write_effects(effect_rows(db, identity.generation_id), paths["effects"])
    write_rejects(reject_rows(db, identity.generation_id), paths["rejects"])
    write_reconciliation(result, paths["reconciliation"])
    summary.processed = count_processed(db, identity.generation_id)
    summary.rejected = count_rejects(db, identity.generation_id)
    summary.accepted = summary.processed - summary.rejected
    summary.output_paths = {key: str(value) for key, value in paths.items()}
    write_summary(summary, paths["summary"])

    if result.passed:
        require_no_reconciliation_findings(db, identity.generation_id)
        settlement = calculate_settlement(db, identity.generation_id)
        require_authorized(system_principal(), "PUBLISH", RunState.READY)
        with transaction(db):
            authorize_close(db, settlement, "equiv-system")
            append_event(
                db,
                identity.generation_id,
                summary.processed,
                "CLOSE_AUTHORIZED",
                identity.generation_id,
                {"net_value": format(settlement.net_value, "f")},
            )
        published = atomic_publish(
            identity.generation_id,
            paths,
            result,
            config.publish_dir,
        )
        registry = PublicationRegistry(
            config.report_dir.parent / "publication-registry.jsonl"
        )
        registry.register(identity.generation_id, published)
        summary.state = RunState.PUBLISHED
        summary.output_paths["published"] = str(published)
        set_run_state(db, identity.generation_id, RunState.PUBLISHED)
        append_event(
            db,
            identity.generation_id,
            summary.processed,
            "PUBLISHED",
            str(published),
            {"registry_valid": registry.validate()},
        )
        db.commit()
        write_summary(summary, paths["summary"])
    return summary
