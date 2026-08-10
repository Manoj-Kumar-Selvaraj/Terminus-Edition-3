"""Regression coverage for the dedicated Terminus CI Orchestrator agent."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
T = ROOT / ".terminus"
PORTABLE = T / "agents" / "CI_ORCHESTRATOR.md"
PROJECT_AGENT = ROOT / ".cursor" / "agents" / "terminus-ci-orchestrator.md"


def test_portable_orchestrator_contract_is_complete() -> None:
    text = PORTABLE.read_text(encoding="utf-8")
    assert "Orchestrator policy version: `1.2`" in text
    for heading in (
        "## Decision right",
        "## Trust order",
        "## Bootstrap",
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
        "assign exactly one responsible role",
        "Do not perform that role inside the Orchestrator context",
        "does not author task implementation",
        "does not perform the routed producer/fixer or reviewer role",
        "INSUFFICIENT_EVIDENCE",
        "NEXT_AGENT_PROMPT",
    ):
        assert marker in text


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
    assert "Do not perform the routed role" in text


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
