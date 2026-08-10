from __future__ import annotations

from engine.journal import save_journal


def put_stash(journal: dict, name: str, modules: list[str], stage: str) -> None:
    journal.setdefault("stash", {})[name] = {
        "modules": list(modules),
        "created_stage": stage,
    }
    save_journal(journal)


def has_stash(journal: dict, name: str | None) -> bool:
    if not name:
        return True
    entry = journal.get("stash", {}).get(name)
    return bool(entry and entry.get("modules"))
