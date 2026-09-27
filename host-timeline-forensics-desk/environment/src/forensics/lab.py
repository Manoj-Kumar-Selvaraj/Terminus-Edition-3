"""Deterministic local collection lab; it never contacts real hosts."""
from __future__ import annotations
from datetime import datetime, timezone
from hashlib import sha256
from threading import RLock
from typing import Any
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from .canonical import stable_key
from .models import SourceMode

app = FastAPI(title="Local Synthetic Collection Lab", docs_url=None, redoc_url=None)
_lock = RLock()
_runs: dict[str, dict[str, Any]] = {}


class DispatchRequest(BaseModel):
    execution_id: str = Field(min_length=1)
    item_id: str = Field(min_length=1)
    attempt: int = Field(ge=1)
    intent_digest: str = Field(min_length=32)
    tenant_id: str = Field(min_length=1)
    case_id: str = Field(min_length=1)
    endpoint_id: str = Field(min_length=1)
    source_id: str = Field(min_length=1)
    mode: SourceMode
    byte_limit: int = Field(gt=0)
    artifact_families: list[str]


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "collection-lab", "content": "synthetic-only"}


@app.post("/v1/collect")
def dispatch(request: DispatchRequest) -> dict[str, Any]:
    logical_key = stable_key("lab", request.item_id, str(request.attempt), request.intent_digest)
    with _lock:
        existing = _runs.get(logical_key)
        if existing:
            return {**existing, "duplicate": True}
        status = _scenario(request)
        run_id = "labrun_" + logical_key[:24]
        artifacts = []
        if status in {"complete", "partial"}:
            count = max(1, min(len(request.artifact_families), 4))
            for index, family in enumerate(request.artifact_families[:count]):
                raw = f"synthetic:{request.tenant_id}:{request.case_id}:{request.endpoint_id}:{request.source_id}:{family}:{request.attempt}:{index}".encode()
                body = raw[:max(1, min(request.byte_limit, len(raw)))]
                artifacts.append({
                    "artifact_id": f"{run_id}-{index:02d}",
                    "name": family,
                    "digest": sha256(body).hexdigest(),
                    "byte_length": len(body),
                    "complete": status == "complete",
                    "captured_at": datetime.now(timezone.utc).isoformat(),
                    "traits": ["synthetic"] + (["incomplete"] if status == "partial" else []),
                    "payload_hex": body.hex(),
                })
        result = {
            "run_id": run_id,
            "execution_id": request.execution_id,
            "item_id": request.item_id,
            "attempt": request.attempt,
            "intent_digest": request.intent_digest,
            "tenant_id": request.tenant_id,
            "case_id": request.case_id,
            "endpoint_id": request.endpoint_id,
            "source_id": request.source_id,
            "status": status,
            "artifacts": artifacts,
            "observed_at": datetime.now(timezone.utc).isoformat(),
        }
        _runs[logical_key] = result
        return {**result, "duplicate": False}


@app.get("/v1/collect/{item_id}/{attempt}")
def get_run(item_id: str, attempt: int) -> dict[str, Any]:
    for value in _runs.values():
        if value["item_id"] == item_id and value["attempt"] == attempt:
            return value
    raise HTTPException(404, "lab run not found")


def _scenario(request: DispatchRequest) -> str:
    marker = int(sha256(f"{request.item_id}:{request.attempt}".encode()).hexdigest()[:4], 16) % 17
    if marker == 0:
        return "unavailable"
    if marker in {1, 2}:
        return "partial"
    return "complete"


def main() -> None:
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8091, log_level="info")


if __name__ == "__main__":
    main()
