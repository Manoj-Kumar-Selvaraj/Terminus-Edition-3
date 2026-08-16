"""Contract edge F2P: CLI smoke, quota-on-deliver, disabled claim + lease expiry."""

from __future__ import annotations

import json
import os
import sqlite3
import subprocess
import time
from pathlib import Path

from conftest import APP, create_endpoint, create_tenant, enqueue


def test_f2p_cli_health_and_enqueue_claim(outbox, built_ctl: Path):
    """outboxctl health and enqueue/claim talk to the live OUTBOX_ADDR API."""
    assert built_ctl.is_file()
    env = os.environ.copy()
    addr = outbox["base"].removeprefix("http://")
    env["OUTBOX_ADDR"] = addr
    env["OUTBOX_TOKEN"] = outbox["token"]

    health = subprocess.run(
        [str(built_ctl), "health"],
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )
    assert health.returncode == 0, health.stderr + health.stdout
    assert '"status"' in health.stdout and "ok" in health.stdout

    t = create_tenant(outbox["api"], "cli1")
    ep = create_endpoint(outbox["api"], t["id"], outbox["sink"]["url"])
    enq = subprocess.run(
        [
            str(built_ctl),
            "enqueue",
            "--endpoint",
            ep["id"],
            "--payload",
            '{"cli":true}',
        ],
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )
    assert enq.returncode == 0, enq.stderr + enq.stdout
    ev = json.loads(enq.stdout.strip().splitlines()[-1])
    assert ev["id"].startswith("evt_")

    claim = subprocess.run(
        [
            str(built_ctl),
            "claim",
            "--event",
            ev["id"],
            "--owner",
            "cli-worker",
            "--seconds",
            "30",
        ],
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )
    assert claim.returncode == 0, claim.stderr + claim.stdout
    claimed = json.loads(claim.stdout.strip().splitlines()[-1])
    assert claimed["lease_owner"] == "cli-worker"


def test_p2p_seed_catalog_artifacts_present():
    """Image seed DB, seed binary, and seed script remain under /app/outbox."""
    seed_db = APP / "data" / "outbox.db"
    seed_bin = APP / "bin" / "seed"
    seed_sh = APP / "scripts" / "seed.sh"
    assert seed_db.is_file(), f"missing seeded database {seed_db}"
    assert seed_sh.is_file(), f"missing seed script {seed_sh}"
    assert seed_bin.is_file() or (APP / "cmd" / "seed" / "main.go").is_file()
    conn = sqlite3.connect(str(seed_db))
    try:
        tenants = conn.execute("SELECT COUNT(*) FROM tenants").fetchone()[0]
        endpoints = conn.execute("SELECT COUNT(*) FROM endpoints").fetchone()[0]
        events = conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]
    finally:
        conn.close()
    assert tenants >= 6
    assert endpoints >= 18
    assert events >= 100


def test_f2p_quota_blocks_deliver_and_complete_when_full(outbox):
    """When the hour window is full, deliver and complete-as-delivered return 429."""
    t = create_tenant(outbox["api"], "qdel1", quota=1)
    ep = create_endpoint(outbox["api"], t["id"], outbox["sink"]["url"])
    ev_a, _ = enqueue(outbox["api"], ep["id"], {"n": 1})
    ev_b, _ = enqueue(outbox["api"], ep["id"], {"n": 2})
    ev_c, _ = enqueue(outbox["api"], ep["id"], {"n": 3})
    outbox["api"](
        "POST",
        f"/api/v1/events/{ev_a['id']}/claim",
        json={"lease_owner": "w1", "lease_seconds": 30},
    )
    d1 = outbox["api"](
        "POST",
        f"/api/v1/events/{ev_a['id']}/deliver",
        json={"lease_owner": "w1"},
    )
    assert d1.status_code == 200

    outbox["api"](
        "POST",
        f"/api/v1/events/{ev_b['id']}/claim",
        json={"lease_owner": "w2", "lease_seconds": 30},
    )
    d2 = outbox["api"](
        "POST",
        f"/api/v1/events/{ev_b['id']}/deliver",
        json={"lease_owner": "w2"},
    )
    assert d2.status_code == 429, d2.text
    assert d2.json()["error"] == "quota_exceeded"
    assert outbox["api"]("GET", f"/api/v1/events/{ev_b['id']}").json()["status"] != "delivered"

    outbox["api"](
        "POST",
        f"/api/v1/events/{ev_c['id']}/claim",
        json={"lease_owner": "w3", "lease_seconds": 30},
    )
    r = outbox["api"](
        "POST",
        f"/api/v1/events/{ev_c['id']}/complete",
        json={
            "lease_owner": "w3",
            "outcome": "delivered",
            "http_status": 200,
            "error": "",
        },
    )
    assert r.status_code == 429
    assert r.json()["error"] == "quota_exceeded"
    assert outbox["api"]("GET", f"/api/v1/events/{ev_c['id']}").json()["status"] != "delivered"


def test_f2p_disabled_claim_and_expired_lease_reclaim(outbox):
    """Disabled endpoints reject claim; after lease expiry another owner can reclaim."""
    t = create_tenant(outbox["api"], "fence1")
    ep = create_endpoint(outbox["api"], t["id"], outbox["sink"]["url"])
    ev_dis, _ = enqueue(outbox["api"], ep["id"], {"v": 1})
    pr = outbox["api"](
        "PATCH", f"/api/v1/endpoints/{ep['id']}", json={"enabled": False}
    )
    assert pr.status_code == 200
    r = outbox["api"](
        "POST",
        f"/api/v1/events/{ev_dis['id']}/claim",
        json={"lease_owner": "worker-a", "lease_seconds": 30},
    )
    assert r.status_code == 409
    assert r.json()["error"] == "endpoint_unavailable"

    outbox["api"]("PATCH", f"/api/v1/endpoints/{ep['id']}", json={"enabled": True})
    ev, _ = enqueue(outbox["api"], ep["id"], {"v": 2})
    r1 = outbox["api"](
        "POST",
        f"/api/v1/events/{ev['id']}/claim",
        json={"lease_owner": "worker-a", "lease_seconds": 1},
    )
    assert r1.status_code == 200
    time.sleep(1.5)
    r2 = outbox["api"](
        "POST",
        f"/api/v1/events/{ev['id']}/claim",
        json={"lease_owner": "worker-b", "lease_seconds": 30},
    )
    assert r2.status_code == 200, r2.text
    assert r2.json()["lease_owner"] == "worker-b"
