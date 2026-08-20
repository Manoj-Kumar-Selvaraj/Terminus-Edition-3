from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / ".terminus"))

from execution import quality_budget, quality_executor  # noqa: E402
from execution.quality_backend import execute_flag_backend  # noqa: E402,F401
from execution.quality_execution_guard import (  # noqa: E402
    ensure_review_output_unoccupied,
    execute_quality_packet,
    materialize_projection,
)


def _git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_lifecycle_backend_installs_projection_and_immutability_guards() -> None:
    assert quality_executor.materialize_projection is materialize_projection
    assert quality_executor.execute_quality_packet is execute_quality_packet


def test_q4_private_test_map_comes_from_control_plane_commit(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init")
    _git(repo, "config", "user.name", "Terminus Test")
    _git(repo, "config", "user.email", "terminus-test@example.com")

    task = "quality-test"
    _write(repo / task / "instruction.md", "# Task\n")
    _write(repo / task / "task.toml", "version = '1'\n")
    _write(repo / task / "tests/test_smoke.py", "def test_smoke():\n    assert True\n")
    _write(repo / "TERMINUS_3_AI_INSTRUCTIONS.md", "# Rules\n")
    _write(repo / ".terminus/AGENT_SYSTEM.md", "# Agent system\n")
    _write(repo / ".terminus/agents/POLICY.md", "# Policy\n")
    test_map = repo / f".terminus/designs/{task}-test-map.json"
    _write(test_map, json.dumps({"source": "task-commit"}) + "\n")
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "task snapshot")
    task_commit = _git(repo, "rev-parse", "HEAD")

    _write(test_map, json.dumps({"source": "control-plane"}) + "\n")
    _git(repo, "add", str(test_map.relative_to(repo)))
    _git(repo, "commit", "-m", "control-plane map update")
    control_commit = _git(repo, "rev-parse", "HEAD")

    review_id = f"{task}-{task_commit[:8]}-spec-test-contract-regression"
    review_rel = Path(
        f".terminus/reviews/{task}/{task_commit[:8]}/{review_id}.json"
    )
    packet_rel = review_rel.with_name(review_rel.stem + ".packet.json")
    _write(repo / packet_rel, "{}\n")
    packet = {
        "task": task,
        "task_commit": task_commit,
        "control_plane_commit": control_commit,
        "role": quality_executor.Q4_ROLE,
        "review_output_path": review_rel.as_posix(),
    }

    projection = materialize_projection(repo, packet_rel, packet, tmp_path / "projection")
    projected_map = projection.root / f".terminus/designs/{task}-test-map.json"
    assert json.loads(projected_map.read_text(encoding="utf-8")) == {
        "source": "control-plane"
    }


def test_occupied_review_output_fails_before_budget_receipt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    task = "quality-test"
    task_commit = "a" * 40
    review_id = f"{task}-{task_commit[:8]}-spec-test-contract-occupied"
    review_rel = Path(
        f".terminus/reviews/{task}/{task_commit[:8]}/{review_id}.json"
    )
    packet_rel = review_rel.with_name(review_rel.stem + ".packet.json")
    packet = {
        "task": task,
        "task_commit": task_commit,
        "control_plane_commit": "b" * 40,
        "review_id": review_id,
        "role": quality_executor.Q4_ROLE,
        "review_output_path": review_rel.as_posix(),
    }
    _write(packet_rel, json.dumps(packet) + "\n")
    _write(review_rel, "{}\n")

    with pytest.raises(
        quality_executor.QualityExecutorError, match="immutable review IDs cannot be reused"
    ):
        ensure_review_output_unoccupied(tmp_path, packet)

    state_root = tmp_path / "budget-state"
    rc = quality_budget.main(
        [
            "--root",
            str(tmp_path),
            "--packet",
            packet_rel.as_posix(),
            "--state-root",
            str(state_root),
            "--backend",
            "cursor",
            "--run-id",
            "123",
            "--run-attempt",
            "1",
        ]
    )
    assert rc == 2
    assert not (state_root / "q-runs").exists()
