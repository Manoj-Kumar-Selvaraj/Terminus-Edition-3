from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
import sqlite3

from .archive import archive_generation as build_archive, verify as verify_archive
from .authorization import decide as authorize, system_principal
from .batch_window import default_window, seconds_remaining
from .catalog import Catalog
from .config import CutoverConfig, validate_all
from .control_export import write_csv as write_control_csv, write_json as write_control_json
from .control_history import baseline, status_ratios, validate_scale
from .controls import collect as collect_controls, critical_clean, summarize as summarize_controls
from .cutover import evaluate as evaluate_cutover
from .delta_export import (
    item_totals as delta_item_totals,
    totals as delta_totals,
    warehouse_totals as delta_warehouse_totals,
    write_csv as write_delta_csv,
    write_json as write_delta_json,
)
from .diagnostics import run as run_diagnostics
from .event_journal import append as append_event, counts as journal_counts, verify as verify_journal
from .generation import build_identity, input_manifest
from .integrity import create as create_integrity, validate as validate_integrity, write as write_integrity
from .inventory_service import InventoryService
from .layout import load_layout
from .lineage import LineageGraph, derived_node, source_node, verify_files, write as write_lineage
from .maintenance import maintenance_summary
from .migration import default_plan, validate_cutover_artifacts
from .publication import verify_publication
from .publication_registry import PublicationRegistry
from .quarantine import QuarantineStore
from .reconciliation_detail import findings as reconciliation_findings
from .recovery import assert_no_checkpoint_gap, database_plan, incomplete_sequences
from .replay_guard import ReplayGuard
from .report_contract import validate as validate_report_contract
from .retention import RetentionPolicy, retention_summary
from .runbook import preflight as runbook_preflight, summary as summarize_runbook
from .safety import describe as safety_description
from .schema_guard import validate as validate_schema
from .services import (
    accepted_without_effects,
    checkpoint_ahead_of_data,
    duplicate_effect_kinds,
    generation_status_counts,
    generation_type_counts,
    item_totals,
    sequence_gaps,
    transfer_shape_errors,
    warehouse_totals,
)
from .settlement import calculate as calculate_settlement
from .source_manifest import from_identity as source_manifest
from .source_profile import profile as profile_source
from .source_scan import scan_file


def _decimal_map(values: dict[str, tuple[Decimal, Decimal]]) -> dict[str, dict[str, str]]:
    return {
        key: {"quantity": format(quantity, "f"), "value": format(value, "f")}
        for key, (quantity, value) in values.items()
    }


def preflight(db: sqlite3.Connection, config: CutoverConfig) -> dict[str, object]:
    """Evaluate whether the inherited cutover inputs and state are safe to process."""
    config_error: str | None = None
    try:
        validate_all(config)
    except (ValueError, OSError) as exc:
        config_error = str(exc)

    layout = load_layout(config.paths.layout)
    scan = scan_file(layout, config.paths.source)
    source = profile_source(layout, config.paths.source)
    identity = build_identity(config.paths.source, config.paths.layout, config.business_date)
    manifest = source_manifest(identity, source.records, config.producer, config.batch_id)
    runbook = runbook_preflight(
        db,
        config.paths.source,
        config.paths.layout,
        config.paths.legacy_controls,
    )
    schema_issues = validate_schema(db)
    history = baseline(db)
    history_issues = validate_scale(history)
    database = maintenance_summary(db)
    catalog = Catalog(db).snapshot()
    integrity = create_integrity(
        identity.generation_id,
        {
            "source": config.paths.source,
            "layout": config.paths.layout,
            "legacy_controls": config.paths.legacy_controls,
            "schema": config.paths.schema,
            "seed": config.paths.seed,
        },
    )
    integrity_issues = validate_integrity(integrity)
    window = default_window(config.business_date)
    now = datetime.now(timezone.utc)
    run_authorization = authorize(system_principal(), "RUN")
    migration = default_plan(identity.generation_id)
    recovery = database_plan(db, identity)

    passed = all(
        [
            config_error is None,
            scan.fully_framed,
            scan.decode_errors == 0,
            source.fully_framed,
            source.decode_errors == 0,
            not schema_issues,
            not history_issues,
            bool(database["healthy"]),
            not integrity_issues,
            bool(run_authorization.allowed),
            bool(summarize_runbook(runbook)["passed"]),
        ]
    )
    return {
        "passed": passed,
        "generation": input_manifest(identity),
        "config_error": config_error,
        "source_profile": asdict(source),
        "source_scan": {
            "records": len(scan.records),
            "complete_records": scan.complete_records,
            "decode_errors": scan.decode_errors,
            "trailing_bytes": scan.trailing_bytes,
            "fully_framed": scan.fully_framed,
        },
        "source_manifest": asdict(manifest) | {"fingerprint": manifest.fingerprint()},
        "schema_issues": [asdict(issue) for issue in schema_issues],
        "historical_baseline": asdict(history),
        "historical_status_ratios": {
            name: format(value, "f") for name, value in status_ratios(history).items()
        },
        "historical_scale_issues": history_issues,
        "database": database,
        "catalog": catalog,
        "integrity_issues": integrity_issues,
        "runbook": summarize_runbook(runbook),
        "authorization": asdict(run_authorization),
        "safety": safety_description(db, identity.generation_id),
        "recovery": asdict(recovery),
        "batch_window": {
            "phase": window.phase(now),
            "hard_close": window.hard_close().isoformat(),
            "seconds_remaining": seconds_remaining(window, now),
        },
        "migration_pending": [step.name for step in migration.pending()],
    }


def audit(
    db: sqlite3.Connection,
    source_path: Path,
    layout_path: Path,
    business_date: str,
    expected_records: int,
    quarantine_path: Path,
    registry_path: Path,
) -> dict[str, object]:
    """Inspect durable processing, recovery, replay and reconciliation state."""
    identity = build_identity(source_path, layout_path, business_date)
    generation_id = identity.generation_id
    replay = ReplayGuard(db).replay_health(generation_id)
    recovery = database_plan(db, identity)
    checkpoint_error: str | None = None
    try:
        assert_no_checkpoint_gap(db, generation_id)
    except ValueError as exc:
        checkpoint_error = str(exc)

    controls = collect_controls(db, generation_id)
    detail = reconciliation_findings(db, generation_id)
    inventory = InventoryService(db)
    metrics = __import__("src.metrics", fromlist=["snapshot"]).snapshot(
        db, generation_id, expected_records
    )
    readiness = evaluate_cutover(db, identity, expected_records)
    diagnostics = run_diagnostics(db, generation_id)
    quarantine = QuarantineStore(quarantine_path).summary(generation_id)
    registry = PublicationRegistry(registry_path)
    registry_entry = registry.get(generation_id)
    settlement = calculate_settlement(db, generation_id)

    missing_effects = accepted_without_effects(db, generation_id)
    duplicate_effects = duplicate_effect_kinds(db, generation_id)
    transfer_errors = transfer_shape_errors(db, generation_id)
    seq_gaps = sequence_gaps(db, generation_id)
    checkpoint_ahead = checkpoint_ahead_of_data(db, generation_id)
    invalid_positions = inventory.negative_positions()
    zero_quantity_values = inventory.zero_quantity_nonzero_value()
    journal_ok = verify_journal(db, generation_id)

    passed = all(
        [
            bool(replay["healthy"]),
            checkpoint_error is None,
            not incomplete_sequences(db, generation_id),
            critical_clean(controls),
            not detail,
            not missing_effects,
            not duplicate_effects,
            not transfer_errors,
            not seq_gaps,
            not checkpoint_ahead,
            not invalid_positions,
            not zero_quantity_values,
            bool(quarantine["hashes_valid"]),
            registry.validate(),
            journal_ok,
        ]
    )
    return {
        "passed": passed,
        "generation": input_manifest(identity),
        "recovery": asdict(recovery),
        "checkpoint_error": checkpoint_error,
        "incomplete_sequences": incomplete_sequences(db, generation_id),
        "replay": replay,
        "controls": summarize_controls(controls),
        "critical_controls_clean": critical_clean(controls),
        "reconciliation_findings": [asdict(row) for row in detail],
        "diagnostics": [asdict(row) for row in diagnostics],
        "metrics": asdict(metrics),
        "cutover": readiness.as_dict(),
        "quarantine": quarantine,
        "registry_valid": registry.validate(),
        "registry_entry": asdict(registry_entry) if registry_entry else None,
        "journal_valid": journal_ok,
        "journal_counts": journal_counts(db, generation_id),
        "settlement": asdict(settlement),
        "accepted_without_effects": missing_effects,
        "duplicate_effect_kinds": duplicate_effects,
        "transfer_shape_errors": transfer_errors,
        "sequence_gaps": seq_gaps,
        "checkpoint_ahead_of_data": checkpoint_ahead,
        "invalid_positions": invalid_positions,
        "zero_quantity_nonzero_value": [
            (warehouse, item, format(value, "f"))
            for warehouse, item, value in zero_quantity_values
        ],
        "warehouse_totals": _decimal_map(warehouse_totals(db)),
        "item_totals": _decimal_map(item_totals(db)),
        "status_counts": generation_status_counts(db, generation_id),
        "type_counts": generation_type_counts(db, generation_id),
    }


def archive(
    db: sqlite3.Connection,
    source_path: Path,
    layout_path: Path,
    business_date: str,
    report_dir: Path,
    publish_dir: Path,
    archive_dir: Path,
    registry_path: Path,
) -> dict[str, object]:
    """Verify and archive one completed generation with control and lineage evidence."""
    identity = build_identity(source_path, layout_path, business_date)
    generation_id = identity.generation_id
    report_root = report_dir / generation_id
    published_root = publish_dir / generation_id
    if not verify_publication(published_root):
        raise ValueError("publication integrity invalid")

    contract_issues = validate_report_contract(report_root)
    migration_issues = validate_cutover_artifacts(report_root, published_root)
    controls = collect_controls(db, generation_id)
    settlement = calculate_settlement(db, generation_id)
    export_root = archive_dir / ".work" / generation_id
    export_root.mkdir(parents=True, exist_ok=True)
    control_csv = export_root / "controls.csv"
    control_json = export_root / "controls.json"
    delta_csv = export_root / "deltas.csv"
    delta_json = export_root / "deltas.json"
    write_control_csv(controls, control_csv)
    write_control_json(controls, control_json)
    write_delta_csv(db, generation_id, delta_csv)
    write_delta_json(db, generation_id, delta_json)

    registry = PublicationRegistry(registry_path)
    registry_entry = registry.register(generation_id, published_root)
    source_node_row = source_node("source", "movement-feed", source_path)
    layout_node_row = source_node("layout", "layout-contract", layout_path)
    controls_node_row = derived_node(
        "controls", "control-export", control_csv, ["source", "layout"]
    )
    deltas_node_row = derived_node(
        "deltas", "inventory-deltas", delta_csv, ["source", "layout"]
    )
    publication_node_row = derived_node(
        "publication",
        "publication-manifest",
        published_root / "manifest.json",
        ["controls", "deltas"],
    )
    graph = LineageGraph(
        generation_id,
        (
            source_node_row,
            layout_node_row,
            controls_node_row,
            deltas_node_row,
            publication_node_row,
        ),
    )
    lineage_path = export_root / "lineage.json"
    write_lineage(graph, lineage_path)
    lineage_ok = verify_files(
        graph,
        {
            "source": source_path,
            "layout": layout_path,
            "controls": control_csv,
            "deltas": delta_csv,
            "publication": published_root / "manifest.json",
        },
    )

    integrity = create_integrity(
        generation_id,
        {
            "controls_csv": control_csv,
            "controls_json": control_json,
            "deltas_csv": delta_csv,
            "deltas_json": delta_json,
            "lineage": lineage_path,
            "publication_manifest": published_root / "manifest.json",
        },
    )
    integrity_path = export_root / "integrity.json"
    write_integrity(integrity, integrity_path)
    integrity_issues = validate_integrity(integrity)
    files = {
        "controls_csv": control_csv,
        "controls_json": control_json,
        "deltas_csv": delta_csv,
        "deltas_json": delta_json,
        "lineage": lineage_path,
        "integrity": integrity_path,
        "publication_manifest": published_root / "manifest.json",
    }
    archive_path = build_archive(generation_id, files, archive_dir)
    archive_ok = verify_archive(archive_path)
    append_event(
        db,
        generation_id,
        settlement.processed,
        "ARCHIVE",
        str(archive_path),
        {
            "archive_verified": archive_ok,
            "lineage_verified": lineage_ok,
            "registry_manifest": registry_entry.manifest_sha256,
        },
    )
    db.commit()
    q_total, v_total = delta_totals(db, generation_id)
    policy = RetentionPolicy()
    passed = all(
        [
            not contract_issues,
            not migration_issues,
            settlement.balanced,
            registry.validate(),
            lineage_ok,
            not integrity_issues,
            archive_ok,
            verify_journal(db, generation_id),
        ]
    )
    return {
        "passed": passed,
        "generation_id": generation_id,
        "report_contract_issues": [asdict(row) for row in contract_issues],
        "migration_issues": migration_issues,
        "settlement": asdict(settlement),
        "controls": summarize_controls(controls),
        "delta_totals": {
            "quantity": format(q_total, "f"),
            "value": format(v_total, "f"),
        },
        "delta_warehouse_totals": _decimal_map(delta_warehouse_totals(db, generation_id)),
        "delta_item_totals": _decimal_map(delta_item_totals(db, generation_id)),
        "registry": asdict(registry_entry),
        "registry_valid": registry.validate(),
        "lineage_valid": lineage_ok,
        "integrity_issues": integrity_issues,
        "archive_path": str(archive_path),
        "archive_valid": archive_ok,
        "journal_valid": verify_journal(db, generation_id),
        "retention": retention_summary(policy),
    }
