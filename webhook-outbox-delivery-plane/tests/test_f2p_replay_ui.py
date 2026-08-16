"""DLQ replay auth and UI contract behavioral tests."""

from __future__ import annotations

import re
import time
from datetime import datetime, timezone

from conftest import APP, create_endpoint, create_tenant, enqueue


def _force_dlq(api, event_id: str, owner: str = "w") -> None:
    api("POST", f"/api/v1/events/{event_id}/claim", json={"lease_owner": owner, "lease_seconds": 30})
    api("POST", f"/api/v1/events/{event_id}/deliver", json={"lease_owner": owner})


def _parse_rfc3339(raw: str) -> float:
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    return datetime.fromisoformat(raw).astimezone(timezone.utc).timestamp()


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
    """Replay restores pending, keeps attempt_count, clears lease, sets next_attempt_at~now."""
    t = create_tenant(outbox["api"], "rep2")
    ep = create_endpoint(outbox["api"], t["id"], "http://127.0.0.1:1/x", max_attempts=1)
    ev, _ = enqueue(outbox["api"], ep["id"], {"n": 1})
    _force_dlq(outbox["api"], ev["id"])
    before = outbox["api"]("GET", f"/api/v1/events/{ev['id']}").json()
    assert before["status"] == "dlq"
    pret_attempts = before["attempt_count"]
    t0 = time.time()
    r = outbox["api"](
        "POST",
        f"/api/v1/events/{ev['id']}/replay",
        headers={"Authorization": f"Bearer {outbox['token']}"},
    )
    t1 = time.time()
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "pending"
    assert body["attempt_count"] == pret_attempts
    assert body["lease_owner"] is None
    assert body["lease_until"] is None
    nxt = _parse_rfc3339(body["next_attempt_at"])
    assert t0 - 2.0 <= nxt <= t1 + 2.0
    aud = outbox["api"]("GET", "/api/v1/audit?limit=100")
    assert "replay" in [e["action"] for e in aud.json()["events"]]


def test_f2p_resume_allows_claim_again(outbox):
    """After resume, claims succeed and a resume audit action is recorded."""
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
    actions = [
        e["action"]
        for e in outbox["api"]("GET", "/api/v1/audit?limit=50").json()["events"]
    ]
    assert "resume" in actions


def test_p2p_ui_index_served(outbox):
    """Static UI index is served from /."""
    r = outbox["api"]("GET", "/")
    assert r.status_code == 200
    assert "Outbox Delivery Plane" in r.text
    assert 'id="error-box"' in r.text


def test_f2p_ui_claim_fields_and_error_box(outbox):
    """Claim helper POSTs lease_owner/lease_seconds; API errors write #error-box textContent."""
    js = (APP / "ui" / "js" / "app.js").read_text(encoding="utf-8")
    claim_m = re.search(
        r"async claim\s*\([^)]*\)\s*\{([\s\S]*?)\n\s*\},?\s*\n\s*async ",
        js,
    )
    assert claim_m, "could not locate outboxUI.claim implementation"
    claim_body = claim_m.group(1)
    assert re.search(r"\blease_owner\s*:", claim_body), claim_body
    assert re.search(r"\blease_seconds\s*:", claim_body), claim_body
    assert not re.search(r"\{\s*owner\s*:", claim_body), claim_body
    assert not re.search(r"(?<!lease_)seconds\s*:", claim_body), claim_body

    api_m = re.search(r"async function api\s*\([^)]*\)\s*\{([\s\S]*?)\n  \}", js)
    assert api_m, "could not locate api() helper"
    api_body = api_m.group(1)
    assert "error-box" in api_body or "errBox" in api_body or "showError" in js
    assert "textContent" in js
    assert re.search(r"!res\.ok|res\.ok\s*===?\s*false", api_body)
    assert "data.error" in api_body or "data && data.error" in api_body


def test_p2p_schema_file_present(outbox):
    """Schema SQL used on boot is present under the product tree."""
    schema = APP / "db" / "schema.sql"
    assert schema.is_file()
    text = schema.read_text(encoding="utf-8")
    assert "CREATE TABLE" in text and "delivery_attempts" in text
