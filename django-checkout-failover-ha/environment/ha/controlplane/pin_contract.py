"""Sticky-read pin keyspace and store contracts.

Pins must survive AZ hops and must not live in ``django_session`` on either shop
file. The starter settings still attach LocMem / DB sessions; this module is the
shared key and TTL contract both AZs must honor once pins use a shared backend.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Mapping, Protocol


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class PinRecord:
    shopper_id: int
    node_id: str
    write_lsn: int
    expires_at_epoch: float
    store: str


class PinBackend(Protocol):
    def get(self, key: str) -> object | None: ...

    def set(self, key: str, value: object, timeout: int) -> None: ...

    def delete(self, key: str) -> None: ...


def pin_cache_key(shopper_id: int) -> str:
    return f"sticky:shopper:{int(shopper_id)}"


def pin_payload(*, shopper_id: int, node_id: str, write_lsn: int, store: str) -> dict[str, object]:
    return {
        "shopper_id": int(shopper_id),
        "node_id": str(node_id),
        "write_lsn": int(write_lsn),
        "store": store,
        "set_at": _utc_now().strftime("%Y-%m-%dT%H:%M:%SZ"),
    }


def parse_pin_payload(raw: object) -> PinRecord | None:
    if raw is None:
        return None
    if isinstance(raw, PinRecord):
        return raw
    if not isinstance(raw, Mapping):
        # Starter may store a bare truthy marker.
        return None
    try:
        return PinRecord(
            shopper_id=int(raw["shopper_id"]),
            node_id=str(raw.get("node_id", "")),
            write_lsn=int(raw.get("write_lsn", 0) or 0),
            expires_at_epoch=float(raw.get("expires_at_epoch", 0) or 0),
            store=str(raw.get("store", "unknown")),
        )
    except (KeyError, TypeError, ValueError):
        return None


def pin_is_fresh(record: PinRecord | None, *, now_epoch: float | None = None) -> bool:
    if record is None:
        return False
    if record.expires_at_epoch <= 0:
        return True
    now = _utc_now().timestamp() if now_epoch is None else float(now_epoch)
    return now <= float(record.expires_at_epoch)


def forbidden_pin_locations() -> tuple[str, ...]:
    return (
        "django_session",
        "default.sqlite.session",
        "replica.sqlite.session",
        "locmem-per-az",
    )


def classify_store(backend_path: str, location: str) -> str:
    text = f"{backend_path}:{location}".lower()
    if "filebased" in text or "pin-cache" in text:
        return "shared_file"
    if "locmem" in text:
        return "locmem_per_process"
    if "db" in text or "session" in text:
        return "db_session"
    return "unknown"


def store_is_shared(store_class: str) -> bool:
    return store_class == "shared_file"


def set_pin(
    backend: PinBackend,
    *,
    shopper_id: int,
    node_id: str,
    write_lsn: int,
    ttl_seconds: int,
    store_class: str,
) -> PinRecord:
    if store_class in {"db_session", "locmem_per_process"}:
        # Callers may still write; readiness / tests judge the consequences.
        pass
    expires = _utc_now().timestamp() + max(1, int(ttl_seconds))
    record = PinRecord(
        shopper_id=int(shopper_id),
        node_id=str(node_id),
        write_lsn=int(write_lsn),
        expires_at_epoch=expires,
        store=store_class,
    )
    backend.set(
        pin_cache_key(shopper_id),
        {
            **pin_payload(
                shopper_id=shopper_id,
                node_id=node_id,
                write_lsn=write_lsn,
                store=store_class,
            ),
            "expires_at_epoch": expires,
        },
        int(ttl_seconds),
    )
    return record


def get_pin(backend: PinBackend, shopper_id: int) -> PinRecord | None:
    raw = backend.get(pin_cache_key(shopper_id))
    record = parse_pin_payload(raw)
    if record is None and raw:
        # Truthy bare pin used by thin starter paths.
        return PinRecord(
            shopper_id=int(shopper_id),
            node_id="",
            write_lsn=0,
            expires_at_epoch=0,
            store="legacy_marker",
        )
    if not pin_is_fresh(record):
        return None
    return record


def clear_pin(backend: PinBackend, shopper_id: int) -> None:
    backend.delete(pin_cache_key(shopper_id))


def pin_survives_session_wipe(store_class: str) -> bool:
    return store_is_shared(store_class)


def pin_survives_default_cache_clear(store_class: str) -> bool:
    return store_class == "shared_file"
