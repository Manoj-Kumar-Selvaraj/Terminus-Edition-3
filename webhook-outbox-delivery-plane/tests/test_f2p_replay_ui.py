"""DLQ replay auth and UI contract behavioral tests."""

from __future__ import annotations

from conftest import APP, create_endpoint, create_tenant, enqueue


def _force_dlq(api, event_id: str, owner: str = "w") -> None:
    api("POST", f"/api/v1/events/{event_id}/claim", json={"lease_owner": owner, "lease_seconds": 30})
    api("POST", f"/api/v1/events/{event_id}/deliver", json={"lease_owner": owner})


def test_f2p_replay_requires_token_when_configured(outbox):
    """Replay without bearer fails with unauthorized when OUTBOX_TOKEN is set."""
    t = create_tenant(outbox["api"], "rep1")
    ep = create_endpoint(outbox["api"], t["id"], "http://127.0.0.1:1/x", max_attempts=1)
    ev, _ = enqueue(outbox["api"], ep["id"], {"n": 1})
    _force_dlq(outbox["api"], ev["id"])
    got = outbox["api"]("GET", f"/api/v1/events/{ev['id']}")
    assert got.json()["status"] == "dlq"
    r = outbox["api"]("POST", f"/api/v1/events/{ev['id']}/replay")
    assert r.status_code == 401
    assert r.json()["error"] == "unauthorized"


def test_f2p_replay_with_token_returns_pending(outbox):
    """Valid bearer token replays a dlq event back to pending."""
    t = create_tenant(outbox["api"], "rep2")
    ep = create_endpoint(outbox["api"], t["id"], "http://127.0.0.1:1/x", max_attempts=1)
    ev, _ = enqueue(outbox["api"], ep["id"], {"n": 1})
    _force_dlq(outbox["api"], ev["id"])
    r = outbox["api"](
        "POST",
        f"/api/v1/events/{ev['id']}/replay",
        headers={"Authorization": f"Bearer {outbox['token']}"},
    )
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "pending"
    aud = outbox["api"]("GET", "/api/v1/audit?limit=100")
    assert "replay" in [e["action"] for e in aud.json()["events"]]


def test_f2p_resume_allows_claim_again(outbox):
    """After resume, claims against a previously paused endpoint succeed."""
    t = create_tenant(outbox["api"], "res1")
    ep = create_endpoint(outbox["api"], t["id"], outbox["sink"]["url"])
    ev, _ = enqueue(outbox["api"], ep["id"], {"n": 1})
    outbox["api"]("POST", f"/api/v1/endpoints/{ep['id']}/pause")
    outbox["api"]("POST", f"/api/v1/endpoints/{ep['id']}/resume")
    r = outbox["api"](
        "POST",
        f"/api/v1/events/{ev['id']}/claim",
        json={"lease_owner": "worker-a", "lease_seconds": 30},
    )
    assert r.status_code == 200
    assert r.json()["status"] == "claimed"


def test_f2p_ui_index_served(outbox):
    """Static UI index is served from /."""
    r = outbox["api"]("GET", "/")
    assert r.status_code == 200
    assert "Outbox Delivery Plane" in r.text
    assert 'id="error-box"' in r.text


def test_f2p_ui_js_uses_lease_owner_fields(outbox):
    """UI claim helper posts lease_owner and lease_seconds field names."""
    js = (APP / "ui" / "js" / "app.js").read_text(encoding="utf-8")
    assert "lease_owner" in js
    assert "lease_seconds" in js
    assert "error-box" in js or "showError" in js


def test_f2p_ui_js_surfaces_api_errors(outbox):
    """UI script writes API error text into the error-box element."""
    js = (APP / "ui" / "js" / "app.js").read_text(encoding="utf-8")
    assert "error-box" in js
    assert "textContent" in js
    assert "data.error" in js or "data && data.error" in js


def test_f2p_schema_file_present(outbox):
    """Schema SQL used on boot is present under the product tree."""
    schema = APP / "db" / "schema.sql"
    assert schema.is_file()
    text = schema.read_text(encoding="utf-8")
    assert "CREATE TABLE" in text and "delivery_attempts" in text
