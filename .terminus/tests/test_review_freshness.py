"""Regression tests for commit-, packet- and policy-bound review freshness."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

CONTROL_PLANE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CONTROL_PLANE))

import validate_review_freshness as checker  # noqa: E402
from review_contract import ROLE_POLICY_VERSIONS, role_contract_hash  # noqa: E402

TASK = "demo-task"
VERSIONS = {
    "agent_system": "2.3",
    "prompts": "2.2",
    "protocol": "2.2",
    "panel": "2.2",
    "comprehensive": "1.0",
    "session": "2.4",
}


def _git(root: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=root, check=True, capture_output=True, text=True)


def _write_policies(root: Path) -> None:
    files = {
        "TERMINUS_3_AI_INSTRUCTIONS.md": "# Edition 3\nCurrent rules.\n",
        ".terminus/AGENT_SYSTEM.md": f"Agent-system policy version: `{VERSIONS['agent_system']}`\n",
        ".terminus/agents/PROTOCOL.md": f"Policy version: `{VERSIONS['protocol']}`\n",
        ".terminus/agents/PROMPTS.md": (
            f"Prompt policy version: `{VERSIONS['prompts']}`\n\n"
            "## Task Architect\nArchitect A.\n\n"
            "## Verifier Engineer\nVerifier A.\n\n"
            "## Originality & Authenticity Reviewer\nOriginality A.\n\n"
            "## Difficulty Reviewer\nDifficulty A.\n\n"
            "## Compliance Auditor\nCompliance A.\n\n"
            "## Instruction Reviewer\nInstruction A.\n\n"
            "## Engineering Documentation Reviewer\nDocumentation A.\n\n"
            "## Human Quality Reviewer\nHuman quality A.\n\n"
            "## Comprehensive Reviewer\nComprehensive A.\n\n"
            "## Trajectory Analyst\nTrajectory A.\n\n"
            "## Adjudicator\nAdjudicator A.\n"
        ),
        ".terminus/agents/COMPREHENSIVE_REVIEWER.md": (
            f"Reviewer policy version: `{VERSIONS['comprehensive']}`\n"
        ),
        ".terminus/reviewers/PRE_LLMAJ.md": f"Panel policy version: `{VERSIONS['panel']}`\n",
        ".terminus/reviewers/REVIEWER_CHECKLIST.md": "Checklist snapshot version: `fixture`\n",
        ".terminus/reviewers/reviewer_criteria.json": '{"criteria": []}\n',
        ".terminus/reviewers/HUMAN_WRITING_CALIBRATION.md": "human calibration\n",
        ".terminus/reviewers/WRITING_EXAMPLE_BANK.md": "human examples\n",
        ".terminus/GOLDEN_TASKS.md": "golden tasks\n",
        ".terminus/sessions/TEMPLATE.md": f"Session schema version: `{VERSIONS['session']}`\n",
        ".terminus/CURSOR_OPERATING.md": "Operating policy version: `1.1`\n",
        ".terminus/agents/INVOKE.md": "Invocation policy version: `1.1`\n",
    }
    for relative, content in files.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    (root / TASK).mkdir(parents=True)
    (root / ".terminus" / "agents" / "schemas").mkdir(parents=True)
    (root / ".terminus" / "sessions").mkdir(parents=True)
    _write_policies(root)
    (root / TASK / "task.toml").write_text(f'name = "{TASK}"\n', encoding="utf-8")
    (root / TASK / "instruction.md").write_text("Restore the nightly close.\n", encoding="utf-8")
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
    return root


def task_commit(root: Path) -> str:
    return subprocess.run(
        ["git", "log", "-1", "--format=%H", "--", TASK],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def head(root: Path) -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=root, check=True, capture_output=True, text=True
    ).stdout.strip()


def session_text(commit: str, gates: list[tuple[str, str, str]], state: str = "PRE_LLMAJ") -> str:
    rows = "\n".join(f"| {name} | {status} | {evidence} |" for name, status, evidence in gates)
    return (
        "# Terminus Task Session\n\n"
        f"Session schema version: `{VERSIONS['session']}`\n\n"
        "## Identity\n\n"
        f"- Task: `{TASK}`\n"
        f"- Controller state: `{state}`\n"
        f"- Current task commit: `{commit}`\n"
        f"- Agent-system policy: `{VERSIONS['agent_system']}`\n"
        f"- Specialist prompt policy: `{VERSIONS['prompts']}`\n"
        f"- Specialist protocol policy: `{VERSIONS['protocol']}`\n"
        f"- Pre-LLMaJ panel policy: `{VERSIONS['panel']}`\n"
        f"- Comprehensive reviewer policy: `{VERSIONS['comprehensive']}`\n\n"
        "## Current gates\n\n"
        "| Gate | Status | Evidence / version |\n"
        "| --- | --- | --- |\n"
        f"{rows}\n\n"
        "## Next action\n\nNone.\n"
    )


def write_session(root: Path, gates: list[tuple[str, str, str]], state: str = "PRE_LLMAJ") -> None:
    commit = task_commit(root)
    (root / ".terminus" / "sessions" / f"{TASK}.md").write_text(
        session_text(commit, gates, state), encoding="utf-8"
    )


def role_key(role: str) -> str:
    return {
        "Task Architect": "task-architect",
        "Verifier Engineer": "verifier-engineer",
        "Originality & Authenticity Reviewer": "originality",
        "Difficulty Reviewer": "difficulty-design",
        "Compliance Auditor": "compliance",
        "Instruction Reviewer": "instruction",
        "Engineering Documentation Reviewer": "documentation",
        "Human Quality Reviewer": "human-quality",
        "Comprehensive Reviewer": "comprehensive-checklist",
        "Trajectory Analyst": "trajectory",
    }[role]


def write_v3_review(
    root: Path,
    role: str,
    verdict: str = "PASS",
    confidence: str = "HIGH",
    evidence_status: str = "SUFFICIENT",
    contract_hash: str | None = None,
    review_id: str | None = None,
) -> str:
    commit = task_commit(root)
    review_id = review_id or f"{TASK}-{commit[:8]}-{role_key(role)}-fixture01"
    directory = root / ".terminus" / "reviews" / TASK / commit[:8]
    directory.mkdir(parents=True, exist_ok=True)
    review_rel = f".terminus/reviews/{TASK}/{commit[:8]}/{review_id}.json"
    packet_rel = f".terminus/reviews/{TASK}/{commit[:8]}/{review_id}.packet.json"
    contract_hash = contract_hash or role_contract_hash(root, role)
    plane_commit = head(root)

    packet = {
        "schema_version": "3.0",
        "review_id": review_id,
        "protocol_policy_version": VERSIONS["protocol"],
        "prompt_policy_version": VERSIONS["prompts"],
        "role_policy_version": ROLE_POLICY_VERSIONS[role],
        "control_plane_commit": plane_commit,
        "role_contract_hash": contract_hash,
        "task": TASK,
        "task_commit": commit,
        "state": "PRE_LLMAJ",
        "role": role,
        "question": "Fixture review question?",
        "authoritative_rules": ["TERMINUS_3_AI_INSTRUCTIONS.md"],
        "evidence_allowed": ["instruction.md"],
        "evidence_excluded": ["prior verdicts"],
        "prior_verdicts_visible": False,
        "isolation_mode": "PROCEDURAL",
        "change_since_last_review": "fixture",
        "output_schema": ".terminus/agents/schemas/review_result.schema.json",
        "review_output_path": review_rel,
    }
    review = {
        "schema_version": "3.0",
        "role": role,
        "review_id": review_id,
        "task": TASK,
        "task_commit": commit,
        "control_plane_commit": plane_commit,
        "protocol_policy_version": VERSIONS["protocol"],
        "prompt_policy_version": VERSIONS["prompts"],
        "role_policy_version": ROLE_POLICY_VERSIONS[role],
        "role_contract_hash": contract_hash,
        "context_packet": packet_rel,
        "verdict": verdict,
        "confidence": confidence,
        "evidence_status": evidence_status,
        "summary": "Fixture review summary.",
        "evidence": [
            {"type": "file", "ref": f"{TASK}/instruction.md", "observation": "Observed fixture."}
        ],
        "findings": [],
        "missing_evidence": [] if evidence_status == "SUFFICIENT" else ["required evidence"],
        "change_scope": [],
        "do_not_change": [],
        "next_gate": "next",
        "role_output": (
            {"checklist_coverage_percent": 100}
            if role == "Comprehensive Reviewer"
            else {"fixture": "ok"}
        ),
    }
    (root / packet_rel).write_text(json.dumps(packet, indent=2), encoding="utf-8")
    (root / review_rel).write_text(json.dumps(review, indent=2), encoding="utf-8")
    return review_rel


def write_aggregate(root: Path, verdict: str = "PASS") -> str:
    commit = task_commit(root)
    directory = root / ".terminus" / "reviews" / TASK / commit[:8]
    directory.mkdir(parents=True, exist_ok=True)
    rel = f".terminus/reviews/{TASK}/{commit[:8]}/pre-llmaj-aggregate.json"
    data = {
        "task": TASK,
        "task_commit": commit,
        "panel_policy_version": VERSIONS["panel"],
        "verdict": verdict,
        "review_reports": {"task_architect": "fixture.json"},
        "open_findings": [],
        "policy_conflicts": [],
    }
    (root / rel).write_text(json.dumps(data, indent=2), encoding="utf-8")
    return rel


def run(root: Path, *extra: str) -> int:
    return checker.main(["--root", str(root), *extra])


def test_current_v3_pass_with_packet_is_accepted(repo: Path) -> None:
    review = write_v3_review(repo, "Task Architect")
    write_session(repo, [("Task Architect", "PASS", review)])
    assert run(repo) == 0


def test_packet_and_review_coexist_without_packet_being_parsed_as_review(repo: Path) -> None:
    review = write_v3_review(repo, "Instruction Reviewer")
    write_session(repo, [("Instruction Reviewer", "PASS", review)])
    assert run(repo) == 0


def test_stale_task_commit_behind_pass_fails(repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    review = write_v3_review(repo, "Task Architect")
    write_session(repo, [("Task Architect", "PASS", review)])
    (repo / TASK / "instruction.md").write_text("changed task\n", encoding="utf-8")
    _git(repo, "add", TASK)
    _git(repo, "commit", "-qm", "change task")
    assert run(repo) == 1
    assert "STALE" in capsys.readouterr().out


def test_allow_stale_downgrades_only_staleness(repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    review = write_v3_review(repo, "Task Architect")
    write_session(repo, [("Task Architect", "PASS", review)])
    (repo / TASK / "instruction.md").write_text("changed task\n", encoding="utf-8")
    _git(repo, "add", TASK)
    _git(repo, "commit", "-qm", "change task")
    new_commit = task_commit(repo)
    # Keep the session identity current while its PASS evidence remains stale.
    write_session(repo, [("Task Architect", "PASS", review)])
    assert new_commit in (repo / ".terminus" / "sessions" / f"{TASK}.md").read_text(encoding="utf-8")
    assert run(repo, "--allow-stale") == 0
    assert "local triage only" in capsys.readouterr().out


@pytest.mark.parametrize(
    ("confidence", "evidence_status", "needle"),
    [("LOW", "SUFFICIENT", "LOW confidence"), ("HIGH", "INSUFFICIENT", "SUFFICIENT")],
)
def test_weak_review_evidence_cannot_back_pass(
    repo: Path,
    capsys: pytest.CaptureFixture[str],
    confidence: str,
    evidence_status: str,
    needle: str,
) -> None:
    review = write_v3_review(
        repo, "Task Architect", confidence=confidence, evidence_status=evidence_status
    )
    write_session(repo, [("Task Architect", "PASS", review)])
    assert run(repo) == 1
    assert needle in capsys.readouterr().out


def test_review_filed_under_wrong_commit_directory_fails(repo: Path) -> None:
    review_rel = write_v3_review(repo, "Task Architect")
    review = repo / review_rel
    packet = review.with_suffix(".packet.json")
    wrong_dir = review.parent.parent / "deadbeef"
    wrong_dir.mkdir()
    wrong_review = wrong_dir / review.name
    wrong_packet = wrong_dir / packet.name
    review.rename(wrong_review)
    packet.rename(wrong_packet)
    data = json.loads(wrong_review.read_text(encoding="utf-8"))
    data["context_packet"] = str(wrong_packet.relative_to(repo))
    wrong_review.write_text(json.dumps(data, indent=2), encoding="utf-8")
    packet_data = json.loads(wrong_packet.read_text(encoding="utf-8"))
    packet_data["review_output_path"] = str(wrong_review.relative_to(repo))
    wrong_packet.write_text(json.dumps(packet_data, indent=2), encoding="utf-8")
    write_session(repo, [("Task Architect", "PASS", str(wrong_review.relative_to(repo)))])
    assert run(repo) == 1


def test_missing_canonical_commit_identity_fails(repo: Path) -> None:
    review = write_v3_review(repo, "Task Architect")
    write_session(repo, [("Task Architect", "PASS", review)])
    session = repo / ".terminus" / "sessions" / f"{TASK}.md"
    text = session.read_text(encoding="utf-8")
    session.write_text(
        text.replace("- Current task commit:", "- Frozen task content commit:"), encoding="utf-8"
    )
    assert run(repo) == 1


def test_new_review_missing_packet_fails(repo: Path) -> None:
    review_rel = write_v3_review(repo, "Task Architect")
    (repo / review_rel).with_suffix(".packet.json").unlink()
    write_session(repo, [("Task Architect", "PASS", review_rel)])
    assert run(repo) == 1


def test_packet_review_metadata_mismatch_fails(repo: Path) -> None:
    review_rel = write_v3_review(repo, "Task Architect")
    review = json.loads((repo / review_rel).read_text(encoding="utf-8"))
    review["review_id"] = "tampered-review-id"
    (repo / review_rel).write_text(json.dumps(review, indent=2), encoding="utf-8")
    write_session(repo, [("Task Architect", "PASS", review_rel)])
    assert run(repo) == 1


def test_role_contract_change_stales_review_without_task_change(repo: Path) -> None:
    review_rel = write_v3_review(repo, "Instruction Reviewer")
    write_session(repo, [("Instruction Reviewer", "PASS", review_rel)])
    prompt = repo / ".terminus" / "agents" / "PROMPTS.md"
    prompt.write_text(
        prompt.read_text(encoding="utf-8").replace("Instruction A.", "Instruction B."),
        encoding="utf-8",
    )
    _git(repo, "add", ".terminus/agents/PROMPTS.md")
    _git(repo, "commit", "-qm", "change instruction reviewer contract")
    assert run(repo) == 1


def test_historical_legacy_review_under_stale_gate_is_not_revalidated(repo: Path) -> None:
    commit = task_commit(repo)
    directory = repo / ".terminus" / "reviews" / TASK / commit[:8]
    directory.mkdir(parents=True)
    legacy_rel = f".terminus/reviews/{TASK}/{commit[:8]}/legacy-task-architect.json"
    (repo / legacy_rel).write_text(
        json.dumps({"task_commit": commit, "policy_version": "2.0", "verdict": "PASS"}),
        encoding="utf-8",
    )
    write_session(repo, [("Task Architect", "STALE", legacy_rel)])
    assert run(repo) == 0


def test_non_pass_aggregate_cannot_back_pass_gate(repo: Path) -> None:
    aggregate = write_aggregate(repo, "PENDING")
    write_session(repo, [("Pre-LLMaJ aggregate", "PASS", aggregate)])
    assert run(repo) == 1


@pytest.mark.parametrize(
    ("gate", "role"),
    [
        ("Final Human Quality", "Human Quality Reviewer"),
        ("Final Compliance", "Compliance Auditor"),
        ("Trial Analysis", "Trajectory Analyst"),
    ],
)
def test_final_semantic_gate_requires_bound_review(repo: Path, gate: str, role: str) -> None:
    write_session(repo, [(gate, "PASS", "looks good")])
    assert run(repo) == 1
    # Control: a correctly bound v3 review is accepted.
    review = write_v3_review(repo, role)
    write_session(repo, [(gate, "PASS", review)])
    assert run(repo) == 0


def test_submission_ready_missing_mandatory_gate_fails(repo: Path) -> None:
    write_session(
        repo,
        [("Preflight/static", "PASS", "run 123")],
        state="SUBMISSION_READY",
    )
    assert run(repo) == 1


def test_ready_deterministic_gate_needs_run_job_or_artifact_evidence(repo: Path) -> None:
    write_session(repo, [("Oracle = 1", "PASS", "green yesterday")])
    assert run(repo) == 1


def test_comprehensive_approve_requires_100_percent_coverage(repo: Path) -> None:
    review_rel = write_v3_review(repo, "Comprehensive Reviewer", verdict="APPROVE")
    review = json.loads((repo / review_rel).read_text(encoding="utf-8"))
    review["role_output"]["checklist_coverage_percent"] = 99
    (repo / review_rel).write_text(json.dumps(review, indent=2), encoding="utf-8")
    write_session(repo, [("Comprehensive Reviewer", "APPROVE", review_rel)])
    assert run(repo) == 1


def test_ready_gate_rejects_non_ready_review_verdict(repo: Path) -> None:
    review_rel = write_v3_review(repo, "Task Architect", verdict="REVISE")
    write_session(repo, [("Task Architect", "PASS", review_rel)])
    assert run(repo) == 1
