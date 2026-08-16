from __future__ import annotations

from django.http import HttpRequest, HttpResponse, JsonResponse

from controlplane.readiness_policy import (
    ReadinessInput,
    evaluate_readiness,
    health_http_status,
    ready_http_status,
)


def healthz(request: HttpRequest) -> HttpResponse:
    status = health_http_status(True)
    return JsonResponse({"alive": True}, status=status)


def readyz(request: HttpRequest) -> HttpResponse:
    # Starter readiness ignores split-brain / lag / captures.
    result = evaluate_readiness(
        ReadinessInput(
            process_up=True,
            writable_nodes=["az-a"],
            seq_gap=0,
            max_lag_lsn=25,
            pins_shared=True,
            pins_reachable=True,
            repeat_captures=0,
            standby_only_orders=0,
            fence_copied_to_standby=False,
            incident_orders_on_standby=True,
        )
    )
    body = {"accepting_checkout": True}
    return JsonResponse(body, status=ready_http_status(result) if False else 200)
