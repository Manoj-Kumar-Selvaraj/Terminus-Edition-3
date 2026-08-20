"""Regression coverage for the dedicated Terminus CI Orchestrator agent."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
T = ROOT / ".terminus"
PORTABLE = T / "agents" / "CI_ORCHESTRATOR.md"
QUALITY_MODE = T / "agents" / "QUALITY_EXECUTION_MODE.md"
QUALITY_MODE_JSON = T / "agents" / "quality_execution_mode.json"
PROJECT_AGENT = ROOT / ".cursor" / "agents" / "terminus-ci-orchestrator.md"
QUALITY_LIFECYCLE = ROOT / ".github" / "workflows" / "terminus-quality-lifecycle.yml"
CONTROLLER_STAGE_WORKFLOW = ROOT / ".github" / "workflows" / "terminus-controller-stage.yml"
CONTROLLER_RUN_LOCATOR = ROOT / ".github" / "workflows" / "terminus-controller-run-locator.yml"
DETERMINISTIC_WORKFLOW = ROOT / ".github" / "workflows" / "terminus-deterministic-request.yml"
DETERMINISTIC_RUN_LOCATOR = ROOT / ".github" / "workflows" / "terminus-deterministic-run-locator.yml"
CONTROLLER_CLI = T / "execution" / "controller_cli.py"
CONTROLLER_STAGE_CLI = T / "execution" / "controller_stage_cli.py"


def test_portable_orchestrator_contract_is_complete() -> None:
    text = PORTABLE.read_text(encoding="utf-8")
    assert "Orchestrator policy version: `1.4`" in text
    for heading in (
        "## Decision right",
        "## Trust order",
        "## Bootstrap",
        "## Execution routing automation",
        "## Cursor local execution",
        "## Control loop",
        "## Gate order",
        "## GitHub Actions evidence",
        "## Active-chat polling",
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
        "INLINE_SPECIALIST",
        "does not issue an independent semantic PASS for its own production work",
        "INSUFFICIENT_EVIDENCE",
        "NEXT_AGENT_PROMPT",
    ):
        assert marker in text


def test_orchestrator_uses_inline_controller_and_independent_quality_routes() -> None:
    portable = PORTABLE.read_text(encoding="utf-8")
    controller = CONTROLLER_CLI.read_text(encoding="utf-8")
    workflow = QUALITY_LIFECYCLE.read_text(encoding="utf-8")
    controller_workflow = CONTROLLER_STAGE_WORKFLOW.read_text(encoding="utf-8")
    controller_stage = CONTROLLER_STAGE_CLI.read_text(encoding="utf-8")

    for marker in (
        "ORCHESTRATOR_DIRECT",
        "HOSTED_CONTROLLER",
        "HOSTED_DETERMINISTIC_VALIDATION",
        "INLINE_SPECIALIST",
        "AUTOMATED_QUALITY",
        "AUTOMATED_NO_MODEL_SKIP",
        "MANUAL_INDEPENDENT_QUALITY",
        "FRESH_ROLE_CHAT",
        "TERMINUS_Q4_Q6_MODE",
        "TERMINUS_Q8_MODE",
        "RULE_RESOLUTION",
        "QUALITY_INTERLOCK",
        "MODEL_DIAGNOSTIC_GPT",
        "MODEL_DIAGNOSTIC_CLAUDE",
        "NEXT_AGENT_PROMPT: none",
    ):
        assert marker in portable

    for marker in (
        "QUALITY_LIFECYCLE_WORKFLOW",
        "QUALITY_LIFECYCLE_STAGES",
        "CONTROLLER_STAGE_WORKFLOW",
        "AUTOMATED_CONTROLLER_STAGES",
        "build_deterministic_request",
        "deterministic_dispatch_envelope",
        'stage_id == "DETERMINISTIC_VALIDATION"',
        'payload["execution_mode"] = "HOSTED_DETERMINISTIC_VALIDATION"',
        "resolve_quality_execution_modes",
        "inline_execution_mode",
        "INLINE_SPECIALIST_SEQUENCE",
        "_inline_specialist_sequence",
        '"QUALITY_INTERLOCK"',
        '"MODEL_DIAGNOSTIC_GPT"',
        '"MODEL_DIAGNOSTIC_CLAUDE"',
        '"RULE_RESOLUTION"',
        '"quality_lifecycle": True',
        '"controller_stage": True',
        '"execution_mode": "MANUAL_INDEPENDENT_QUALITY"',
        '"trigger": "REQUEST_BRANCH_PUSH"',
    ):
        assert marker in controller

    for marker in (
        "Terminus Quality Lifecycle",
        "QUALITY_INTERLOCK",
        "MODEL_DIAGNOSTIC_GPT",
        "MODEL_DIAGNOSTIC_CLAUDE",
        "execute_optional_q8",
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


def test_quality_execution_mode_policy_is_bound_to_orchestrator() -> None:
    portable = PORTABLE.read_text(encoding="utf-8")
    policy = QUALITY_MODE.read_text(encoding="utf-8")
    policy_json = QUALITY_MODE_JSON.read_text(encoding="utf-8")
    for marker in (
        ".terminus/agents/QUALITY_EXECUTION_MODE.md",
        ".terminus/agents/quality_execution_mode.json",
        "Q1/Q2/Q3",
        "Q5",
        "Q7",
    ):
        assert marker in portable
    for marker in (
        "TERMINUS_Q4_Q6_MODE=AUTOMATED|MANUAL",
        "TERMINUS_Q8_MODE=OFF|AUTOMATED|MANUAL",
        "INLINE_SPECIALIST",
        "INLINE_SPECIALIST_SEQUENCE",
        "MANUAL_INDEPENDENT_QUALITY",
    ):
        assert marker in policy
    for marker in (
        '"TERMINUS_Q4_Q6_MODE": "AUTOMATED"',
        '"TERMINUS_Q8_MODE": "OFF"',
        '"Q1_SPEC_GAP_REPAIRER"',
        '"Q5_ORACLE_RUNTIME_REPAIR_SPECIALIST"',
        '"Q7_TASK_FORMAT_ENFORCER"',
        '"inline_stage_sequences"',
        '"SPEC_ALIGNMENT"',
    ):
        assert marker in policy_json


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


def test_orchestrator_polling_is_non_blocking_and_resumable() -> None:
    portable = PORTABLE.read_text(encoding="utf-8")
    project_agent = PROJECT_AGENT.read_text(encoding="utf-8")
    for marker in (
        "POLL_INTERVAL_SECONDS: 30",
        "PROGRESS_UPDATE_SECONDS: 120",
        "There is no policy `MAX_POLL_MINUTES`",
        ".terminus/controller-run-locators/",
        "numeric job ID",
        "Deduplicate unchanged snapshots",
        "A normal chat cannot wake itself after its active turn ends",
        "POLLING_STATUS",
    ):
        assert marker in portable
    assert "MAX_POLL_MINUTES: 20" not in portable
    for marker in (
        "seven hours",
        ".terminus/controller-run-locators/",
        "suggestions only",
        "unattended background monitoring",
    ):
        assert marker in project_agent


def test_controller_run_locator_persists_exact_run_and_job_identity() -> None:
    workflow = CONTROLLER_RUN_LOCATOR.read_text(encoding="utf-8")
    for marker in (
        "workflow_run:",
        'workflows: ["Terminus Controller Stage"]',
        "requested",
        "in_progress",
        "completed",
        "terminus-controller-request/",
        ".terminus/controller-run-locators/",
        "actions/runs/$RUN_ID/jobs?per_page=100",
        "Execute deterministic controller stage",
        "request_commit",
        "run_id",
        "run_number",
        "run_attempt",
        "job_id",
    ):
        assert marker in workflow
    for forbidden in (
        "CURSOR_API_KEY",
        "OPENAI_API_KEY",
        "ANTHROPIC_API_KEY",
        "STB_AI_API_KEY",
        "terminus-quality-executor.yml",
        "stb keys refresh",
    ):
        assert forbidden not in workflow


def test_controller_stage_has_no_policy_time_limit() -> None:
    workflow = CONTROLLER_STAGE_WORKFLOW.read_text(encoding="utf-8")
    assert "timeout-minutes:" not in workflow
    assert "Execute controller stage" in workflow


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
    assert "INLINE_SPECIALIST_SEQUENCE" in text
    assert "terminus-quality-lifecycle.yml" in text
    assert "HOSTED_DETERMINISTIC_VALIDATION" in text
    assert ".terminus/deterministic-run-locators/<task>/<request-commit>.json" in text


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


def test_orchestrator_owns_hosted_deterministic_dispatch_poll_and_record() -> None:
    portable = PORTABLE.read_text(encoding="utf-8")
    workflow = DETERMINISTIC_WORKFLOW.read_text(encoding="utf-8")
    locator = DETERMINISTIC_RUN_LOCATOR.read_text(encoding="utf-8")
    for marker in (
        "HOSTED_DETERMINISTIC_VALIDATION",
        "terminus-deterministic-request/",
        ".terminus/deterministic-run-locators/<task>/<request-commit>.json",
        "must never synthesize `DETERMINISTIC_VALIDATION=PASS`",
        "missing direct `workflow_dispatch` API",
        "workflow, not the chat",
    ):
        assert marker in portable
    for marker in (
        "Reconstruct exact controller invocation",
        "Compile empirical StageResult",
        "deterministic_evidence.py",
        "controller_cli.py record",
        "Record deterministic result on canonical main",
    ):
        assert marker in workflow
    for marker in (
        'workflows: ["Terminus Deterministic Request"]',
        ".terminus/deterministic-run-locators/$task/$REQUEST_SHA.json",
        "run_id",
        "job_id",
    ):
        assert marker in locator
