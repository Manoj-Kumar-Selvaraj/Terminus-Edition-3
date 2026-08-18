"""Regression coverage for ENVIRONMENT_BUILD complexity isolation."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

CONTROL_PLANE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CONTROL_PLANE))

import validate_environment_complexity as environment_gate  # noqa: E402
import validate_task_complexity as full_gate  # noqa: E402

TASK = "edge-router-runtime"


def test_environment_gate_does_not_require_private_test_map() -> None:
    test_map = CONTROL_PLANE / "designs" / f"{TASK}-test-map.json"
    assert not test_map.exists(), "regression requires the pre-verifier lifecycle state"
    assert environment_gate.validate(TASK) == 0


def test_full_gate_still_requires_private_test_map(capsys: pytest.CaptureFixture[str]) -> None:
    test_map = CONTROL_PLANE / "designs" / f"{TASK}-test-map.json"
    assert not test_map.exists(), "regression requires the pre-verifier lifecycle state"
    with pytest.raises(SystemExit) as exc:
        full_gate.validate(TASK)
    assert exc.value.code == 1
    assert "missing private test map" in capsys.readouterr().err


def test_environment_gate_keeps_strict_loc_floor(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    root = tmp_path / "repo"
    task = root / "strict-small"
    (task / "environment").mkdir(parents=True)
    (root / ".terminus" / "designs").mkdir(parents=True)
    (task / "task.toml").write_text('name = "strict-small"\n', encoding="utf-8")
    (task / "environment" / "main.go").write_text("package main\nfunc main() {}\n", encoding="utf-8")
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
    import json

    (root / ".terminus" / "designs" / "strict-small.json").write_text(
        json.dumps(
            {
                "profile": "large_system_strict",
                "task": "strict-small",
                "root_cause_clusters": {f"C{i}": f"cluster {i}" for i in range(4)},
                "defects": defects,
                "causal_edges": edges,
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(environment_gate, "ROOT", root)
    assert environment_gate.validate("strict-small") == 1
    assert "below required 3000" in capsys.readouterr().err
