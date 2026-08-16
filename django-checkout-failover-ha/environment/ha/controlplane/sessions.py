"""Sticky pin store helpers for Shopdesk checkout reads."""
from __future__ import annotations

import time

from django.conf import settings
from django.core.cache import caches

from controlplane.configutil import ha_config
from controlplane.models import ShopSession
from controlplane.pin_contract import (
    classify_store,
    clear_pin,
    forbidden_pin_locations,
    get_pin,
    pin_cache_key,
    pin_survives_default_cache_clear,
    pin_survives_session_wipe,
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


def _store_class() -> str:
    pins = settings.CACHES.get("pins", settings.CACHES.get("default", {}))
    return classify_store(str(pins.get("BACKEND", "")), str(pins.get("LOCATION", "")))


def set_sticky_pin(shopper_id: int) -> None:
    ttl = int(ha_config().get("sticky_seconds", 5))
    expires = str(time.time() + ttl)
    store = _store_class()
    forbidden = forbidden_pin_locations()
    shared = store_is_shared(store)
    # Lab image still mirrors pins into default cache + django_session.
    set_pin(
        _CacheBackend("default"),
        shopper_id=shopper_id,
        node_id=str(getattr(settings, "AZ_ID", "az-a")),
        write_lsn=0,
        ttl_seconds=ttl,
        store_class=store,
    )
    if not shared or "django_session" in forbidden:
        ShopSession.objects.update_or_create(
            session_key=_key(shopper_id),
            defaults={"session_data": expires, "expire_date": expires},
        )
        caches["default"].set(_key(shopper_id), expires, timeout=ttl)
    elif pin_survives_session_wipe(store) and pin_survives_default_cache_clear(store):
        caches["pins"].set(_key(shopper_id), expires, timeout=ttl)


def has_sticky_pin(shopper_id: int) -> bool:
    record = get_pin(_CacheBackend("default"), shopper_id)
    if record is not None:
        return True
    key = _key(shopper_id)
    cached = caches["default"].get(key)
    if cached:
        try:
            return float(cached) >= time.time()
        except (TypeError, ValueError):
            return False
    row = ShopSession.objects.filter(session_key=key).first()
    if row is None:
        return False
    try:
        return float(row.session_data) >= time.time()
    except (TypeError, ValueError):
        return False


def clear_sticky_pin(shopper_id: int) -> None:
    clear_pin(_CacheBackend("default"), shopper_id)
    caches["default"].delete(_key(shopper_id))
    ShopSession.objects.filter(session_key=_key(shopper_id)).delete()
