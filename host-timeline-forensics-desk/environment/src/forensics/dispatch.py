"""Source dispatch and ambiguous acknowledgement handling."""
from __future__ import annotations
from typing import Any
import httpx
from .config import get_settings
from .errors import LabUnavailable


class CollectionDispatcher:
    def __init__(self, *, lab_url: str | None = None, timeout: float = 8.0):
        self.lab_url = (lab_url or get_settings().lab_url).rstrip("/")
        self.timeout = timeout

    def dispatch(self, item: dict[str, Any], *, attempt: int, intent_digest: str,
                 tenant_id: str, case_id: str) -> dict[str, Any]:
        body = {
            "execution_id": f"{item['item_id']}:{attempt}",
            "item_id": item["item_id"],
            "attempt": attempt,
            "intent_digest": intent_digest,
            "tenant_id": tenant_id,
            "case_id": case_id,
            "endpoint_id": item["endpoint_id"],
            "source_id": item["source_id"],
            "mode": item["mode"],
            "byte_limit": item["byte_limit"],
            "artifact_families": item["artifact_families"],
        }
        try:
            response = httpx.post(f"{self.lab_url}/v1/collect", json=body, timeout=self.timeout)
            response.raise_for_status()
            return response.json()
        except (httpx.TimeoutException, httpx.NetworkError) as exc:
            raise LabUnavailable(f"collection lab acknowledgement is ambiguous: {exc}") from exc

    def find_attempt(self, item_id: str, attempt: int) -> dict[str, Any] | None:
        try:
            response = httpx.get(f"{self.lab_url}/v1/collect/{item_id}/{attempt}", timeout=self.timeout)
            if response.status_code == 404:
                return None
            response.raise_for_status()
            return response.json()
        except (httpx.TimeoutException, httpx.NetworkError) as exc:
            raise LabUnavailable(f"collection lab lookup failed: {exc}") from exc
