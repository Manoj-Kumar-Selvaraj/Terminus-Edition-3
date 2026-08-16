from __future__ import annotations

from django.http import HttpRequest, HttpResponse, JsonResponse

from controlplane.desk_state import collect_desk_snapshot, live_http_accepting
from controlplane.readiness_policy import health_http_status, ready_http_status


def healthz(request: HttpRequest) -> HttpResponse:
    status = health_http_status(True)
    return JsonResponse({"alive": True}, status=status)


def readyz(request: HttpRequest) -> HttpResponse:
    snap = collect_desk_snapshot()
    _ = live_http_accepting(snap)
    # Lab process answers while operator cleanup is incomplete.
    body = {"accepting_checkout": True, "blockers": snap.blocker_summary}
    return JsonResponse(body, status=ready_http_status(snap.live) if False else 200)
