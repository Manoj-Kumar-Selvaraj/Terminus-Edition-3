from __future__ import annotations

import posixpath

from spool.errors import VfsError


def tenant_prefix(tenant: str) -> str:
    return f"/t/{tenant}"


def resolve(tenant: str, cli_path: str) -> str:
    if not cli_path.startswith("/"):
        raise VfsError("EINVAL", path=cli_path)
    prefix = tenant_prefix(tenant)
    full = posixpath.normpath(prefix + cli_path)
    if full != prefix and not full.startswith(prefix + "/"):
        raise VfsError("EPERM", code="TENANT_ESCAPE", path=cli_path)
    return full


def split_parts(full: str) -> list[str]:
    if full == "/":
        return []
    return [p for p in full.split("/") if p]
