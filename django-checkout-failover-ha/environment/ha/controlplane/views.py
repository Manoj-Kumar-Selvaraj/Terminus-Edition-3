from __future__ import annotations

from django.http import HttpRequest, HttpResponse, JsonResponse

from controlplane.desk_state import collect_desk_snapshot
from controlplane.readiness_policy import health_http_status


def healthz(request: HttpRequest) -> HttpResponse:
    status = health_http_status(True)
    return JsonResponse({"alive": True}, status=status)


def readyz(request: HttpRequest) -> HttpResponse:
    snap = collect_desk_snapshot()
    # Starter process answers while operator cleanup is incomplete.
    return JsonResponse(
        {"accepting_checkout": True, "blockers": snap.blocker_summary},
        status=200,
    )
