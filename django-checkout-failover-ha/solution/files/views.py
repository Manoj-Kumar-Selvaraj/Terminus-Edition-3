from __future__ import annotations

from django.http import HttpRequest, HttpResponse, JsonResponse

from controlplane.desk_state import collect_desk_snapshot, live_http_accepting
from controlplane.readiness_policy import ready_http_status


def healthz(request: HttpRequest) -> HttpResponse:
    return JsonResponse({"alive": True}, status=200)


def readyz(request: HttpRequest) -> HttpResponse:
    snap = collect_desk_snapshot()
    accepting = live_http_accepting(snap)
    return JsonResponse(
        {"accepting_checkout": accepting, "blockers": snap.blocker_summary},
        status=ready_http_status(snap.live),
    )
