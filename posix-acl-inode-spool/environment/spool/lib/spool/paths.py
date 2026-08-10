from __future__ import annotations

import posixpath

from spool.errors import VfsError


def tenant_prefix(tenant: str) -> str:
    return f"/t/{tenant}"


def resolve(tenant: str, cli_path: str) -> str:
    if not cli_path.startswith("/") or cli_path == "":
        raise VfsError("EINVAL", path=cli_path)
    # Broken: join + normalize without staying inside the tenant prefix.
    full = posixpath.normpath(tenant_prefix(tenant) + cli_path)
    if full == "/":
        return full
    return full


def split_parts(full: str) -> list[str]:
    if full == "/":
        return []
    return [p for p in full.split("/") if p]
