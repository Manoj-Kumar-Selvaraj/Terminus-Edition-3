"""Regression coverage for the dedicated Terminus CI Orchestrator agent."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
T = ROOT / ".terminus"
PORTABLE = T / "agents" / "CI_ORCHESTRATOR.md"
PROJECT_AGENT = ROOT / ".cursor" / "agents" / "terminus-ci-orchestrator.md"
QUALITY_LIFECYCLE = ROOT / ".github" / "workflows" / "terminus-quality-lifecycle.yml"
CONTROLLER_STAGE_WORKFLOW = ROOT / ".github" / "workflows" / "terminus-controller-stage.yml"
CONTROLLER_CLI = T / "execution" / "controller_cli.py"
CONTROLLER_STAGE_CLI = T / "execution" / "controller_stage_cli.py"


def test_portable_orchestrator_contract_is_complete() -> None:
    text = PORTABLE.read_text(encoding="utf-8")
    assert "Orchestrator policy version: `1.3`" in text
    for heading in (
        "## Decision right",
        "## Trust order",
        "## Bootstrap",
        "## Execution routing automation",
        "## Cursor local execution",
        "## Control loop",
        "## Gate order",
        "## GitHub Actions evidence",
        "## Bounded active-chat polling",
        "## Routing",
        "## Review packets and independence",
        "## Write boundary",
        "## Circuit breakers",
        "## Required response",
        "## Submission-ready boundary",
    ):
        assert heading in text


def test_orchestrator_routes_without_self_certifying() -> None:
    text = PORTABLE.read_text(encoding="utf-8")
    for marker in (
        "first genuinely incomplete, failed, stale or blocked gate",
        "Resolve execution mode",
        "Do not perform producer/fixer or non-automated reviewer work",
        "does not author task implementation",
        "INSUFFICIENT_EVIDENCE",
        "NEXT_AGENT_PROMPT",
    ):
        assert marker in text


def test_orchestrator_uses_direct_controller_and_automated_quality_routes() -> None:
    portable = PORTABLE.read_text(encoding="utf-8")
    controller = CONTROLLER_CLI.read_text(encoding="utf-8")
    workflow = QUALITY_LIFECYCLE.read_text(encoding="utf-8")
    controller_workflow = CONTROLLER_STAGE_WORKFLOW.read_text(encoding="utf-8")
    controller_stage = CONTROLLER_STAGE_CLI.read_text(encoding="utf-8")

    for marker in (
        "ORCHESTRATOR_DIRECT",
        "AUTOMATED_QUALITY",
        "FRESH_ROLE_CHAT",
        "RULE_RESOLUTION",
        "QUALITY_INTERLOCK",
        "MODEL_DIAGNOSTIC_GPT",
        "MODEL_DIAGNOSTIC_CLAUDE",
        ".github/workflows/terminus-quality-lifecycle.yml",
        "Do not create a manual reviewer-chat handoff",
        "NEXT_AGENT_PROMPT: none",
    ):
        assert marker in portable

    for marker in (
        "QUALITY_LIFECYCLE_WORKFLOW",
        "QUALITY_LIFECYCLE_STAGES",
        "CONTROLLER_STAGE_WORKFLOW",
        "AUTOMATED_CONTROLLER_STAGES",
        '"QUALITY_INTERLOCK"',
        '"MODEL_DIAGNOSTIC_GPT"',
        '"MODEL_DIAGNOSTIC_CLAUDE"',
        '"RULE_RESOLUTION"',
        '"quality_lifecycle": True',
        '"controller_stage": True',
        '"trigger": "REQUEST_BRANCH_PUSH"',
    ):
        assert marker in controller

    for marker in (
        "Terminus Quality Lifecycle",
        "QUALITY_INTERLOCK",
        "MODEL_DIAGNOSTIC_GPT",
        "MODEL_DIAGNOSTIC_CLAUDE",
        "terminus-quality-executor.yml",
        "validate_quality_interlock.py",
        "controller_cli.py record",
    ):
        assert marker in workflow

    for marker in (
        "Terminus Controller Stage",
        "terminus-controller-request/**",
        "controller_cli.py continue",
        "controller_stage_cli.py",
        "controller_cli.py record",
        "git push origin HEAD:main",
    ):
        assert marker in controller_workflow

    for marker in (
        "SUPPORTED_DIRECT_STAGES",
        '"RULE_RESOLUTION"',
        "RULES_RESOLVED",
        "validate_agent_system.py",
        "cannot replace semantic reviewers",
    ):
        assert marker in controller_stage


def test_orchestrator_requires_commit_bound_ci_and_review_evidence() -> None:
    text = PORTABLE.read_text(encoding="utf-8")
    for marker in (
        "head SHA",
        "run ID and run number",
        "job ID",
        "log or artifact IDs",
        "role-contract hash",
        "new immutable review ID",
        "A green check is a pointer to evidence, not proof by itself",
    ):
        assert marker in text


def test_cursor_agent_uses_attached_laptop_for_preflight() -> None:
    portable = PORTABLE.read_text(encoding="utf-8")
    project_agent = PROJECT_AGENT.read_text(encoding="utf-8")
    for marker in (
        "use the attached laptop as the default environment",
        "tests, linters, format checks, validators, builds, package checks and Docker-based verification",
        "Do not merely recommend a command",
        "LOCAL_EXECUTION_STATUS",
        "do not replace required GitHub Actions/Harbor evidence",
    ):
        assert marker in portable
    for marker in (
        "attached laptop's local terminal and hardware",
        "Run relevant tests, linters, validators, builds, package checks and Docker checks yourself",
        "Treat local results as preflight evidence",
    ):
        assert marker in project_agent


def test_orchestrator_bounds_active_chat_polling() -> None:
    portable = PORTABLE.read_text(encoding="utf-8")
    project_agent = PROJECT_AGENT.read_text(encoding="utf-8")
    for marker in (
        "POLL_INTERVAL_SECONDS: 30",
        "MAX_POLL_MINUTES: 20",
        "PROGRESS_UPDATE_SECONDS: 120",
        "Deduplicate unchanged snapshots",
        "A normal chat cannot wake itself after its active turn ends",
        "POLLING_STATUS",
    ):
        assert marker in portable
    assert "bounded active-chat polling contract" in project_agent
    assert "never claim unattended background monitoring" in project_agent


def test_project_agent_frontmatter_and_contract_reference() -> None:
    text = PROJECT_AGENT.read_text(encoding="utf-8")
    match = re.match(r"^---\n(.*?)\n---\n", text, flags=re.DOTALL)
    assert match is not None
    frontmatter = match.group(1)
    assert re.search(r"(?m)^name: terminus-ci-orchestrator$", frontmatter)
    assert re.search(r"(?m)^description: .+", frontmatter)
    assert ".terminus/agents/CI_ORCHESTRATOR.md" in text
    assert "exactly one active task" in text
    assert "Do not default every stage to a fresh chat" in text
    assert "terminus-quality-lifecycle.yml" in text


def test_orchestrator_is_integrated_into_control_plane_and_ci() -> None:
    files = {
        "agent system": T / "AGENT_SYSTEM.md",
        "bootstrap": T / "CONTINUE_SESSION.md",
        "operating law": T / "CURSOR_OPERATING.md",
        "invocation": T / "agents" / "INVOKE.md",
        "prompt registry": T / "agents" / "PROMPTS.md",
    }
    combined = "\n".join(path.read_text(encoding="utf-8") for path in files.values())
    assert ".terminus/agents/CI_ORCHESTRATOR.md" in combined
    assert ".cursor/agents/terminus-ci-orchestrator.md" in combined

    workflow = (
        ROOT / ".github" / "workflows" / "terminus-agent-system-ci.yml"
    ).read_text(encoding="utf-8")
    assert ".cursor/agents/**" in workflow
