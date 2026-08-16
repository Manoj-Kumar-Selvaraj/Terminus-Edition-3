from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from django.conf import settings

from controlplane.ha_config import as_public_dict, load_ha_config


@lru_cache(maxsize=1)
def ha_config() -> dict:
    path = Path(getattr(settings, "HA_CONFIG_PATH"))
    loaded = load_ha_config(path)
    return {**as_public_dict(loaded), **loaded.raw}
