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


def test_f2p_complete_requires_lease_holder(outbox):
    """Complete from a non-holder returns lease_mismatch."""
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


def test_f2p_deliver_posts_signed_headers(outbox):
    """Deliver POSTs to the endpoint with contract HMAC headers and body."""
    secret = "sig-secret-9"
    t = create_tenant(outbox["api"], "sig1")
    ep = create_endpoint(outbox["api"], t["id"], outbox["sink"]["url"], secret=secret)
    ev, _ = enqueue(outbox["api"], ep["id"], {"hello": "world"})
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
    expect = expect_signature(secret, ev["id"], hdrs["x-outbox-timestamp"], cap["body"])
    assert hdrs["x-outbox-signature"] == expect


def test_f2p_failed_delivery_retries_then_dlq(outbox):
    """Exhausted max_attempts after failures lands the event in dlq."""
    t = create_tenant(outbox["api"], "dlq1")
    # Point at a closed port so deliver fails.
    ep = create_endpoint(
        outbox["api"], t["id"], "http://127.0.0.1:1/nope", max_attempts=2
    )
    ev, _ = enqueue(outbox["api"], ep["id"], {"x": 1})
    for i in range(2):
        outbox["api"](
            "POST",
            f"/api/v1/events/{ev['id']}/claim",
            json={"lease_owner": f"w{i}", "lease_seconds": 30},
        )
        outbox["api"](
            "POST",
            f"/api/v1/events/{ev['id']}/deliver",
            json={"lease_owner": f"w{i}"},
        )
    got = outbox["api"]("GET", f"/api/v1/events/{ev['id']}")
    assert got.status_code == 200
    assert got.json()["status"] == "dlq"
    assert got.json()["attempt_count"] == 2


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
