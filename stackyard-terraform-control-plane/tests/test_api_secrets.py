"""Sensitive variable redaction and TF_VAR / env injection tests."""

from __future__ import annotations

from pathlib import Path

from conftest import read_text


def test_sensitive_create_redacts_value(stackyard, workspace):
    """Create responses for sensitive vars must null the value field."""
    api = stackyard["api"]
    r = api(
        "POST",
        f"/api/v1/workspaces/{workspace['id']}/vars",
        json={
            "key": "db_password",
            "value": "s3cret-value",
            "sensitive": True,
            "category": "terraform",
        },
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["sensitive"] is True
    assert body["value"] is None


def test_sensitive_get_and_list_redact(stackyard, workspace):
    """GET and list endpoints never return plaintext for sensitive vars."""
    api = stackyard["api"]
    created = api(
        "POST",
        f"/api/v1/workspaces/{workspace['id']}/vars",
        json={
            "key": "api_token",
            "value": "tok-plain",
            "sensitive": True,
            "category": "terraform",
        },
    ).json()
    got = api("GET", f"/api/v1/vars/{created['id']}").json()
    assert got["value"] is None
    listed = api("GET", f"/api/v1/workspaces/{workspace['id']}/vars").json()["vars"]
    match = next(v for v in listed if v["id"] == created["id"])
    assert match["value"] is None


def test_nonsensitive_value_returned(stackyard, workspace):
    """Non-sensitive terraform vars still return their value in API responses."""
    api = stackyard["api"]
    r = api(
        "POST",
        f"/api/v1/workspaces/{workspace['id']}/vars",
        json={
            "key": "region",
            "value": "us-east-1",
            "sensitive": False,
            "category": "terraform",
        },
    )
    assert r.status_code == 201
    assert r.json()["value"] == "us-east-1"


def test_tf_var_injection_into_runner(stackyard, workspace):
    """Terraform-category vars are exported as TF_VAR_* into the shim environment."""
    api = stackyard["api"]
    api(
        "POST",
        f"/api/v1/workspaces/{workspace['id']}/vars",
        json={
            "key": "image_tag",
            "value": "1.2.3",
            "sensitive": False,
            "category": "terraform",
        },
    )
    api(
        "POST",
        f"/api/v1/workspaces/{workspace['id']}/vars",
        json={
            "key": "db_password",
            "value": "hidden-but-injected",
            "sensitive": True,
            "category": "terraform",
        },
    )
    api(
        "POST",
        f"/api/v1/workspaces/{workspace['id']}/vars",
        json={
            "key": "REGION",
            "value": "eu-west-1",
            "sensitive": False,
            "category": "env",
        },
    )
    r = api(
        "POST",
        f"/api/v1/workspaces/{workspace['id']}/runs",
        json={"command": "plan", "message": "inject"},
    )
    assert r.status_code == 201, r.text
    env_dump = read_text(Path(stackyard["shim_env"]))
    assert "TF_VAR_image_tag=1.2.3" in env_dump
    assert "TF_VAR_db_password=hidden-but-injected" in env_dump
    assert "REGION=eu-west-1" in env_dump


def test_delete_variable(stackyard, workspace):
    """Variables can be deleted and then return not found."""
    api = stackyard["api"]
    created = api(
        "POST",
        f"/api/v1/workspaces/{workspace['id']}/vars",
        json={
            "key": "tmp",
            "value": "x",
            "sensitive": False,
            "category": "env",
        },
    ).json()
    r = api("DELETE", f"/api/v1/vars/{created['id']}")
    assert r.status_code == 204
    assert api("GET", f"/api/v1/vars/{created['id']}").status_code == 404
