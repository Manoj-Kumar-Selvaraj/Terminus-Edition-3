"""Quota accounting and audit trail behavioral tests."""

from __future__ import annotations

from conftest import create_endpoint, create_tenant, enqueue


def test_f2p_quota_ignores_failed_attempts(outbox):
    """Failed deliveries do not consume the rolling successful-delivery quota."""
    t = create_tenant(outbox["api"], "quota1", quota=1)
    bad = create_endpoint(outbox["api"], t["id"], "http://127.0.0.1:1/fail", max_attempts=3)
    good = create_endpoint(outbox["api"], t["id"], outbox["sink"]["url"], secret="s2")
    ev_bad, _ = enqueue(outbox["api"], bad["id"], {"n": 1})
    outbox["api"](
        "POST",
        f"/api/v1/events/{ev_bad['id']}/claim",
        json={"lease_owner": "w", "lease_seconds": 30},
    )
    outbox["api"](
        "POST",
        f"/api/v1/events/{ev_bad['id']}/deliver",
        json={"lease_owner": "w"},
    )
    # Still able to enqueue and deliver one success under quota=1
    ev_ok, code = enqueue(outbox["api"], good["id"], {"n": 2})
    assert code == 201, ev_ok
    outbox["api"](
        "POST",
        f"/api/v1/events/{ev_ok['id']}/claim",
        json={"lease_owner": "w2", "lease_seconds": 30},
    )
    d = outbox["api"](
        "POST",
        f"/api/v1/events/{ev_ok['id']}/deliver",
        json={"lease_owner": "w2"},
    )
    assert d.status_code == 200, d.text
    assert d.json()["status"] == "delivered"


def test_f2p_quota_blocks_enqueue_after_success(outbox):
    """After successful deliveries fill the hour window, enqueue returns 429."""
    t = create_tenant(outbox["api"], "quota2", quota=1)
    ep = create_endpoint(outbox["api"], t["id"], outbox["sink"]["url"])
    ev, _ = enqueue(outbox["api"], ep["id"], {"n": 1})
    outbox["api"](
        "POST",
        f"/api/v1/events/{ev['id']}/claim",
        json={"lease_owner": "w", "lease_seconds": 30},
    )
    outbox["api"](
        "POST",
        f"/api/v1/events/{ev['id']}/deliver",
        json={"lease_owner": "w"},
    )
    ev2, code = enqueue(outbox["api"], ep["id"], {"n": 2})
    assert code == 429
    assert ev2["error"] == "quota_exceeded"


def test_f2p_audit_records_enqueue(outbox):
    """Enqueue writes an audit action of enqueue."""
    t = create_tenant(outbox["api"], "aud1")
    ep = create_endpoint(outbox["api"], t["id"], outbox["sink"]["url"])
    enqueue(outbox["api"], ep["id"], {"n": 1})
    r = outbox["api"]("GET", "/api/v1/audit?limit=50")
    assert r.status_code == 200
    actions = [e["action"] for e in r.json()["events"]]
    assert "enqueue" in actions


def test_f2p_audit_records_claim(outbox):
    """Successful claim writes a claim audit event."""
    t = create_tenant(outbox["api"], "aud2")
    ep = create_endpoint(outbox["api"], t["id"], outbox["sink"]["url"])
    ev, _ = enqueue(outbox["api"], ep["id"], {"n": 1})
    outbox["api"](
        "POST",
        f"/api/v1/events/{ev['id']}/claim",
        json={"lease_owner": "auditor", "lease_seconds": 30},
    )
    r = outbox["api"]("GET", "/api/v1/audit?limit=100")
    actions = [e["action"] for e in r.json()["events"]]
    assert "claim" in actions


def test_f2p_audit_records_dlq_transition(outbox):
    """Transition into dlq writes a dlq audit action."""
    t = create_tenant(outbox["api"], "aud3")
    ep = create_endpoint(outbox["api"], t["id"], "http://127.0.0.1:1/x", max_attempts=1)
    ev, _ = enqueue(outbox["api"], ep["id"], {"n": 1})
    outbox["api"](
        "POST",
        f"/api/v1/events/{ev['id']}/claim",
        json={"lease_owner": "w", "lease_seconds": 30},
    )
    outbox["api"](
        "POST",
        f"/api/v1/events/{ev['id']}/deliver",
        json={"lease_owner": "w"},
    )
    r = outbox["api"]("GET", "/api/v1/audit?limit=100")
    actions = [e["action"] for e in r.json()["events"]]
    assert "dlq" in actions


def test_f2p_audit_records_pause(outbox):
    """Pause writes a pause audit action for the endpoint."""
    t = create_tenant(outbox["api"], "aud4")
    ep = create_endpoint(outbox["api"], t["id"], outbox["sink"]["url"])
    outbox["api"]("POST", f"/api/v1/endpoints/{ep['id']}/pause")
    r = outbox["api"]("GET", "/api/v1/audit?limit=50")
    actions = [e["action"] for e in r.json()["events"]]
    assert "pause" in actions


def test_f2p_deliver_ok_audit(outbox):
    """Successful delivery writes deliver.ok audit action."""
    t = create_tenant(outbox["api"], "aud5")
    ep = create_endpoint(outbox["api"], t["id"], outbox["sink"]["url"])
    ev, _ = enqueue(outbox["api"], ep["id"], {"n": 1})
    outbox["api"](
        "POST",
        f"/api/v1/events/{ev['id']}/claim",
        json={"lease_owner": "w", "lease_seconds": 30},
    )
    outbox["api"](
        "POST",
        f"/api/v1/events/{ev['id']}/deliver",
        json={"lease_owner": "w"},
    )
    r = outbox["api"]("GET", "/api/v1/audit?limit=100")
    actions = [e["action"] for e in r.json()["events"]]
    assert "deliver.ok" in actions
