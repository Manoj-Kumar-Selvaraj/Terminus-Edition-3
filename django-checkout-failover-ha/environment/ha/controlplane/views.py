from __future__ import annotations

from django.http import HttpRequest, HttpResponse, JsonResponse


def healthz(request: HttpRequest) -> HttpResponse:
    return JsonResponse({"alive": True})


def readyz(request: HttpRequest) -> HttpResponse:
    return JsonResponse({"accepting_checkout": True})
