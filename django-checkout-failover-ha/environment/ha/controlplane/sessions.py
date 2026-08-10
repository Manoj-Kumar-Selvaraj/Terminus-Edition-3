"""Starter pin store: Django DB sessions + per-process locmem."""
from __future__ import annotations

import time

from django.core.cache import caches

from controlplane.configutil import ha_config
from controlplane.models import ShopSession


def _key(shopper_id: int) -> str:
    return f"sticky:shopper:{shopper_id}"


def set_sticky_pin(shopper_id: int) -> None:
    ttl = int(ha_config().get("sticky_seconds", 5))
    expires = str(time.time() + ttl)
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
