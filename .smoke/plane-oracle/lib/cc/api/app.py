"""Request router for the control-plane HTTP surface.

``handle`` is the public entry point: it takes a method, a path with optional
query string, request headers, and a decoded JSON body, and returns the status
code and response object. The socket server in :mod:`cc.server` is a thin
wrapper over this function.
"""

from __future__ import annotations

import re
from typing import Any, Callable, Mapping
from urllib.parse import parse_qs, urlsplit

from cc import VERSION
from cc.api import routes_audit, routes_pipelines, routes_prs, routes_repos, routes_webhooks
from cc.errors import CcError, NotFound, ValidationException, as_cc_error

Handler = Callable[..., tuple[int, dict[str, Any]]]
API_PREFIX = "/api/v1"


def health(_match: re.Match[str], _query: dict[str, list[str]], _headers: Any, _body: Any):
    """Liveness probe; no identity required."""
    return 200, {"ok": True, "service": "codecommit-control-plane", "version": VERSION}


ROUTES: list[tuple[str, re.Pattern[str], Handler]] = [
    ("GET", re.compile(rf"^{API_PREFIX}/health$"), health),
    ("GET", re.compile(rf"^{API_PREFIX}/repos$"), routes_repos.list_repos),
    ("GET", re.compile(rf"^{API_PREFIX}/repos/(?P<repo>[^/]+)/refs$"), routes_repos.list_refs),
    ("POST", re.compile(rf"^{API_PREFIX}/repos/(?P<repo>[^/]+)/push$"), routes_repos.push),
    ("GET", re.compile(rf"^{API_PREFIX}/prs$"), routes_prs.list_prs),
    ("POST", re.compile(rf"^{API_PREFIX}/prs$"), routes_prs.create_pr),
    ("GET", re.compile(rf"^{API_PREFIX}/prs/(?P<pr_id>\d+)$"), routes_prs.get_pr),
    ("POST", re.compile(rf"^{API_PREFIX}/prs/(?P<pr_id>\d+)/approvals$"), routes_prs.approve_pr),
    ("POST", re.compile(rf"^{API_PREFIX}/prs/(?P<pr_id>\d+)/merge$"), routes_prs.merge_pr),
    ("POST", re.compile(rf"^{API_PREFIX}/pipelines/deliver$"), routes_pipelines.deliver),
    ("GET", re.compile(rf"^{API_PREFIX}/pipelines/journal$"), routes_pipelines.journal),
    ("GET", re.compile(rf"^{API_PREFIX}/audit$"), routes_audit.query),
    ("GET", re.compile(rf"^{API_PREFIX}/webhooks/outbox$"), routes_webhooks.outbox),
    ("POST", re.compile(rf"^{API_PREFIX}/webhooks/dispatch$"), routes_webhooks.dispatch),
]


def split_target(target: str) -> tuple[str, dict[str, list[str]]]:
    """Separate the path from its query parameters."""
    parts = urlsplit(target)
    return parts.path or "/", parse_qs(parts.query)


def _match_route(method: str, path: str) -> tuple[Handler, re.Match[str]]:
    allowed: list[str] = []
    for route_method, pattern, handler in ROUTES:
        match = pattern.match(path)
        if match is None:
            continue
        if route_method == method:
            return handler, match
        allowed.append(route_method)
    if allowed:
        raise ValidationException(
            "METHOD_NOT_ALLOWED", f"{method} is not supported for {path}", allow=sorted(allowed)
        )
    raise NotFound("NO_SUCH_ROUTE", f"no route for {method} {path}")


def require_body(body: Any) -> dict[str, Any]:
    """Reject a mutating request that did not carry a JSON object."""
    if body is None:
        raise ValidationException("MISSING_BODY", "a JSON object body is required")
    if not isinstance(body, dict):
        raise ValidationException("BAD_BODY", "request body must be a JSON object")
    return body


def field(body: Mapping[str, Any], name: str) -> str:
    """Read a required string field from a request body."""
    value = body.get(name)
    if value is None or str(value).strip() == "":
        raise ValidationException("MISSING_FIELD", f"body field {name!r} is required")
    return str(value).strip()


def single(query: Mapping[str, list[str]], name: str) -> str | None:
    """First value of an optional query parameter."""
    values = query.get(name)
    if not values:
        return None
    text = values[0].strip()
    return text or None


def handle(
    method: str,
    target: str,
    headers: Mapping[str, Any] | None = None,
    body: Any = None,
) -> tuple[int, dict[str, Any]]:
    """Route one request and render either its result or a structured error."""
    path, query = split_target(target)
    try:
        handler, match = _match_route(method.upper(), path)
        return handler(match, query, headers, body)
    except CcError as exc:
        return exc.status, exc.payload()
    except Exception as exc:  # noqa: BLE001 - surface unexpected faults as 500 JSON
        wrapped = as_cc_error(exc)
        return wrapped.status, wrapped.payload()
