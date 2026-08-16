"""Route delivery and audit events to notification sinks."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from cc import home
from cc.audit import query as audit_query
from cc.pipeline_admin import journal_for, load_bindings
from cc.util import dump_json, load_json, read_jsonl
from cc.webhook_admin import load_webhooks


def load_routes() -> list[dict[str, Any]]:
    return list(
        load_json(home.var_dir() / "notification-routes.json", {"routes": []}).get("routes") or []
    )


def save_routes(routes: list[dict[str, Any]]) -> None:
    dump_json(home.var_dir() / "notification-routes.json", {"routes": routes})


def upsert_route(route: dict[str, Any]) -> dict[str, Any]:
    routes = load_routes()
    rid = str(route.get("id"))
    routes = [r for r in routes if str(r.get("id")) != rid]
    routes.append(route)
    save_routes(routes)
    return route


def routes_for(event_type: str, repo: str | None = None) -> list[dict[str, Any]]:
    matched: list[dict[str, Any]] = []
    for route in load_routes():
        if route.get("event_type") not in (event_type, "*"):
            continue
        repos = route.get("repos") or ["*"]
        if repo and "*" not in repos and repo not in repos:
            continue
        matched.append(route)
    return matched


def fanout_denied_audit(limit: int = 50) -> list[dict[str, Any]]:
    messages: list[dict[str, Any]] = []
    for row in audit_query.denied_only()[:limit]:
        for route in routes_for("audit.denied", str(row.get("repo") or "")):
            messages.append(
                {"route_id": route.get("id"), "channel": route.get("channel"), "payload": row}
            )
    return messages


def fanout_deliveries(repo: str, ref: str) -> list[dict[str, Any]]:
    messages: list[dict[str, Any]] = []
    for row in journal_for(repo, ref):
        for route in routes_for("pipeline.delivered", repo):
            messages.append(
                {"route_id": route.get("id"), "channel": route.get("channel"), "payload": row}
            )
    return messages


def outbox_pressure() -> dict[str, Any]:
    by_status: dict[str, int] = defaultdict(int)
    for row in read_jsonl(home.outbox_path()):
        by_status[str(row.get("status") or "unknown")] += 1
    return dict(by_status)


def routing_health() -> dict[str, Any]:
    return {
        "routes": len(load_routes()),
        "webhooks": len(load_webhooks()),
        "bindings": len(load_bindings()),
        "outbox": outbox_pressure(),
        "denied_fanout_sample": len(fanout_denied_audit(10)),
    }


def seed_default_routes() -> list[dict[str, Any]]:
    defaults = [
        {"id": "deny-slack", "event_type": "audit.denied", "channel": "slack", "repos": ["*"]},
        {
            "id": "deliver-pager",
            "event_type": "pipeline.delivered",
            "channel": "pager",
            "repos": ["ledger"],
        },
        {"id": "all-email", "event_type": "*", "channel": "email", "repos": ["*"]},
    ]
    for route in defaults:
        upsert_route(route)
    return load_routes()
