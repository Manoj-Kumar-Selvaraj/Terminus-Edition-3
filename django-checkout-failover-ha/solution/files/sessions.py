from __future__ import annotations

import time
from pathlib import Path

from django.conf import settings
from django.core.cache import caches

from controlplane.configutil import ha_config


def _key(shopper_id: int) -> str:
    return f"sticky:shopper:{shopper_id}"


def _pins():
    return caches["pins"]


def set_sticky_pin(shopper_id: int) -> None:
    ttl = int(ha_config().get("sticky_seconds", 5))
    _pins().set(_key(shopper_id), str(time.time() + ttl), timeout=ttl)


def has_sticky_pin(shopper_id: int) -> bool:
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
        return True
    except OSError:
        return False
