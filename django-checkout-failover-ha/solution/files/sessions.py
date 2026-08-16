from __future__ import annotations

import time
from pathlib import Path

from django.conf import settings
from django.core.cache import caches

from controlplane.configutil import ha_config
from controlplane.pin_contract import (
    classify_store,
    get_pin,
    pin_cache_key,
    set_pin,
    store_is_shared,
)


class _CacheBackend:
    def __init__(self, alias: str) -> None:
        self._alias = alias

    def get(self, key: str) -> object | None:
        return caches[self._alias].get(key)

    def set(self, key: str, value: object, timeout: int) -> None:
        caches[self._alias].set(key, value, timeout=timeout)

    def delete(self, key: str) -> None:
        caches[self._alias].delete(key)


def _key(shopper_id: int) -> str:
    return pin_cache_key(shopper_id)


def _pins():
    return caches["pins"]


def _store_class() -> str:
    pins = settings.CACHES.get("pins", {})
    return classify_store(str(pins.get("BACKEND", "")), str(pins.get("LOCATION", "")))


def set_sticky_pin(shopper_id: int) -> None:
    ttl = int(ha_config().get("sticky_seconds", 5))
    store = _store_class()
    set_pin(
        _CacheBackend("pins"),
        shopper_id=shopper_id,
        node_id=str(getattr(settings, "AZ_ID", "az-a")),
        write_lsn=0,
        ttl_seconds=ttl,
        store_class=store,
    )
    # Compatibility marker for callers that still float-compare pin values.
    _pins().set(_key(shopper_id), str(time.time() + ttl), timeout=ttl)


def has_sticky_pin(shopper_id: int) -> bool:
    record = get_pin(_CacheBackend("pins"), shopper_id)
    if record is not None:
        return True
    raw = _pins().get(_key(shopper_id))
    if not raw:
        return False
    try:
        return float(raw) >= time.time()
    except (TypeError, ValueError):
        return False


def pin_store_ok() -> bool:
    root = Path(getattr(settings, "BASE_DIR"))
    cache_dir = root / "state" / "pin-cache"
    try:
        cache_dir.mkdir(parents=True, exist_ok=True)
        probe = cache_dir / ".probe"
        probe.write_text("ok", encoding="utf-8")
        return store_is_shared(_store_class())
    except OSError:
        return False
