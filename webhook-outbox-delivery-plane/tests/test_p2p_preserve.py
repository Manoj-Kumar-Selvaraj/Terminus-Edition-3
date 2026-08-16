"""Preservation tests for already-correct starter behaviors."""

from __future__ import annotations

from conftest import create_endpoint, create_tenant, enqueue


def test_p2p_health_remains_ok(outbox):
    """Health stays available after unrelated tenant creation."""
    create_tenant(outbox["api"], "p2p1")
    r = outbox["api"]("GET", "/api/v1/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_p2p_get_missing_event_404(outbox):
    """Unknown event ids return not_found."""
    r = outbox["api"]("GET", "/api/v1/events/evt_does_not_exist")
    assert r.status_code == 404
    assert r.json()["error"] == "not_found"


def test_p2p_invalid_payload_rejected(outbox):
    """Non-object payload is rejected with 400."""
    t = create_tenant(outbox["api"], "p2p2")
    ep = create_endpoint(outbox["api"], t["id"], outbox["sink"]["url"])
    r = outbox["api"](
        "POST",
        f"/api/v1/endpoints/{ep['id']}/events",
        json={"payload": [1, 2, 3]},
    )
    assert r.status_code == 400


def test_p2p_list_tenants_includes_created(outbox):
    """Created tenants appear in the tenant list."""
    t = create_tenant(outbox["api"], "p2p3")
    r = outbox["api"]("GET", "/api/v1/tenants")
    assert r.status_code == 200
    assert any(x["id"] == t["id"] for x in r.json()["tenants"])


def test_p2p_enqueue_audit_detail_has_endpoint(outbox):
    """Enqueue audit detail includes endpoint_id for operators."""
    t = create_tenant(outbox["api"], "p2p4")
    ep = create_endpoint(outbox["api"], t["id"], outbox["sink"]["url"])
    enqueue(outbox["api"], ep["id"], {"z": 1})
    r = outbox["api"]("GET", "/api/v1/audit?limit=20")
    enq = next(e for e in r.json()["events"] if e["action"] == "enqueue")
    assert enq["detail"].get("endpoint_id") == ep["id"]
