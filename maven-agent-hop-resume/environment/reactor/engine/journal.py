from __future__ import annotations

import json

from engine.paths import JOURNAL


def load_journal() -> dict:
    return json.loads(JOURNAL.read_text(encoding="utf-8"))


def save_journal(data: dict) -> None:
    JOURNAL.parent.mkdir(parents=True, exist_ok=True)
    JOURNAL.write_text(json.dumps(data, indent=2, sort_keys=False) + "\n", encoding="utf-8")


def empty_stage() -> dict:
    return {
        "status": "pending",
        "agent_id": None,
        "agent_labels": [],
        "modules_ok": [],
        "skipped_modules": [],
        "failed_module": None,
    }
