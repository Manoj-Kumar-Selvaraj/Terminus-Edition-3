from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(autouse=True)
def _complete_external_gate_temp_snapshot(request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch):
    """Add root control policy only for tests that compile an external-gate invocation."""
    if not request.module.__name__.endswith("test_external_gate_controller"):
        yield
        return
    original = request.module._temp_control_repo

    def wrapped(tmp_path: Path):
        root, _commit = original(tmp_path)
        shutil.copy2(ROOT / ".terminus" / "AGENT_SYSTEM.md", root / ".terminus" / "AGENT_SYSTEM.md")
        subprocess.run(["git", "-C", str(root), "add", ".terminus/AGENT_SYSTEM.md"], check=True)
        subprocess.run(["git", "-C", str(root), "commit", "--amend", "--no-edit"], check=True, capture_output=True)
        commit = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        return root, commit

    monkeypatch.setattr(request.module, "_temp_control_repo", wrapped)
    yield
