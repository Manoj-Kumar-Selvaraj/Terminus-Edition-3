from __future__ import annotations

from controlplane.configutil import ha_config
from controlplane.models import Watermark


def watermarks() -> tuple[int, int]:
    primary = Watermark.objects.using("default").filter(role="primary").first()
    replica = Watermark.objects.using("replica").filter(role="replica").first()
    primary_lsn = 0 if primary is None else int(primary.wal_lsn)
    applied = 0 if replica is None else int(replica.applied_lsn)
    return primary_lsn, applied


def lag_lsn() -> int:
    primary_lsn, applied = watermarks()
    return max(0, primary_lsn - applied)


def replica_eligible() -> bool:
    cfg = ha_config()
    return lag_lsn() <= int(cfg.get("max_lag_lsn", 25))
