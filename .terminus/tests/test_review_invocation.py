"""Regression tests for fail-closed semantic review dispatch."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

CONTROL_PLANE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CONTROL_PLANE))

import new_review_packet as generator  # noqa: E402
import validate_review_invocation as guard  # noqa: E402

TASK = "demo-task"


def _git(root: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=root, check=True, capture_output=True, text=True)


def _policies(root: Path) -> None:
    files = {
        "TERMINUS_3_AI_INSTRUCTIONS.md": "# Edition 3\nCurrent local rules.\n",
        ".terminus/AGENT_SYSTEM.md": "Agent-system policy version: `2.4`\n",
        ".terminus/agents/PROTOCOL.md": "Policy version: `2.2`\n",
        ".terminus/agents/PROMPTS.md": "Prompt policy version: `2.2`\n\n## Adjudicator\nAdjudicator A.\n\n## Task Architect\nArchitect A.\n",
        ".terminus/agents/PRODUCTION_AUTHENTICITY.md": "Production authenticity policy.\n",
        ".terminus/agents/QUALITY_AGENT_REGISTRY.md": "Quality-agent registry version: `1.1`\n",
        ".terminus/agents/QUALITY_AGENT_PROMPTS.md": "Quality-agent prompt policy version: `1.1`\n\n## Q4 — Spec-Test Contract Reviewer\nQ4 A.\n\n## Q6 — Production Logic Auditor\nQ6 A.\n",
        ".terminus/agents/COMPREHENSIVE_REVIEWER.md": "Reviewer policy version: `1.0`\n",
        ".terminus/reviewers/PRE_LLMAJ.md": "Panel policy version: `2.2`\n",
        ".terminus/reviewers/REVIEWER_CHECKLIST.md": "Checklist snapshot version: `fixture`\n",
        ".terminus/reviewers/reviewer_criteria.json": '{"criteria": []}\n',
        ".terminus/reviewers/HUMAN_WRITING_CALIBRATION.md": "human calibration\n",
        ".terminus/reviewers/WRITING_EXAMPLE_BANK.md": "human examples\n",
        ".terminus/GOLDEN_TASKS.md": "golden references\n",
        ".terminus/sessions/TEMPLATE.md": "Session schema version: `2.4`\n",
        ".terminus/CURSOR_OPERATING.md": "Operating policy version: `1.1`\n",
        ".terminus/agents/INVOKE.md": "Invocation policy version: `1.1`\n",
    }
    for relative, content in files.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")


@pytest.fixture
def repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    root = tmp_path / "repo"
    (root / TASK / "environment").mkdir(parents=True)
    (root / ".terminus" / "agents" / "schemas").mkdir(parents=True)
    _policies(root)
    (root / TASK / "task.toml").write_text(f'name = "{TASK}"\n', encoding="utf-8")
    (root / TASK / "instruction.md").write_text("Repair the evaluator.\n", encoding="utf-8")
    (root / TASK / "environment" / "app.py").write_text("print('starter')\n", encoding="utf-8")
    for name in ("context_packet.schema.json", "review_result.schema.json"):
        source = CONTROL_PLANE / "agents" / "schemas" / name
        (root / ".terminus" / "agents" / "schemas" / name).write_text(
            source.read_text(encoding="utf-8"), encoding="utf-8"
        )

    _git(root, "init", "-q", "-b", "main")
    _git(root, "config", "user.email", "control-plane@example.invalid")
    _git(root, "config", "user.name", "Terminus Test")
    _git(root, "add", "-A")
    _git(root, "commit", "-qm", "fixture baseline")

    monkeypatch.setattr(generator, "ROOT", root)
    monkeypatch.setattr(generator, "T", root / ".terminus")
    guard.set_root(root)
    return root


def _task_commit(root: Path) -> str:
    return subprocess.run(
        ["git", "log", "-1", "--format=%H", "--", TASK],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _packet(root: Path, role_key: str = "task-architect") -> Path:
    commit = _task_commit(root)
    packet = generator.build(TASK, role_key, "FROZEN_CANDIDATE", "", commit)
    output = root / packet["review_output_path"]
    path = output.with_suffix(".packet.json")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(packet, indent=2) + "\n", encoding="utf-8")
    return path


def test_current_unused_packet_is_ready(repo: Path) -> None:
    packet = _packet(repo)
    assert guard.validate_invocation(packet) == []


def test_stale_task_commit_is_blocked_before_review(repo: Path) -> None:
    packet = _packet(repo)
    (repo / TASK / "instruction.md").write_text("Changed task contract.\n", encoding="utf-8")
    _git(repo, "add", TASK)
    _git(repo, "commit", "-qm", "change task")
    problems = guard.validate_invocation(packet)
    assert any("stale packet task_commit" in problem for problem in problems)


def test_existing_result_path_blocks_rerun(repo: Path) -> None:
    packet = _packet(repo)
    data = json.loads(packet.read_text(encoding="utf-8"))
    result = repo / data["review_output_path"]
    result.write_text("{}\n", encoding="utf-8")
    problems = guard.validate_invocation(packet)
    assert any("immutable review output already exists" in problem for problem in problems)


def test_stale_role_contract_is_blocked(repo: Path) -> None:
    packet = _packet(repo)
    prompts = repo / ".terminus" / "agents" / "PROMPTS.md"
    prompts.write_text(
        prompts.read_text(encoding="utf-8").replace("Architect A.", "Architect B."),
        encoding="utf-8",
    )
    _git(repo, "add", str(prompts.relative_to(repo)))
    _git(repo, "commit", "-qm", "change role contract")
    problems = guard.validate_invocation(packet)
    assert any("stale packet role contract" in problem for problem in problems)


def test_q6_scope_change_is_blocked(repo: Path) -> None:
    packet = _packet(repo, "production-logic")
    environment = repo / TASK / "environment" / "app.py"
    environment.write_text("print('changed')\n", encoding="utf-8")
    _git(repo, "add", TASK)
    _git(repo, "commit", "-qm", "change production scope")
    problems = guard.validate_invocation(packet)
    assert any("stale packet task_commit" in problem for problem in problems)
    assert any("stale packet review scope" in problem for problem in problems)
