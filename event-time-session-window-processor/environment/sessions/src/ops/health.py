from __future__ import annotations

from pathlib import Path

from src.catalog.connect import catalog_exists
from src.catalog.inventory import inventory_snapshot
from src.paths import CONFIG_PATH, JOURNAL_PATH, LEDGER_PATH, OPEN_SESSIONS_PATH


def runtime_layout_ok() -> dict[str, bool]:
    return {
        "config": CONFIG_PATH.is_file(),
        "journal_parent": JOURNAL_PATH.parent.is_dir(),
        "open_parent": OPEN_SESSIONS_PATH.parent.is_dir(),
        "warehouse": LEDGER_PATH.is_file() and LEDGER_PATH.stat().st_size > 0,
        "catalog": catalog_exists(),
    }


def missing_required() -> list[str]:
    layout = runtime_layout_ok()
    return [name for name, ok in layout.items() if not ok]


def warehouse_ready() -> bool:
    if not runtime_layout_ok()["warehouse"]:
        return False
    snap = inventory_snapshot()
    if not snap.get("available"):
        return LEDGER_PATH.is_file()
    return bool(snap.get("schema_ok")) and int(snap.get("event_count") or 0) > 0


def config_present(path: Path | None = None) -> bool:
    return (path or CONFIG_PATH).is_file()
