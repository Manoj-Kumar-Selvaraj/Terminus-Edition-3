"""Regression coverage for ENVIRONMENT_BUILD complexity isolation."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

CONTROL_PLANE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CONTROL_PLANE))

import validate_environment_complexity as environment_gate  # noqa: E402
import validate_task_complexity as full_gate  # noqa: E402

TASK = "environment-only"


def write_fixture(root: Path, *, substantive_lines: int = 3050) -> None:
    task = root / TASK
    (task / "environment").mkdir(parents=True)
    (root / ".terminus" / "designs").mkdir(parents=True)
    (task / "task.toml").write_text(f'name = "{TASK}"\n', encoding="utf-8")
    body = ["package main", "func main() {}"]
    body.extend(f"var Value{i} = {i}" for i in range(substantive_lines))
    (task / "environment" / "main.go").write_text("\n".join(body) + "\n", encoding="utf-8")

    defects = [
        {
            "id": f"D{i:02d}",
            "component": f"internal/c{i % 5}.go",
            "observable_failure": f"failure {i}",
            "root_cause": f"C{i % 4}",
            "partial_fix_trap": "partial fix remains incomplete",
        }
        for i in range(20)
    ]
    edges = [{"from": f"D{i:02d}", "to": f"D{i + 1:02d}"} for i in range(19)]
    (root / ".terminus" / "designs" / f"{TASK}.json").write_text(
        json.dumps(
            {
                "profile": "large_system_strict",
                "task": TASK,
                "root_cause_clusters": {f"C{i}": f"cluster {i}" for i in range(4)},
                "defects": defects,
                "causal_edges": edges,
            }
        ),
        encoding="utf-8",
    )


def bind_root(root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(environment_gate, "ROOT", root)
    monkeypatch.setattr(full_gate, "ROOT", root)


def test_environment_gate_does_not_require_private_test_map(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "repo"
    write_fixture(root)
    bind_root(root, monkeypatch)
    assert not (root / TASK / "tests").exists()
    assert not (root / ".terminus" / "designs" / f"{TASK}-test-map.json").exists()
    assert environment_gate.validate(TASK) == 0


def test_full_gate_still_requires_private_test_map(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    root = tmp_path / "repo"
    write_fixture(root)
    bind_root(root, monkeypatch)
    with pytest.raises(SystemExit) as exc:
        full_gate.validate(TASK)
    assert exc.value.code == 1
    assert "missing private test map" in capsys.readouterr().err


def test_environment_gate_keeps_strict_loc_floor(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    root = tmp_path / "repo"
    write_fixture(root, substantive_lines=10)
    bind_root(root, monkeypatch)
    assert environment_gate.validate(TASK) == 1
    assert "below required 3000" in capsys.readouterr().err
