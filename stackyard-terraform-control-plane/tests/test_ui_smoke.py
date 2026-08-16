"""UI presence and API-through-UI contract smoke tests."""

from __future__ import annotations

from pathlib import Path

APP = Path("/app/stackyard")


def test_ui_index_served(stackyard):
    """Root serves the Stackyard operator HTML shell."""
    r = stackyard["api"]("GET", "/")
    assert r.status_code == 200
    text = r.text
    assert "Stackyard" in text
    assert 'id="run-form"' in text
    assert 'name="command"' in text
    assert 'id="error-box"' in text


def test_ui_assets_present(stackyard):
    """CSS and JS assets are reachable and include operator wiring markers."""
    css = stackyard["api"]("GET", "/css/app.css")
    js = stackyard["api"]("GET", "/js/app.js")
    assert css.status_code == 200
    assert js.status_code == 200
    assert "error-box" in js.text
    # Fixed UI must post command, not cmd.
    assert "command:" in js.text
    assert "cmd:" not in js.text


def test_ui_js_surfaces_errors(stackyard):
    """UI script shows API error strings instead of swallowing failures."""
    js = (APP / "ui" / "js" / "app.js").read_text(encoding="utf-8")
    assert "body.error" in js
    assert "cmd:" not in js


def test_ui_forms_cover_lock_and_vars(stackyard):
    """HTML includes lock, unlock, and sensitive variable controls."""
    html = stackyard["api"]("GET", "/").text
    assert 'id="lock-form"' in html
    assert 'id="unlock-form"' in html
    assert 'name="sensitive"' in html
    assert 'id="var-form"' in html


def test_runs_list_endpoint_shape(stackyard, workspace):
    """Runs listing returns newest-first array envelope used by the UI."""
    api = stackyard["api"]
    api(
        "POST",
        f"/api/v1/workspaces/{workspace['id']}/runs",
        json={"command": "validate", "message": "ui"},
    )
    r = api("GET", f"/api/v1/workspaces/{workspace['id']}/runs")
    assert r.status_code == 200
    body = r.json()
    assert "runs" in body
    assert isinstance(body["runs"], list)
    assert body["runs"][0]["command"] == "validate"
