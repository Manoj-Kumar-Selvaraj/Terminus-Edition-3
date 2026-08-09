from __future__ import annotations

from django.http import HttpRequest, HttpResponse, JsonResponse

from controlplane.reports import failover_status


def healthz(request: HttpRequest) -> HttpResponse:
    return JsonResponse({"alive": True}, status=200)


def readyz(request: HttpRequest) -> HttpResponse:
    payload = failover_status()
    accepting = bool(payload.get("accepting_checkout"))
    return JsonResponse({"accepting_checkout": accepting}, status=200 if accepting else 503)
