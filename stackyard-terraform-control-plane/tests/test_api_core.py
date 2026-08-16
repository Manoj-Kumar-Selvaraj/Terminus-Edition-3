"""Core org/workspace/health contract tests."""

from __future__ import annotations


def test_health_ok(stackyard):
    """Health endpoint reports status ok for a live control plane."""
    r = stackyard["api"]("GET", "/api/v1/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_default_org_acme_seeded(acme_org):
    """First boot seeds organization slug acme with matching name."""
    assert acme_org["name"] == "acme"
    assert acme_org["slug"] == "acme"
    assert acme_org["id"].startswith("org_")


def test_create_and_get_workspace(stackyard, workspace):
    """Workspace create returns contract fields and is fetchable by id."""
    assert workspace["id"].startswith("ws_")
    assert workspace["working_directory"] == "infra"
    assert workspace["locked"] is False
    r = stackyard["api"]("GET", f"/api/v1/workspaces/{workspace['id']}")
    assert r.status_code == 200
    assert r.json()["name"] == workspace["name"]


def test_list_workspaces_under_org(stackyard, acme_org, workspace):
    """Org workspace listing includes the newly created workspace."""
    r = stackyard["api"]("GET", f"/api/v1/orgs/{acme_org['id']}/workspaces")
    assert r.status_code == 200
    ids = {w["id"] for w in r.json()["workspaces"]}
    assert workspace["id"] in ids


def test_create_org(stackyard):
    """Operators can create additional organizations with unique slugs."""
    r = stackyard["api"](
        "POST",
        "/api/v1/orgs",
        json={"name": "Globex", "slug": "globex"},
    )
    assert r.status_code == 201
    body = r.json()
    assert body["slug"] == "globex"
    assert body["id"].startswith("org_")


def test_delete_workspace_when_idle(stackyard, workspace):
    """Idle unlocked workspaces can be deleted with HTTP 204."""
    r = stackyard["api"]("DELETE", f"/api/v1/workspaces/{workspace['id']}")
    assert r.status_code == 204
    r2 = stackyard["api"]("GET", f"/api/v1/workspaces/{workspace['id']}")
    assert r2.status_code == 404
