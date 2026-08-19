from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WORKFLOWS = ROOT / ".github" / "workflows"


def _workflow(name: str) -> str:
    return (WORKFLOWS / name).read_text(encoding="utf-8")


def test_only_primary_ci_workflows_auto_run_for_normal_repo_changes() -> None:
    agent = _workflow("terminus-agent-system-ci.yml")
    task = _workflow("terminus-edition-3-ci.yml")
    assert "pull_request:" in agent and "push:" in agent
    assert "pull_request:" in task and "push:" in task

    explicit_only = (
        "terminus-time-budget-ci.yml",
        "terminus-executor-bridge-ci.yml",
        "terminus-feedback-learning-ci.yml",
        "terminus-human-writing-calibration-ci.yml",
        "terminus-creator-complexity.yml",
        "terminus-production-authenticity.yml",
        "terminus-ec2-artifact-policy-direct-ci.yml",
    )
    for name in explicit_only:
        text = _workflow(name)
        assert "workflow_dispatch:" in text, name
        assert "pull_request:" not in text, name
        assert "\n  push:" not in text, name


def test_control_plane_and_task_ci_have_disjoint_normal_change_scopes() -> None:
    agent = _workflow("terminus-agent-system-ci.yml")
    task = _workflow("terminus-edition-3-ci.yml")

    for marker in (
        ".terminus/executions/**",
        ".terminus/workflows/**",
        ".terminus/reviews/**",
        ".terminus/sessions/**",
        ".terminus/designs/**",
    ):
        assert marker not in agent

    for marker in (
        "- '.terminus/**'",
        "- '.github/**'",
        "- '.cursor/**'",
        "- '.smoke/**'",
    ):
        assert marker in task


def test_automatic_task_ci_is_deterministic_only() -> None:
    task = _workflow("terminus-edition-3-ci.yml")
    assert "Oracle must score 1" in task
    assert "NOP must score 0" in task
    assert "validate_task_complexity.py" in task
    assert "validate_runtime_authenticity.py" in task
    assert "STB_AI_API_KEY" not in task
    assert "keys-set" not in task
    assert "Run Harbor LLMaJ" not in task
    assert "diff-gpt" not in task
    assert "diff-claude" not in task


def test_repository_wide_task_gates_never_scan_unrelated_tasks() -> None:
    complexity = _workflow("terminus-creator-complexity.yml")
    authenticity = _workflow("terminus-production-authenticity.yml")
    assert "for manifest in .terminus/designs" not in complexity
    assert "for manifest in .terminus/designs" not in authenticity
    assert "Validate requested task only" in complexity
    assert "Validate requested task only" in authenticity
