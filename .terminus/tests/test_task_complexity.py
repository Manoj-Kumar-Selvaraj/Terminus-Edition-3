"""Regression tests for strict scale requirements and structural authenticity."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

CONTROL_PLANE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CONTROL_PLANE))

import validate_task_complexity as gate  # noqa: E402

TASK = "demo-large-system"
CLUSTERS = ["C-IDENTITY", "C-CAPACITY", "C-RESUME", "C-CLOSE"]
REQUIREMENTS = [f"REQ-{index}" for index in range(1, 9)]
F2P_SPREAD = [4, 4, 3, 3, 3, 3, 3, 2]


def defects() -> list[dict]:
    return [
        {
            "id": f"D{index:02d}",
            "component": f"lib/module_{index % 6}.sh",
            "observable_failure": f"Subsystem {index} leaves settlement state {index} inconsistent.",
            "root_cause": CLUSTERS[(index - 1) % len(CLUSTERS)],
            "partial_fix_trap": f"Repairing manifestation {index} alone leaves a downstream invariant broken.",
        }
        for index in range(1, 21)
    ]


def edges() -> list[dict]:
    return [{"from": f"D{index:02d}", "to": f"D{index + 1:02d}"} for index in range(1, 20)]


def tests() -> list[list[str]]:
    entries: list[list[str]] = []
    counter = 0
    for requirement, count in zip(REQUIREMENTS, F2P_SPREAD):
        for _ in range(count):
            counter += 1
            entries.append([f"test_f2p_scenario_{counter:02d}_behaviour", "F2P", requirement])
    entries.extend(
        [
            ["test_p2p_stable_interface_still_answers", "P2P", REQUIREMENTS[0]],
            ["test_p2p_history_keeps_rejected_business", "P2P", REQUIREMENTS[1]],
        ]
    )
    return entries


def env_file(index: int, count: int = 40) -> str:
    lines = [f"# unique module {index}", "set -euo pipefail"]
    lines.extend(
        f"step_{index}_{step}() {{ printf 'stage {index}.{step} value {index * 1000 + step}\\n'; }}"
        for step in range(count)
    )
    return "\n".join(lines) + "\n"


def write_tests(root: Path, entries: list[list[str]]) -> None:
    body = "\n\n".join(
        f'def {name}():\n    """Checks {requirement}."""\n    assert True'
        for name, _classification, requirement in entries
    )
    (root / TASK / "tests" / "test_outputs.py").write_text(body + "\n", encoding="utf-8")


def write_design(
    root: Path,
    *,
    profile: str = "large_system",
    defect_items: list[dict] | None = None,
    edge_items: list[dict] | None = None,
    task_kind: str = "software",
    resource_count: int | None = None,
) -> None:
    data = {
        "schema_version": "1.0",
        "profile": profile,
        "task_kind": task_kind,
        "task": TASK,
        "root_cause_clusters": {name: f"{name} description" for name in CLUSTERS},
        "defects": defects() if defect_items is None else defect_items,
        "causal_edges": edges() if edge_items is None else edge_items,
    }
    if resource_count is not None:
        data["resource_count"] = resource_count
    (root / ".terminus" / "designs" / f"{TASK}.json").write_text(
        json.dumps(data, indent=2), encoding="utf-8"
    )


def write_test_map(root: Path, entries: list[list[str]]) -> None:
    (root / ".terminus" / "designs" / f"{TASK}-test-map.json").write_text(
        json.dumps(
            {
                "schema_version": "1.0",
                "task": TASK,
                "requirements": {name: f"{name} behavior" for name in REQUIREMENTS},
                "tests": entries,
            },
            indent=2,
        ),
        encoding="utf-8",
    )


def inflate_to_strict_scale(root: Path) -> None:
    lib = root / TASK / "environment" / "eod" / "lib"
    # 30 unique files x ~102 substantive lines plus the baseline files -> >3000 LOC.
    for index in range(100, 130):
        (lib / f"large_{index}.sh").write_text(env_file(index, 105), encoding="utf-8")


@pytest.fixture
def repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    root = tmp_path / "repo"
    task = root / TASK
    (task / "environment" / "eod" / "lib").mkdir(parents=True)
    (task / "tests").mkdir()
    (root / ".terminus" / "designs").mkdir(parents=True)
    (task / "task.toml").write_text(f'name = "{TASK}"\n', encoding="utf-8")
    for index in range(6):
        (task / "environment" / "eod" / "lib" / f"module_{index}.sh").write_text(
            env_file(index), encoding="utf-8"
        )
    entries = tests()
    write_tests(root, entries)
    write_design(root)
    write_test_map(root, entries)
    monkeypatch.setattr(gate, "ROOT", root)
    return root


def test_non_strict_coupled_but_undersized_task_passes_with_diagnostic(
    repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert gate.validate(TASK) == 0
    output = capsys.readouterr().out
    assert "below required 3000" in output
    assert "strict=false" in output


def test_strict_profile_blocks_undersized_task(repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    write_design(repo, profile="large_system_strict")
    assert gate.validate(TASK) == 1
    assert "below required 3000" in capsys.readouterr().err


def test_strict_profile_passes_when_scale_and_authenticity_both_pass(repo: Path) -> None:
    inflate_to_strict_scale(repo)
    write_design(repo, profile="large_system_strict")
    assert gate.validate(TASK) == 0


def test_duplicated_environment_file_fails(repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    lib = repo / TASK / "environment" / "eod" / "lib"
    (lib / "copied.sh").write_text((lib / "module_1.sh").read_text(encoding="utf-8"), encoding="utf-8")
    assert gate.validate(TASK) == 1
    assert "equivalent" in capsys.readouterr().err


def test_duplicate_observable_failure_fails(repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    items = defects()
    items[5]["observable_failure"] = "  " + items[4]["observable_failure"].upper() + "  "
    write_design(repo, defect_items=items)
    assert gate.validate(TASK) == 1
    assert "same observable failure" in capsys.readouterr().err


def test_no_cross_cluster_causality_fails(repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    items = defects()
    by_cluster: dict[str, list[str]] = {}
    for item in items:
        by_cluster.setdefault(item["root_cause"], []).append(item["id"])
    intra = []
    for ids in by_cluster.values():
        intra.extend({"from": ids[index], "to": ids[index + 1]} for index in range(len(ids) - 1))
    write_design(repo, defect_items=items, edge_items=intra)
    assert gate.validate(TASK) == 1
    assert "no edge between different root-cause clusters" in capsys.readouterr().err


def test_empty_root_cause_cluster_fails(repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    items = [item for item in defects() if item["root_cause"] != CLUSTERS[-1]]
    valid = {item["id"] for item in items}
    remaining_edges = [edge for edge in edges() if edge["from"] in valid and edge["to"] in valid]
    write_design(repo, defect_items=items, edge_items=remaining_edges)
    assert gate.validate(TASK) == 1
    assert "has no defect manifestation" in capsys.readouterr().err


def test_untested_requirement_fails(repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    entries = [entry for entry in tests() if entry[2] != REQUIREMENTS[-1]]
    write_tests(repo, entries)
    write_test_map(repo, entries)
    assert gate.validate(TASK) == 1
    assert "has no test" in capsys.readouterr().err


def test_one_requirement_dominating_f2p_fails(repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    entries = tests()
    f2p_seen = 0
    for entry in entries:
        if entry[1] == "F2P":
            f2p_seen += 1
            if f2p_seen <= 11:
                entry[2] = REQUIREMENTS[0]
    write_test_map(repo, entries)
    assert gate.validate(TASK) == 1
    assert "dominates the suite" in capsys.readouterr().err


def test_test_map_drift_fails(repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    write_test_map(repo, tests()[:-1])
    assert gate.validate(TASK) == 1
    assert "absent from test map" in capsys.readouterr().err


def test_f2p_p2p_classification_mismatch_fails(repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    entries = tests()
    entries[0][1] = "P2P"
    write_test_map(repo, entries)
    assert gate.validate(TASK) == 1
    assert "classification drift" in capsys.readouterr().err


def test_invalid_test_map_class_fails(repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    entries = tests()
    entries[0][1] = "SMOKE"
    write_test_map(repo, entries)
    assert gate.validate(TASK) == 1
    assert "invalid classification" in capsys.readouterr().err


@pytest.mark.parametrize("resource_count", [29, 51])
def test_strict_infrastructure_resource_floor_and_ceiling(
    repo: Path, capsys: pytest.CaptureFixture[str], resource_count: int
) -> None:
    inflate_to_strict_scale(repo)
    write_design(
        repo,
        profile="large_system_strict",
        task_kind="infrastructure",
        resource_count=resource_count,
    )
    assert gate.validate(TASK) == 1
    assert "outside required 30-50" in capsys.readouterr().err


def test_strict_infrastructure_with_30_to_50_resources_passes(repo: Path) -> None:
    inflate_to_strict_scale(repo)
    write_design(repo, profile="large_system_strict", task_kind="infrastructure", resource_count=40)
    assert gate.validate(TASK) == 0
