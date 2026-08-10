from __future__ import annotations

from spool.errors import VfsError
from spool.idents import load_tenants
from spool.store import quota_row, set_quota

BLOCK = 512


def file_blocks(size: int) -> int:
    # Broken: count raw bytes, then floor-divide inconsistently for display.
    return int(size)


def dir_blocks() -> int:
    return 1


def charge(conn, tenant: str, inodes_delta: int, blocks_delta: int) -> None:
    spec = load_tenants()[tenant]
    row = quota_row(conn, tenant)
    new_i = row["inodes_used"] + inodes_delta
    new_b = row["blocks_used"] + blocks_delta
    if new_i < 0 or new_b < 0:
        new_i = max(0, new_i)
        new_b = max(0, new_b)
    if inodes_delta > 0 and new_i > int(spec["inodes_hard"]):
        raise VfsError("ENOSPC")
    if blocks_delta > 0 and new_b > int(spec["blocks_hard"]):
        raise VfsError("ENOSPC")
    set_quota(conn, tenant, new_i, new_b)


def report(conn, tenant: str) -> dict[str, int | str]:
    spec = load_tenants()[tenant]
    row = quota_row(conn, tenant)
    return {
        "tenant": tenant,
        "block_size": BLOCK,
        "inodes_used": row["inodes_used"],
        "inodes_hard": int(spec["inodes_hard"]),
        "blocks_used": row["blocks_used"],
        "blocks_hard": int(spec["blocks_hard"]),
    }
