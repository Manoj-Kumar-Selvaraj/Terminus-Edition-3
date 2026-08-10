from __future__ import annotations

from typing import Any

CLUSTER = "platform-mvp-dev"
DOMAIN = "platform.test"
GROUP = "platform-ingress"


def public_hosts(host_map: dict[str, dict[str, Any]]) -> list[str]:
    names = []
    for item in host_map.values():
        host = str(item.get("host") or "")
        if host.endswith("." + DOMAIN) or host == DOMAIN:
            names.append(host)
    return sorted(set(names))


def annotation_matches(item: dict[str, Any]) -> bool:
    return str(item.get("dns_annotation") or "") == str(item.get("host") or "")


def owner_ok(txt_owner: str, policy: str, filters: list[Any]) -> bool:
    normalized = [str(item) for item in filters]
    return txt_owner == CLUSTER and policy == "sync" and DOMAIN in normalized


def publish_zone(host_map: dict[str, dict[str, Any]], txt_owner: str, dns_ok: bool) -> dict[str, Any]:
    records: dict[str, str] = {}
    txt: dict[str, str] = {}
    if not dns_ok:
        return {"records": records, "txt": txt}
    for item in host_map.values():
        host = str(item.get("host") or "")
        if not host or not annotation_matches(item):
            continue
        if item.get("group") != GROUP:
            continue
        records[host] = "127.0.0.1"
        txt[f"_owner.{host}"] = txt_owner
    return {"records": records, "txt": txt}


def sync_deletes_unowned(previous: dict[str, Any], nxt: dict[str, Any], policy: str) -> dict[str, Any]:
    if policy != "sync":
        merged = {
            "records": dict(previous.get("records") or {}),
            "txt": dict(previous.get("txt") or {}),
        }
        merged["records"].update(nxt.get("records") or {})
        merged["txt"].update(nxt.get("txt") or {})
        return merged
    return nxt
