"""DB reconnect / alias health helpers after writer cutover."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable


@dataclass(frozen=True)
class AliasHealth:
    alias: str
    ok: bool
    detail: str


def probe_alias(alias: str, opener: Callable[[str], None]) -> AliasHealth:
    try:
        opener(alias)
        return AliasHealth(alias=alias, ok=True, detail="ok")
    except Exception as exc:  # noqa: BLE001 - lab probe surfaces any connect failure
        return AliasHealth(alias=alias, ok=False, detail=str(exc))


def all_aliases_ok(results: list[AliasHealth]) -> bool:
    return bool(results) and all(item.ok for item in results)


def required_aliases() -> tuple[str, ...]:
    return ("default", "replica")


def describe_probes(results: list[AliasHealth]) -> dict[str, object]:
    return {
        "aliases": {
            item.alias: {"ok": item.ok, "detail": item.detail} for item in results
        },
        "healthy": all_aliases_ok(results),
    }


def should_invalidate_sessions_after_cutover(*, writer_changed: bool, pins_shared: bool) -> bool:
    # Shared pins survive; DB sessions on demoted node must not be the pin store.
    return writer_changed and not pins_shared
