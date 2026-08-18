"""Regression coverage for DEFECT_TOPOLOGY complexity isolation."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

CONTROL_PLANE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CONTROL_PLANE))

import validate_defect_topology as gate  # noqa: E402

TASK = "topology-only"


def write_manifest(root: Path, *, edge_limit: int = 19) -> None:
    designs = root / ".terminus" / "designs"
    designs.mkdir(parents=True)
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
    edges = [{"from": f"D{i:02d}", "to": f"D{i + 1:02d}"} for i in range(edge_limit)]
    (designs / f"{TASK}.json").write_text(
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


def test_topology_gate_requires_neither_environment_nor_verifier(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "repo"
    write_manifest(root)
    monkeypatch.setattr(gate, "ROOT", root)
    assert not (root / TASK / "environment").exists()
    assert not (root / TASK / "tests").exists()
    assert not (root / ".terminus" / "designs" / f"{TASK}-test-map.json").exists()
    assert gate.validate(TASK) == 0


def test_topology_gate_keeps_interdependency_floor(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    root = tmp_path / "repo"
    write_manifest(root, edge_limit=13)
    monkeypatch.setattr(gate, "ROOT", root)
    assert gate.validate(TASK) == 1
    assert "require at least 15" in capsys.readouterr().err
