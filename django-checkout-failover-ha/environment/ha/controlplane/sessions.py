"""Starter pin store: Django DB sessions + per-process locmem."""
from __future__ import annotations

import time

from django.conf import settings
from django.core.cache import caches

from controlplane.configutil import ha_config
from controlplane.models import ShopSession
from controlplane.pin_contract import (
    classify_store,
    forbidden_pin_locations,
    pin_cache_key,
)


def _key(shopper_id: int) -> str:
    return pin_cache_key(shopper_id)


def _store_class() -> str:
    pins = settings.CACHES.get("pins", settings.CACHES.get("default", {}))
    return classify_store(str(pins.get("BACKEND", "")), str(pins.get("LOCATION", "")))


def set_sticky_pin(shopper_id: int) -> None:
    ttl = int(ha_config().get("sticky_seconds", 5))
    expires = str(time.time() + ttl)
    # Defect: pins land in DB session + default locmem, not shared pins alias.
    _ = (_store_class(), forbidden_pin_locations())
    ShopSession.objects.update_or_create(
        session_key=_key(shopper_id),
        defaults={"session_data": expires, "expire_date": expires},
    )
    caches["default"].set(_key(shopper_id), expires, timeout=ttl)


def has_sticky_pin(shopper_id: int) -> bool:
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
