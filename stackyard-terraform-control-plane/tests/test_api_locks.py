"""Lock fencing, unlock holder checks, and workspace delete guards."""

from __future__ import annotations


def test_lock_and_get(stackyard, workspace):
    """Locking a workspace stores holder metadata and marks locked=true."""
    api = stackyard["api"]
    r = api(
        "POST",
        f"/api/v1/workspaces/{workspace['id']}/lock",
        json={"holder": "alice", "reason": "cutover"},
    )
    assert r.status_code == 201
    body = r.json()
    assert body["holder"] == "alice"
    assert body["id"].startswith("lock_")
    ws = api("GET", f"/api/v1/workspaces/{workspace['id']}").json()
    assert ws["locked"] is True
    assert ws["lock_id"] == body["id"]


def test_double_lock_rejected(stackyard, workspace):
    """A second lock while held returns already locked."""
    api = stackyard["api"]
    assert (
        api(
            "POST",
            f"/api/v1/workspaces/{workspace['id']}/lock",
            json={"holder": "alice", "reason": "a"},
        ).status_code
        == 201
    )
    r = api(
        "POST",
        f"/api/v1/workspaces/{workspace['id']}/lock",
        json={"holder": "bob", "reason": "b"},
    )
    assert r.status_code == 409
    assert r.json()["error"] == "already locked"


def test_unlock_wrong_holder_forbidden(stackyard, workspace):
    """Unlock by a non-holder is rejected with not lock holder."""
    api = stackyard["api"]
    api(
        "POST",
        f"/api/v1/workspaces/{workspace['id']}/lock",
        json={"holder": "alice", "reason": "a"},
    )
    r = api(
        "POST",
        f"/api/v1/workspaces/{workspace['id']}/unlock",
        json={"holder": "bob"},
    )
    assert r.status_code == 403
    assert r.json()["error"] == "not lock holder"
    ws = api("GET", f"/api/v1/workspaces/{workspace['id']}").json()
    assert ws["locked"] is True


def test_unlock_by_holder(stackyard, workspace):
    """Matching holder can unlock and clears locked state."""
    api = stackyard["api"]
    api(
        "POST",
        f"/api/v1/workspaces/{workspace['id']}/lock",
        json={"holder": "alice", "reason": "a"},
    )
    r = api(
        "POST",
        f"/api/v1/workspaces/{workspace['id']}/unlock",
        json={"holder": "alice"},
    )
    assert r.status_code == 204
    ws = api("GET", f"/api/v1/workspaces/{workspace['id']}").json()
    assert ws["locked"] is False


def test_lock_audit_events(stackyard, workspace):
    """Lock acquire and release write lock.acquire / lock.release audits."""
    api = stackyard["api"]
    api(
        "POST",
        f"/api/v1/workspaces/{workspace['id']}/lock",
        json={"holder": "carol", "reason": "r"},
    )
    api(
        "POST",
        f"/api/v1/workspaces/{workspace['id']}/unlock",
        json={"holder": "carol"},
    )
    events = api("GET", f"/api/v1/workspaces/{workspace['id']}/audit").json()["events"]
    actions = {e["action"]: e["detail"] for e in events}
    assert actions.get("lock.acquire") == "carol"
    assert actions.get("lock.release") == "carol"


def test_delete_blocked_when_locked(stackyard, workspace):
    """Workspace delete fails while an exclusive lock is held."""
    api = stackyard["api"]
    api(
        "POST",
        f"/api/v1/workspaces/{workspace['id']}/lock",
        json={"holder": "alice", "reason": "hold"},
    )
    r = api("DELETE", f"/api/v1/workspaces/{workspace['id']}")
    assert r.status_code == 409


def test_delete_blocked_with_active_run(stackyard, workspace):
    """Workspace delete fails while a non-terminal run exists."""
    api = stackyard["api"]
    created = api(
        "POST",
        f"/api/v1/workspaces/{workspace['id']}/runs",
        json={"command": "plan", "message": "hold"},
    )
    assert created.status_code == 201
    assert created.json()["status"] == "planned"
    r = api("DELETE", f"/api/v1/workspaces/{workspace['id']}")
    assert r.status_code == 409
