"""Exclusive ref leases for protected merge destinations."""

from __future__ import annotations

import time
import uuid
from typing import Any

from cc import home
from cc.errors import ValidationException
from cc.util import dump_json, full_ref, load_json


def leases_path():
    return home.var_dir() / "ref-leases.json"


def _doc() -> dict[str, Any]:
    return load_json(leases_path(), {"leases": {}})


def _save(doc: dict[str, Any]) -> None:
    dump_json(leases_path(), doc)


def _key(repo: str, ref: str) -> str:
    return f"{repo}|{full_ref(ref)}"


def acquire(repo: str, ref: str, principal: str, *, ttl_sec: int = 120) -> dict[str, Any]:
    doc = _doc()
    leases = dict(doc.get("leases") or {})
    key = _key(repo, ref)
    now = time.time()
    existing = leases.get(key)
    if existing and float(existing.get("expires_at") or 0) > now and existing.get("principal") != principal:
        raise ValidationException(code="REF_LEASE_HELD", repo=repo, ref=full_ref(ref))
    token = str(uuid.uuid4())
    entry = {
        "repo": repo,
        "ref": full_ref(ref),
        "principal": principal,
        "token": token,
        "expires_at": now + ttl_sec,
        "acquired_at": now,
    }
    leases[key] = entry
    doc["leases"] = leases
    _save(doc)
    return entry


def release(repo: str, ref: str, token: str) -> bool:
    doc = _doc()
    leases = dict(doc.get("leases") or {})
    key = _key(repo, ref)
    entry = leases.get(key)
    if not entry or entry.get("token") != token:
        return False
    leases.pop(key, None)
    doc["leases"] = leases
    _save(doc)
    return True


def require_held(repo: str, ref: str, principal: str, token: str | None) -> None:
    doc = _doc()
    entry = (doc.get("leases") or {}).get(_key(repo, ref))
    now = time.time()
    if not entry or float(entry.get("expires_at") or 0) <= now:
        raise ValidationException(code="REF_LEASE_REQUIRED", repo=repo, ref=full_ref(ref))
    if entry.get("principal") != principal:
        raise ValidationException(code="REF_LEASE_HELD", repo=repo, ref=full_ref(ref))
    if token and entry.get("token") != token:
        raise ValidationException(code="REF_LEASE_MISMATCH", repo=repo, ref=full_ref(ref))


def active_leases() -> list[dict[str, Any]]:
    now = time.time()
    return [e for e in (_doc().get("leases") or {}).values() if float(e.get("expires_at") or 0) > now]


def purge_expired() -> int:
    doc = _doc()
    leases = dict(doc.get("leases") or {})
    now = time.time()
    keep = {k: v for k, v in leases.items() if float(v.get("expires_at") or 0) > now}
    removed = len(leases) - len(keep)
    doc["leases"] = keep
    _save(doc)
    return removed
