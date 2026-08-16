"""Run lifecycle, concurrency, destroy mapping, and transition tests."""

from __future__ import annotations

from pathlib import Path

from conftest import read_text


def _lock(api, ws_id: str, holder: str = "alice") -> None:
    r = api("POST", f"/api/v1/workspaces/{ws_id}/lock", json={"holder": holder, "reason": "apply"})
    assert r.status_code == 201, r.text


def test_plan_run_reaches_planned(stackyard, workspace):
    """A plan run executes through the shim and lands in planned status."""
    api = stackyard["api"]
    r = api(
        "POST",
        f"/api/v1/workspaces/{workspace['id']}/runs",
        json={"command": "plan", "message": "demo"},
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["status"] == "planned"
    assert "shim" in body["plan_output"].lower() or body["plan_output"] != ""
    log = read_text(Path(stackyard["shim_log"]))
    assert " plan " in log or "plan -input=false" in log


def test_reject_second_nonterminal_run(stackyard, workspace):
    """Only one non-terminal run is allowed per workspace at a time."""
    api = stackyard["api"]
    # Force a non-terminal run by creating plan then... plan completes to planned
    # which is still non-terminal. Second create must 409.
    r1 = api(
        "POST",
        f"/api/v1/workspaces/{workspace['id']}/runs",
        json={"command": "plan", "message": "one"},
    )
    assert r1.status_code == 201
    assert r1.json()["status"] == "planned"
    r2 = api(
        "POST",
        f"/api/v1/workspaces/{workspace['id']}/runs",
        json={"command": "plan", "message": "two"},
    )
    assert r2.status_code == 409
    assert r2.json()["error"] == "workspace has active run"


def test_apply_requires_lock(stackyard, workspace):
    """Apply without an exclusive lock is rejected with lock required."""
    api = stackyard["api"]
    r = api(
        "POST",
        f"/api/v1/workspaces/{workspace['id']}/runs",
        json={"command": "apply", "message": "no-lock"},
    )
    assert r.status_code == 409
    assert r.json()["error"] == "lock required"


def test_destroy_requires_lock(stackyard, workspace):
    """Destroy without a lock is rejected the same way as apply."""
    api = stackyard["api"]
    r = api(
        "POST",
        f"/api/v1/workspaces/{workspace['id']}/runs",
        json={"command": "destroy", "message": "no-lock"},
    )
    assert r.status_code == 409
    assert r.json()["error"] == "lock required"


def test_apply_with_lock_succeeds(stackyard, workspace):
    """Apply succeeds when the workspace holds a lock and reaches applied."""
    api = stackyard["api"]
    _lock(api, workspace["id"])
    r = api(
        "POST",
        f"/api/v1/workspaces/{workspace['id']}/runs",
        json={"command": "apply", "message": "go"},
    )
    assert r.status_code == 201, r.text
    assert r.json()["status"] == "applied"
    assert r.json()["apply_output"] != ""


def test_destroy_maps_to_apply_destroy(stackyard, workspace):
    """Destroy runs invoke terraform apply -destroy via the shim argv log."""
    api = stackyard["api"]
    _lock(api, workspace["id"])
    r = api(
        "POST",
        f"/api/v1/workspaces/{workspace['id']}/runs",
        json={"command": "destroy", "message": "teardown"},
    )
    assert r.status_code == 201, r.text
    assert r.json()["status"] == "applied"
    log = read_text(Path(stackyard["shim_log"]))
    assert "apply" in log
    assert "-destroy" in log
    assert " destroy " not in log.replace("apply -destroy", "APPLY_DESTROY")


def test_discard_from_planned(stackyard, workspace):
    """Discard is allowed from planned and yields discarded."""
    api = stackyard["api"]
    created = api(
        "POST",
        f"/api/v1/workspaces/{workspace['id']}/runs",
        json={"command": "plan", "message": "d"},
    ).json()
    r = api("POST", f"/api/v1/runs/{created['id']}/discard", json={})
    assert r.status_code == 200
    assert r.json()["status"] == "discarded"


def test_discard_from_applied_rejected(stackyard, workspace):
    """Discard from applied is an invalid transition."""
    api = stackyard["api"]
    _lock(api, workspace["id"])
    created = api(
        "POST",
        f"/api/v1/workspaces/{workspace['id']}/runs",
        json={"command": "apply", "message": "a"},
    ).json()
    assert created["status"] == "applied"
    r = api("POST", f"/api/v1/runs/{created['id']}/discard", json={})
    assert r.status_code == 409
    assert r.json()["error"] == "invalid transition"


def test_cancel_from_planned_rejected(stackyard, workspace):
    """Cancel is not allowed once a run has reached planned."""
    api = stackyard["api"]
    created = api(
        "POST",
        f"/api/v1/workspaces/{workspace['id']}/runs",
        json={"command": "plan", "message": "c"},
    ).json()
    r = api("POST", f"/api/v1/runs/{created['id']}/cancel", json={})
    assert r.status_code == 409
    assert r.json()["error"] == "invalid transition"


def test_init_validate_fmt_commands(stackyard, workspace):
    """Init, validate, and fmt commands complete as planned successes."""
    api = stackyard["api"]
    for cmd in ("init", "validate", "fmt"):
        # discard previous planned run if any
        runs = api("GET", f"/api/v1/workspaces/{workspace['id']}/runs").json()["runs"]
        for run in runs:
            if run["status"] == "planned":
                api("POST", f"/api/v1/runs/{run['id']}/discard", json={})
        r = api(
            "POST",
            f"/api/v1/workspaces/{workspace['id']}/runs",
            json={"command": cmd, "message": cmd},
        )
        assert r.status_code == 201, (cmd, r.text)
        assert r.json()["status"] == "planned"
        api("POST", f"/api/v1/runs/{r.json()['id']}/discard", json={})


def test_run_created_and_status_audit(stackyard, workspace):
    """Run create and status transitions emit required audit actions."""
    api = stackyard["api"]
    created = api(
        "POST",
        f"/api/v1/workspaces/{workspace['id']}/runs",
        json={"command": "plan", "message": "aud"},
    ).json()
    events = api("GET", f"/api/v1/workspaces/{workspace['id']}/audit").json()["events"]
    actions = [e["action"] for e in events]
    assert "run.created" in actions
    assert "run.status" in actions
    details = [e["detail"] for e in events if e["action"] == "run.status"]
    assert any("queued->running" in d for d in details)
    assert any("running->planned" in d for d in details)
    assert created["command"] == "plan"
