from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


def spool_root() -> Path:
    return Path(os.environ.get("SPOOL_ROOT", "/app/spool"))


def load_identities(root: Path | None = None) -> dict[str, dict[str, Any]]:
    path = (root or spool_root()) / "ops" / "identities.json"
    return json.loads(path.read_text(encoding="utf-8"))


def load_tenants(root: Path | None = None) -> dict[str, dict[str, Any]]:
    path = (root or spool_root()) / "ops" / "tenants.json"
    return json.loads(path.read_text(encoding="utf-8"))


def identity(name: str, root: Path | None = None) -> dict[str, Any]:
    catalog = load_identities(root)
    if name not in catalog:
        raise KeyError(name)
    rec = catalog[name]
    groups = list(rec.get("groups") or [])
    gid = int(rec["gid"])
    if gid not in groups:
        groups.append(gid)
    return {
        "name": name,
        "uid": int(rec["uid"]),
        "gid": gid,
        "groups": [int(g) for g in groups],
    }


def uid_to_name(uid: int, root: Path | None = None) -> str:
    for name, rec in load_identities(root).items():
        if int(rec["uid"]) == int(uid):
            return name
    return str(uid)


def name_to_uid(name: str, root: Path | None = None) -> int:
    catalog = load_identities(root)
    if name.isdigit() and name not in catalog:
        return int(name)
    return int(catalog[name]["uid"])


def gid_to_name(gid: int, tenant: str, root: Path | None = None) -> str:
    groups = load_tenants(root)[tenant].get("groups") or {}
    for name, value in groups.items():
        if int(value) == int(gid):
            return name
    for rec in load_identities(root).values():
        if int(rec["gid"]) == int(gid):
            pass
    return str(gid)


def name_to_gid(name: str, tenant: str, root: Path | None = None) -> int:
    groups = load_tenants(root)[tenant].get("groups") or {}
    if name in groups:
        return int(groups[name])
    if name.isdigit():
        return int(name)
    raise KeyError(name)
