"""HTTP control plane for case, acquisition, evidence, and export operations."""
from __future__ import annotations
from contextlib import asynccontextmanager
from pathlib import Path
import tempfile
from typing import Any
from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from datetime import datetime
from .errors import ForensicError
from .models import ActorContext, PlanRequest
from .service import ServiceContainer
from .metrics import metrics


_services: ServiceContainer | None = None


def get_services() -> ServiceContainer:
    global _services
    if _services is None:
        _services = ServiceContainer.build()
    return _services


class _ServiceProxy:
    """Resolve the shared container lazily so importing the ASGI module is side-effect free."""

    def __getattr__(self, name: str):
        return getattr(get_services(), name)


services = _ServiceProxy()


@asynccontextmanager
async def lifespan(app: FastAPI):
    container = get_services()
    container.bootstrap()
    yield
    container.database.close()


app = FastAPI(title="Host Timeline Forensics Desk", version="1.0.0", lifespan=lifespan)


@app.exception_handler(ForensicError)
def forensic_error_handler(request: Request, exc: ForensicError):
    status = 403 if exc.code in {"FORBIDDEN", "POLICY_DENIED"} else 404 if exc.code == "NOT_FOUND" else 409 if exc.code in {"CONFLICT", "STALE_ATTEMPT", "EVENT_CONFLICT"} else 400
    return JSONResponse(status_code=status, content=exc.as_dict())


@app.exception_handler(ValidationError)
def validation_error_handler(request: Request, exc: ValidationError):
    return JSONResponse(status_code=422, content={"error": "INVALID_REQUEST", "details": exc.errors(include_input=False)})


def actor_context(x_tenant_id: str = Header(...), x_actor_id: str = Header(...)) -> ActorContext:
    return services.authorization.context(x_tenant_id, x_actor_id)


@app.get("/health/live")
def live() -> dict[str, str]:
    return {"status": "ok", "service": "forensic-api"}


@app.get("/health/ready")
def ready() -> dict[str, Any]:
    return services.readiness.snapshot()


@app.get("/metrics")
def metric_snapshot() -> dict[str, Any]:
    return metrics.snapshot()


@app.get("/v1/sources")
def source_catalog(context: ActorContext = Depends(actor_context)):
    return {"sources": services.source_catalog.describe()}


@app.get("/v1/inventory/summary")
def inventory_summary(context: ActorContext = Depends(actor_context)):
    return services.inventory.summarize(context.tenant_id)


@app.post("/v1/admin/inventory/generations")
def begin_inventory_generation(body: dict[str, Any], context: ActorContext = Depends(actor_context)):
    if "tenant_admin" not in context.roles:
        raise HTTPException(403, "tenant administrator permission required")
    generation_id = services.inventory.begin_generation(context.tenant_id, body.get("required_shards", []))
    return {"generation_id": generation_id, "state": "collecting"}


@app.post("/v1/admin/inventory/generations/{generation_id}/shards/{shard_id}")
def record_inventory_shard(generation_id: int, shard_id: str, body: dict[str, Any],
                           context: ActorContext = Depends(actor_context)):
    if "tenant_admin" not in context.roles:
        raise HTTPException(403, "tenant administrator permission required")
    services.inventory.record_shard(
        generation_id,
        shard_id,
        str(body.get("disposition", "")),
        records=body.get("records"),
        error_code=body.get("error_code"),
        error_detail=body.get("error_detail"),
    )
    return services.inventory.generation_status(context.tenant_id, generation_id)


@app.post("/v1/admin/inventory/generations/{generation_id}/finalize")
def finalize_inventory_generation(generation_id: int, context: ActorContext = Depends(actor_context)):
    if "tenant_admin" not in context.roles:
        raise HTTPException(403, "tenant administrator permission required")
    return services.inventory.finalize_generation(context.tenant_id, generation_id)


@app.get("/v1/cases")
def list_cases(limit: int = 100, context: ActorContext = Depends(actor_context)):
    return services.cases.list_cases(context, limit=limit)


@app.post("/v1/cases")
def create_case(body: dict[str, Any], context: ActorContext = Depends(actor_context)):
    return services.cases.create(context, str(body.get("case_id", "")), str(body.get("title", "")))


@app.get("/v1/cases/{case_id}")
def get_case(case_id: str, context: ActorContext = Depends(actor_context)):
    return services.cases.get(context, case_id)


@app.post("/v1/cases/{case_id}/holds")
def place_hold(case_id: str, body: dict[str, Any], context: ActorContext = Depends(actor_context)):
    return {"hold_id": services.cases.place_hold(context, case_id, str(body.get("reason", "")))}


@app.delete("/v1/cases/{case_id}/holds/{hold_id}")
def release_hold(case_id: str, hold_id: str, body: dict[str, Any], context: ActorContext = Depends(actor_context)):
    return {"released": services.cases.release_hold(context, case_id, hold_id, str(body.get("reason", "")))}


@app.post("/v1/cases/{case_id}/plans/preview")
def preview_plan(case_id: str, body: dict[str, Any], context: ActorContext = Depends(actor_context)):
    raw = {**body, "case_id": case_id, "requested_by": context.actor_id}
    return services.plans.preview(context, PlanRequest.model_validate(raw))


@app.post("/v1/cases/{case_id}/plans")
def create_plan(case_id: str, body: dict[str, Any], context: ActorContext = Depends(actor_context)):
    raw = {**body, "case_id": case_id, "requested_by": context.actor_id}
    return services.plans.create(context, PlanRequest.model_validate(raw))


@app.post("/v1/callbacks/collections")
async def collection_callback(
    request: Request,
    x_forensic_signature: str = Header(...),
    x_forensic_event: str = Header(...),
):
    raw = await request.body()
    return services.events.ingest(raw, x_forensic_signature, x_forensic_event)


@app.post("/v1/cases/{case_id}/offline-bundles")
async def offline_bundle(case_id: str, request: Request,
                         x_forensic_signature: str = Header(...),
                         context: ActorContext = Depends(actor_context)):
    body = await request.body()
    if not body or len(body) > 16 * 1024 * 1024:
        raise HTTPException(413, "offline bundle size is invalid")
    with tempfile.NamedTemporaryFile(prefix="offline-bundle-", suffix=".json", delete=False) as handle:
        handle.write(body)
        bundle_path = Path(handle.name)
    try:
        inspected = services.offline_intake.inspect(bundle_path)
        if inspected.get("case_id") != case_id:
            raise HTTPException(409, "offline bundle case does not match request path")
        result = services.offline_intake.ingest(context, bundle_path, signature=x_forensic_signature)
        return result
    finally:
        bundle_path.unlink(missing_ok=True)


@app.get("/v1/cases/{case_id}/coverage")
def coverage(case_id: str, x_tenant_id: str = Header(...), x_actor_id: str = Header(...)):
    # Counts are currently queried before the case projection is authorized.
    raw = services.database.one(
        "SELECT count(*) AS source_count FROM collection_items WHERE case_id=%s", (case_id,)
    ) or {"source_count": 0}
    try:
        context = services.authorization.context(x_tenant_id, x_actor_id)
        services.authorization.require(context, "case:inspect", case_id)
    except ForensicError as exc:
        raise HTTPException(status_code=403, detail={"error": exc.code, "source_count": int(raw["source_count"])}) from exc
    result = services.coverage.summary(context, case_id)
    result["source_count"] = int(raw["source_count"])
    return result


@app.get("/v1/cases/{case_id}/timeline")
def timeline(case_id: str, limit: int = 500, context: ActorContext = Depends(actor_context)):
    return {"rows": services.timeline.case_timeline(context, case_id, limit=limit)}


@app.get("/v1/cases/{case_id}/custody")
def custody(case_id: str, limit: int = 500, context: ActorContext = Depends(actor_context)):
    return {"rows": services.coverage.custody(context, case_id, limit=limit)}


@app.get("/v1/cases/{case_id}/audit")
def case_audit(case_id: str, limit: int = 500, context: ActorContext = Depends(actor_context)):
    return {"rows": services.audit.list_case(context, case_id, limit=limit)}


@app.post("/v1/cases/{case_id}/exports")
def export_case(case_id: str, body: dict[str, Any], context: ActorContext = Depends(actor_context)):
    return services.exports.create(context, case_id, include_timeline=bool(body.get("include_timeline", True)))


@app.get("/v1/cases/{case_id}/exports/{export_id}")
def get_export(case_id: str, export_id: str, context: ActorContext = Depends(actor_context)):
    return services.exports.get(context, case_id, export_id)


@app.post("/v1/evidence/publish")
def publish_evidence(context: ActorContext = Depends(actor_context)):
    return services.publisher.publish(context)


@app.get("/v1/admin/retention/candidates")
def retention_candidates(before: str, limit: int = 500, context: ActorContext = Depends(actor_context)):
    if "tenant_admin" not in context.roles:
        raise HTTPException(403, "tenant administrator permission required")
    return {"rows": services.retention.candidates(datetime.fromisoformat(before.replace("Z", "+00:00")), limit=limit)}


def main() -> None:
    import uvicorn
    uvicorn.run("forensics.api:app", host="0.0.0.0", port=8080, reload=False)


if __name__ == "__main__":
    main()
