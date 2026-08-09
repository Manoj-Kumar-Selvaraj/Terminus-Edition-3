from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from django.conf import settings


@lru_cache(maxsize=1)
def ha_config() -> dict:
    path = Path(getattr(settings, "HA_CONFIG_PATH"))
    return json.loads(path.read_text(encoding="utf-8"))
