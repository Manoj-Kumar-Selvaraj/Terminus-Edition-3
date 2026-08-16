"""Claim fencing, pause, delivery signatures, and backoff/DLQ tests."""

from __future__ import annotations

from conftest import create_endpoint, create_tenant, enqueue, expect_signature


def test_f2p_claim_sets_lease_owner(outbox):
    """Successful claim moves event to claimed and records lease_owner."""
    t = create_tenant(outbox["api"], "claim1")
    ep = create_endpoint(outbox["api"], t["id"], outbox["sink"]["url"])
    ev, _ = enqueue(outbox["api"], ep["id"], {"v": 1})
    r = outbox["api"](
        "POST",
        f"/api/v1/events/{ev['id']}/claim",
        json={"lease_owner": "worker-a", "lease_seconds": 60},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "claimed"
    assert body["lease_owner"] == "worker-a"
    assert body["lease_until"] is not None


def test_f2p_second_claim_different_owner_conflict(outbox):
    """A non-expired lease held by another owner returns 409 lease_held."""
    t = create_tenant(outbox["api"], "claim2")
    ep = create_endpoint(outbox["api"], t["id"], outbox["sink"]["url"])
    ev, _ = enqueue(outbox["api"], ep["id"], {"v": 1})
    r1 = outbox["api"](
        "POST",
        f"/api/v1/events/{ev['id']}/claim",
        json={"lease_owner": "worker-a", "lease_seconds": 120},
    )
    assert r1.status_code == 200
    r2 = outbox["api"](
        "POST",
        f"/api/v1/events/{ev['id']}/claim",
        json={"lease_owner": "worker-b", "lease_seconds": 120},
    )
    assert r2.status_code == 409
    assert r2.json()["error"] == "lease_held"


def test_f2p_same_owner_can_renew_lease(outbox):
    """The current lease holder may renew before expiry."""
    t = create_tenant(outbox["api"], "claim3")
    ep = create_endpoint(outbox["api"], t["id"], outbox["sink"]["url"])
    ev, _ = enqueue(outbox["api"], ep["id"], {"v": 1})
    outbox["api"](
        "POST",
        f"/api/v1/events/{ev['id']}/claim",
        json={"lease_owner": "worker-a", "lease_seconds": 30},
    )
    r = outbox["api"](
        "POST",
        f"/api/v1/events/{ev['id']}/claim",
        json={"lease_owner": "worker-a", "lease_seconds": 90},
    )
    assert r.status_code == 200
    assert r.json()["lease_owner"] == "worker-a"


def test_f2p_paused_endpoint_rejects_claim(outbox):
    """Paused endpoints reject new claims with endpoint_unavailable."""
    t = create_tenant(outbox["api"], "pause1")
    ep = create_endpoint(outbox["api"], t["id"], outbox["sink"]["url"])
    ev, _ = enqueue(outbox["api"], ep["id"], {"v": 1})
    pr = outbox["api"]("POST", f"/api/v1/endpoints/{ep['id']}/pause")
    assert pr.status_code == 200
    assert pr.json()["paused"] is True
    r = outbox["api"](
        "POST",
        f"/api/v1/events/{ev['id']}/claim",
        json={"lease_owner": "worker-a", "lease_seconds": 30},
    )
    assert r.status_code == 409
    assert r.json()["error"] == "endpoint_unavailable"


def test_f2p_complete_and_deliver_require_lease_holder(outbox):
    """Complete and deliver from a non-holder return lease_mismatch."""
    t = create_tenant(outbox["api"], "lease1")
    ep = create_endpoint(outbox["api"], t["id"], outbox["sink"]["url"])
    ev, _ = enqueue(outbox["api"], ep["id"], {"v": 1})
    outbox["api"](
        "POST",
        f"/api/v1/events/{ev['id']}/claim",
        json={"lease_owner": "worker-a", "lease_seconds": 60},
    )
    r = outbox["api"](
        "POST",
        f"/api/v1/events/{ev['id']}/complete",
        json={"lease_owner": "other", "outcome": "delivered", "http_status": 200},
    )
    assert r.status_code == 409
    assert r.json()["error"] == "lease_mismatch"
    d = outbox["api"](
        "POST",
        f"/api/v1/events/{ev['id']}/deliver",
        json={"lease_owner": "other"},
    )
    assert d.status_code == 409
    assert d.json()["error"] == "lease_mismatch"
    assert outbox["api"]("GET", f"/api/v1/events/{ev['id']}").json()["status"] == "claimed"


def test_f2p_deliver_posts_signed_headers(outbox):
    """Deliver POSTs with HMAC headers, application/json, and compact sorted-key body."""
    secret = "sig-secret-9"
    t = create_tenant(outbox["api"], "sig1")
    ep = create_endpoint(outbox["api"], t["id"], outbox["sink"]["url"], secret=secret)
    ev, _ = enqueue(outbox["api"], ep["id"], {"z": 2, "a": 1})
    outbox["api"](
        "POST",
        f"/api/v1/events/{ev['id']}/claim",
        json={"lease_owner": "worker-a", "lease_seconds": 60},
    )
    r = outbox["api"](
        "POST",
        f"/api/v1/events/{ev['id']}/deliver",
        json={"lease_owner": "worker-a"},
    )
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "delivered"
    assert len(outbox["sink"]["captures"]) >= 1
    cap = outbox["sink"]["captures"][-1]
    hdrs = {k.lower(): v for k, v in cap["headers"].items()}
    assert hdrs["x-outbox-id"] == ev["id"]
    assert "x-outbox-timestamp" in hdrs
    assert "x-outbox-signature" in hdrs
    assert hdrs.get("content-type", "").startswith("application/json")
    assert cap["body"] == b'{"a":1,"z":2}'
    expect = expect_signature(secret, ev["id"], hdrs["x-outbox-timestamp"], cap["body"])
    assert hdrs["x-outbox-signature"] == expect


def test_f2p_failed_delivery_retries_then_dlq(outbox):
    """Backoff follows 5s then 15s; exhausted max_attempts lands in dlq."""
    from datetime import datetime, timezone
    import time as time_mod

    def parse_ts(raw: str) -> float:
        if raw.endswith("Z"):
            raw = raw[:-1] + "+00:00"
        return datetime.fromisoformat(raw).astimezone(timezone.utc).timestamp()

    t = create_tenant(outbox["api"], "dlq1")
    ep = create_endpoint(
        outbox["api"], t["id"], "http://127.0.0.1:1/nope", max_attempts=3
    )
    ev, _ = enqueue(outbox["api"], ep["id"], {"x": 1})

    before1 = time_mod.time()
    outbox["api"](
        "POST",
        f"/api/v1/events/{ev['id']}/claim",
        json={"lease_owner": "w0", "lease_seconds": 30},
    )
    outbox["api"](
        "POST",
        f"/api/v1/events/{ev['id']}/deliver",
        json={"lease_owner": "w0"},
    )
    after1 = time_mod.time()
    mid1 = outbox["api"]("GET", f"/api/v1/events/{ev['id']}").json()
    assert mid1["status"] == "pending"
    assert mid1["attempt_count"] == 1
    assert mid1["lease_owner"] is None
    nxt1 = parse_ts(mid1["next_attempt_at"])
    assert before1 + 4.0 <= nxt1 <= after1 + 7.0

    before2 = time_mod.time()
    outbox["api"](
        "POST",
        f"/api/v1/events/{ev['id']}/claim",
        json={"lease_owner": "w1", "lease_seconds": 30},
    )
    outbox["api"](
        "POST",
        f"/api/v1/events/{ev['id']}/deliver",
        json={"lease_owner": "w1"},
    )
    after2 = time_mod.time()
    mid2 = outbox["api"]("GET", f"/api/v1/events/{ev['id']}").json()
    assert mid2["status"] == "pending"
    assert mid2["attempt_count"] == 2
    nxt2 = parse_ts(mid2["next_attempt_at"])
    assert before2 + 13.0 <= nxt2 <= after2 + 18.0

    outbox["api"](
        "POST",
        f"/api/v1/events/{ev['id']}/claim",
        json={"lease_owner": "w2", "lease_seconds": 30},
    )
    outbox["api"](
        "POST",
        f"/api/v1/events/{ev['id']}/deliver",
        json={"lease_owner": "w2"},
    )
    got = outbox["api"]("GET", f"/api/v1/events/{ev['id']}")
    assert got.status_code == 200
    assert got.json()["status"] == "dlq"
    assert got.json()["attempt_count"] == 3

    actions = [
        e["action"]
        for e in outbox["api"]("GET", "/api/v1/audit?limit=100").json()["events"]
    ]
    assert "deliver.fail" in actions
    assert "dlq" in actions


def test_f2p_attempts_list_records_outcomes(outbox):
    """Attempt history lists each delivery outcome for an event."""
    t = create_tenant(outbox["api"], "att1")
    ep = create_endpoint(outbox["api"], t["id"], outbox["sink"]["url"])
    ev, _ = enqueue(outbox["api"], ep["id"], {"x": 1})
    outbox["api"](
        "POST",
        f"/api/v1/events/{ev['id']}/claim",
        json={"lease_owner": "worker-a", "lease_seconds": 30},
    )
    outbox["api"](
        "POST",
        f"/api/v1/events/{ev['id']}/deliver",
        json={"lease_owner": "worker-a"},
    )
    r = outbox["api"]("GET", f"/api/v1/events/{ev['id']}/attempts")
    assert r.status_code == 200
    attempts = r.json()["attempts"]
    assert len(attempts) >= 1
    assert attempts[-1]["outcome"] == "delivered"
