from __future__ import annotations

import hashlib


def partition_id(tenant_id: str, user_id: str, buckets: int = 32) -> int:
    if buckets <= 0:
        raise ValueError("buckets must be positive")
    material = f"{tenant_id}\0{user_id}".encode("utf-8")
    digest = hashlib.sha256(material).digest()
    return int.from_bytes(digest[:4], "big") % buckets


def partition_range(buckets: int = 32) -> range:
    return range(int(buckets))
