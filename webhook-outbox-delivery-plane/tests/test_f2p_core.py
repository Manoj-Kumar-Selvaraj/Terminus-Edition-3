"""Core API, bootstrap, and enqueue contract tests."""

from __future__ import annotations

from conftest import create_endpoint, create_tenant, enqueue


def test_f2p_health_ok(outbox):
    """Health endpoint reports status ok after boot."""
    r = outbox["api"]("GET", "/api/v1/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_f2p_create_tenant_and_endpoint(outbox):
    """Operators can create a tenant and endpoint with quota and secret."""
    t = create_tenant(outbox["api"], "alpha", quota=50)
    assert t["id"].startswith("ten_")
    assert t["deliveries_per_hour"] == 50
    ep = create_endpoint(outbox["api"], t["id"], outbox["sink"]["url"])
    assert ep["id"].startswith("ep_")
    assert ep["hmac_secret"] == "hook-secret"
    assert ep["paused"] is False


def test_f2p_enqueue_pending_event(outbox):
    """Enqueue stores a pending event with payload and returns 201."""
    t = create_tenant(outbox["api"], "beta")
    ep = create_endpoint(outbox["api"], t["id"], outbox["sink"]["url"])
    ev, code = enqueue(outbox["api"], ep["id"], {"order": 1})
    assert code == 201
    assert ev["status"] == "pending"
    assert ev["payload"]["order"] == 1
    assert ev["attempt_count"] == 0


def test_f2p_idempotent_enqueue_returns_existing(outbox):
    """Same endpoint idempotency_key returns the existing event with 200."""
    t = create_tenant(outbox["api"], "gamma")
    ep = create_endpoint(outbox["api"], t["id"], outbox["sink"]["url"])
    ev1, c1 = enqueue(outbox["api"], ep["id"], {"a": 1}, idem="k-1")
    ev2, c2 = enqueue(outbox["api"], ep["id"], {"a": 2}, idem="k-1")
    assert c1 == 201 and c2 == 200
    assert ev1["id"] == ev2["id"]
    assert ev2["payload"]["a"] == 1


def test_f2p_disabled_endpoint_rejects_enqueue(outbox):
    """Disabled endpoints reject enqueue with endpoint_disabled."""
    t = create_tenant(outbox["api"], "delta")
    ep = create_endpoint(outbox["api"], t["id"], outbox["sink"]["url"])
    r = outbox["api"]("PATCH", f"/api/v1/endpoints/{ep['id']}", json={"enabled": False})
    assert r.status_code == 200
    ev, code = enqueue(outbox["api"], ep["id"], {"x": 1})
    assert code == 409
    assert ev["error"] == "endpoint_disabled"


def test_f2p_list_events_and_get_event(outbox):
    """Tenant event list and get-by-id return the enqueued record."""
    t = create_tenant(outbox["api"], "epsilon")
    ep = create_endpoint(outbox["api"], t["id"], outbox["sink"]["url"])
    ev, _ = enqueue(outbox["api"], ep["id"], {"n": 9})
    lst = outbox["api"]("GET", f"/api/v1/tenants/{t['id']}/events")
    assert lst.status_code == 200
    assert any(e["id"] == ev["id"] for e in lst.json()["events"])
    got = outbox["api"]("GET", f"/api/v1/events/{ev['id']}")
    assert got.status_code == 200
    assert got.json()["id"] == ev["id"]


def test_f2p_stats_endpoint_shape(outbox):
    """Stats reports tenant/endpoint counts and by_status map."""
    create_tenant(outbox["api"], "zeta")
    r = outbox["api"]("GET", "/api/v1/stats")
    assert r.status_code == 200
    body = r.json()
    assert "tenants" in body and "endpoints" in body and "by_status" in body
