"""Regression coverage for non-payment production-authenticity datasets."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

CONTROL_PLANE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CONTROL_PLANE))

import validate_runtime_authenticity as gate  # noqa: E402

TASK = "demo-generic-production-task"


def schema_sql() -> str:
    return """
CREATE TABLE events(
    event_id INTEGER PRIMARY KEY,
    region TEXT NOT NULL,
    device_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    priority INTEGER NOT NULL
);
"""


def seed_sql(count: int = 10050) -> str:
    return f"""
WITH RECURSIVE n(x) AS (VALUES(1) UNION ALL SELECT x+1 FROM n WHERE x<{count})
INSERT INTO events(event_id,region,device_id,event_type,priority)
SELECT x,
       CASE x%2 WHEN 0 THEN 'east' ELSE 'west' END,
       printf('dev-%03d',1+(x%120)),
       printf('type-%02d',1+(x%8)),
       x%10
FROM n;
"""


def design() -> dict:
    return {
        "schema_version": "1.0",
        "profile": "large_system_strict",
        "task_kind": "software",
        "task": TASK,
        "production_authenticity": {
            "incident_evidence": [
                "environment/app/log/archive/run.log",
                "environment/app/ops/handoff.txt",
            ],
            "instruction_evidence_paths": [
                "/app/log/archive",
                "/app/ops",
            ],
            "stateful_dataset": {
                "schema": "environment/app/sql/schema.sql",
                "seed": "environment/app/sql/seed.sql",
                "primary_table": "events",
                "min_records": 10000,
                "max_records": 20000,
                "variance_queries": {
                    "regions": {
                        "sql": "SELECT COUNT(DISTINCT region) FROM events",
                        "min": 2,
                    },
                    "devices": {
                        "sql": "SELECT COUNT(DISTINCT device_id) FROM events",
                        "min": 100,
                    },
                    "event_types": {
                        "sql": "SELECT COUNT(DISTINCT event_type) FROM events",
                        "min": 8,
                    },
                    "priorities": {
                        "sql": "SELECT COUNT(DISTINCT priority) FROM events",
                        "min": 10,
                    },
                },
            },
        },
    }


@pytest.fixture
def repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    root = tmp_path / "repo"
    task = root / TASK
    (task / "environment/app/sql").mkdir(parents=True)
    (task / "environment/app/log/archive").mkdir(parents=True)
    (task / "environment/app/ops").mkdir(parents=True)
    (root / ".terminus/designs").mkdir(parents=True)
    (task / "task.toml").write_text(f'name = "{TASK}"\n', encoding="utf-8")
    (task / "instruction.md").write_text(
        "Inspect /app/log/archive and /app/ops before repairing regional continuity.\n",
        encoding="utf-8",
    )
    (task / "README.md").write_text(
        "# Event service\n\nOperational notes for the inherited regional event service.\n",
        encoding="utf-8",
    )
    (task / "environment/app/log/archive/run.log").write_text(
        "2026-08-08 region=west state=disconnected archive_lag=145\n" * 3,
        encoding="utf-8",
    )
    (task / "environment/app/ops/handoff.txt").write_text(
        "Night shift stopped replay after archive membership diverged from the edge journal.\n" * 3,
        encoding="utf-8",
    )
    (task / "environment/app/sql/schema.sql").write_text(schema_sql(), encoding="utf-8")
    (task / "environment/app/sql/seed.sql").write_text(seed_sql(), encoding="utf-8")
    (root / ".terminus/designs" / f"{TASK}.json").write_text(
        json.dumps(design(), indent=2),
        encoding="utf-8",
    )
    monkeypatch.setattr(gate, "ROOT", root)
    return root


def test_generic_stateful_dataset_passes_without_cobol_or_payment_columns(repo: Path) -> None:
    assert gate.validate(TASK) == 0


def test_generic_variance_threshold_failure_is_reported(
    repo: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    manifest_path = repo / ".terminus/designs" / f"{TASK}.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["production_authenticity"]["stateful_dataset"]["variance_queries"]["regions"]["min"] = 3
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    assert gate.validate(TASK) == 1
    assert "seed regions=2 is below required 3" in capsys.readouterr().err


def test_generic_variance_query_must_be_read_only_scalar(repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    manifest_path = repo / ".terminus/designs" / f"{TASK}.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["production_authenticity"]["stateful_dataset"]["variance_queries"]["regions"]["sql"] = (
        "DELETE FROM events"
    )
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    assert gate.validate(TASK) == 1
    assert "must be a SELECT/WITH scalar query" in capsys.readouterr().err
