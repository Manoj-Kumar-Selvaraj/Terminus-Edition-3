"""Wiki probe split and durable creation-counter reconcile after DB flap."""

from __future__ import annotations

import json
import os
import sqlite3
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path

import pytest

ROOT = Path(os.environ.get("WIKI_ROOT", "/app/wiki"))
DB = Path(os.environ.get("WIKI_DB", str(ROOT / "var" / "wiki.db")))
CTL = ROOT / "bin" / "wikictl"
OUT = ROOT / "out"


def _ctl(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(CTL), *args],
        check=True,
        capture_output=True,
        text=True,
        env={**os.environ, "WIKI_ROOT": str(ROOT), "WIKI_DB": str(DB)},
    )


def _get(url: str) -> tuple[int, str]:
    try:
        with urllib.request.urlopen(url, timeout=4) as resp:
            return resp.status, resp.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8")


def _metric(body: str, name: str) -> float:
    total = 0.0
    for line in body.splitlines():
        if line.startswith(name + " ") or line.startswith(name + "{"):
            total += float(line.rsplit(" ", 1)[-1])
    return total


@pytest.fixture(scope="module")
def served() -> None:
    assert CTL.is_file(), "wikictl missing"
    _ctl("seed")
    _ctl("stop")
    _ctl("serve")
    deadline = time.time() + 15
    while time.time() < deadline:
        code, _ = _get("http://127.0.0.1:8001/health/startup")
        if code == 200:
            yield
            _ctl("stop")
            return
        time.sleep(0.2)
    raise AssertionError("replicas did not start")


def test_live_stays_up_during_flap(served: None) -> None:
    """Liveness must remain 200 while the database file is absent."""
    _ctl("flap")
    try:
        for port in (8001, 8002):
            code, body = _get(f"http://127.0.0.1:{port}/health/live")
            assert code == 200
            assert json.loads(body)["status"] == "alive"
    finally:
        _ctl("restore")


def test_ready_503_during_flap_and_200_after_restore(served: None) -> None:
    """Readiness follows the database file without a process restart."""
    _ctl("flap")
    try:
        for port in (8001, 8002):
            code, _ = _get(f"http://127.0.0.1:{port}/health/ready")
            assert code == 503
    finally:
        _ctl("restore")
    for port in (8001, 8002):
        code, body = _get(f"http://127.0.0.1:{port}/health/ready")
        assert code == 200
        assert json.loads(body)["status"] == "ready"


def test_metrics_match_table_counts_after_restore(served: None) -> None:
    """Creation gauges must equal durable COUNT(*) after the file returns."""
    _ctl("flap")
    _ctl("restore")
    con = sqlite3.connect(str(DB))
    users = int(con.execute("SELECT COUNT(*) FROM users").fetchone()[0])
    posts = int(con.execute("SELECT COUNT(*) FROM posts").fetchone()[0])
    con.close()
    assert users >= 4000
    assert posts >= 6000
    for port in (8001, 8002):
        code, body = _get(f"http://127.0.0.1:{port}/metrics")
        assert code == 200
        assert _metric(body, "users_created_total") == users
        assert _metric(body, "posts_created_total") == posts


def test_missing_author_is_404(served: None) -> None:
    """POST /posts with an unknown user_id is 404, not a 5xx or 400."""
    req = urllib.request.Request(
        "http://127.0.0.1:8001/posts",
        data=json.dumps({"user_id": 999999, "content": "orphan"}).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        urllib.request.urlopen(req, timeout=4)
        raise AssertionError("expected 404")
    except urllib.error.HTTPError as exc:
        assert exc.code == 404
        detail = json.loads(exc.read().decode())
        assert detail["detail"] == "User not found"


def test_create_post_uses_post_id(served: None) -> None:
    """Successful post creation exposes post_id, not a colliding id field."""
    req = urllib.request.Request(
        "http://127.0.0.1:8001/posts",
        data=json.dumps({"user_id": 1, "content": "slo-check"}).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=4) as resp:
        payload = json.loads(resp.read().decode())
    assert "post_id" in payload
    assert "id" not in payload
    assert payload["user_id"] == 1


def test_probe_and_reconcile_reports(served: None) -> None:
    """wikictl report writes both required JSON objects after restore."""
    _ctl("restore")
    _ctl("report")
    probe = json.loads((OUT / "probe-matrix.json").read_text(encoding="utf-8"))
    recon = json.loads((OUT / "creation-reconcile.json").read_text(encoding="utf-8"))
    assert probe["live_8001"] == "alive"
    assert probe["live_8002"] == "alive"
    assert probe["ready_8001"] == "ready"
    assert probe["ready_8002"] == "ready"
    assert probe["db_present"] is True
    assert recon["reconciled"] is True
    assert recon["users_table"] == recon["users_metric"]
    assert recon["posts_table"] == recon["posts_metric"]
    assert recon["scrape_targets"] == ["127.0.0.1:8001", "127.0.0.1:8002"]


def test_probe_matrix_during_flap(served: None) -> None:
    """Hidden variation: report during flap marks ready not_ready and db absent."""
    _ctl("flap")
    try:
        _ctl("report")
        probe = json.loads((OUT / "probe-matrix.json").read_text(encoding="utf-8"))
        assert probe["db_present"] is False
        assert probe["live_8001"] == "alive"
        assert probe["ready_8001"] == "not_ready"
        assert probe["ready_8002"] == "not_ready"
    finally:
        _ctl("restore")


def test_p2p_public_tree_remains() -> None:
    """Contract, incident log, and wikictl stay on the submitted tree."""
    assert (ROOT / "docs" / "creation-slo.md").is_file()
    assert (ROOT / "ops" / "handoff.md").is_file()
    assert (ROOT / "log" / "grafana-flap.log").is_file()
    assert CTL.is_file()
