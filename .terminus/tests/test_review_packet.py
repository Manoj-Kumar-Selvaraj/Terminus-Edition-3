"""Regression tests for immutable, role-bound specialist context packets."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

CONTROL_PLANE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CONTROL_PLANE))

import new_review_packet as generator  # noqa: E402
from review_contract import role_contract_hash  # noqa: E402

TASK = "demo-task"


def _git(root: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=root, check=True, capture_output=True, text=True)


def _policies(root: Path) -> None:
    files = {
        "TERMINUS_3_AI_INSTRUCTIONS.md": "# Edition 3\nCurrent local rules.\n",
        ".terminus/AGENT_SYSTEM.md": "Agent-system policy version: `2.3`\n",
        ".terminus/agents/PROTOCOL.md": "Policy version: `2.2`\n",
        ".terminus/agents/PROMPTS.md": (
            "Prompt policy version: `2.2`\n\n"
            "## Task Architect\nArchitect contract A.\n\n"
            "## Instruction Reviewer\nInstruction contract A.\n\n"
            "## Verifier Engineer\nVerifier contract A.\n\n"
            "## Originality & Authenticity Reviewer\nOriginality contract A.\n\n"
            "## Difficulty Reviewer\nDifficulty contract A.\n\n"
            "## Compliance Auditor\nCompliance contract A.\n\n"
            "## Engineering Documentation Reviewer\nDocumentation contract A.\n\n"
            "## Human Quality Reviewer\nHuman quality contract A.\n\n"
            "## Comprehensive Reviewer\nComprehensive contract A.\n\n"
            "## Trajectory Analyst\nTrajectory contract A.\n\n"
            "## Adjudicator\nAdjudicator contract A.\n"
        ),
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
    (root / TASK).mkdir(parents=True)
    (root / ".terminus" / "agents" / "schemas").mkdir(parents=True)
    (root / ".terminus" / "sessions").mkdir(parents=True)
    _policies(root)

    (root / TASK / "task.toml").write_text(f'name = "{TASK}"\n', encoding="utf-8")
    (root / TASK / "instruction.md").write_text("Restore the nightly close.\n", encoding="utf-8")
    (root / ".terminus" / "sessions" / f"{TASK}.md").write_text(
        "- Controller state: `PRE_LLMAJ`\n", encoding="utf-8"
    )
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
    return root


def task_commit(root: Path) -> str:
    return subprocess.run(
        ["git", "log", "-1", "--format=%H", "--", TASK],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def test_packet_binds_current_task_and_policy_provenance(repo: Path) -> None:
    assert generator.main([TASK, "instruction"]) == 0
    commit = task_commit(repo)
    packets = list((repo / ".terminus" / "reviews" / TASK / commit[:8]).glob("*.packet.json"))
    assert len(packets) == 1
    packet = json.loads(packets[0].read_text(encoding="utf-8"))
    assert packet["schema_version"] == "3.0"
    assert packet["task_commit"] == commit
    assert packet["protocol_policy_version"] == "2.2"
    assert packet["prompt_policy_version"] == "2.2"
    assert packet["role_policy_version"] == "1.0"
    assert len(packet["role_contract_hash"]) == 64
    assert packet["control_plane_commit"]
    assert packet["review_output_path"].endswith(f"/{packet['review_id']}.json")
    assert packet["isolation_mode"] == "PROCEDURAL"


def test_dirty_task_tree_is_refused(repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    (repo / TASK / "instruction.md").write_text("edited\n", encoding="utf-8")
    assert generator.main([TASK, "instruction"]) == 1
    assert "uncommitted changes" in capsys.readouterr().out


def test_dirty_governing_policy_is_refused(repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    prompt = repo / ".terminus" / "agents" / "PROMPTS.md"
    prompt.write_text(prompt.read_text(encoding="utf-8") + "\npolicy edit\n", encoding="utf-8")
    assert generator.main([TASK, "instruction"]) == 1
    assert "governing policy" in capsys.readouterr().out


def test_instruction_packet_excludes_hidden_solution_and_tests(repo: Path) -> None:
    packet = generator.build(TASK, "instruction", "PRE_LLMAJ", "", task_commit(repo))
    assert "solution/" in packet["evidence_excluded"]
    assert "tests/ bodies" in packet["evidence_excluded"]
    assert packet["prior_verdicts_visible"] is False


def test_comprehensive_packet_excludes_specialist_verdicts(repo: Path) -> None:
    packet = generator.build(
        TASK, "comprehensive-checklist", "PRE_LLMAJ", "", task_commit(repo)
    )
    assert any("specialist verdicts" in item for item in packet["evidence_excluded"])


def test_every_generic_role_produces_schema_valid_packet(repo: Path) -> None:
    schema = json.loads(
        (repo / ".terminus" / "agents" / "schemas" / "context_packet.schema.json").read_text(
            encoding="utf-8"
        )
    )
    from review_contract import validate_schema

    for role_key in generator.ROLES:
        if role_key == "q4-closure-adjudication":
            continue
        packet = generator.build(TASK, role_key, "PRE_LLMAJ", "change", task_commit(repo))
        problems: list[str] = []
        validate_schema(packet, schema, role_key, problems)
        assert problems == []


def test_q4_closure_packet_requires_dedicated_generator() -> None:
    assert generator.ROLES["q4-closure-adjudication"]["role"] == "Q4 Closure Adjudicator"
    assert (CONTROL_PLANE / "new_q4_closure_packet.py").is_file()
    schema = json.loads(
        (CONTROL_PLANE / "agents" / "schemas" / "context_packet.schema.json").read_text(
            encoding="utf-8"
        )
    )
    closure_required = schema["allOf"][1]["then"]["required"]
    assert set(closure_required) == {
        "closure_policy_version",
        "boundary_adjudication",
        "final_q4_result",
        "repair_base_task_commit",
        "final_task_commit",
        "finding_fingerprints",
    }


def test_repeated_generation_uses_unique_immutable_review_ids(repo: Path) -> None:
    assert generator.main([TASK, "instruction"]) == 0
    assert generator.main([TASK, "instruction"]) == 0
    commit = task_commit(repo)
    packets = list((repo / ".terminus" / "reviews" / TASK / commit[:8]).glob("*.packet.json"))
    assert len(packets) == 2
    ids = {json.loads(path.read_text(encoding="utf-8"))["review_id"] for path in packets}
    assert len(ids) == 2


def test_role_contract_hash_changes_when_that_role_contract_changes(repo: Path) -> None:
    before = role_contract_hash(repo, "Instruction Reviewer")
    prompt = repo / ".terminus" / "agents" / "PROMPTS.md"
    text = prompt.read_text(encoding="utf-8")
    prompt.write_text(
        text.replace("Instruction contract A.", "Instruction contract B."), encoding="utf-8"
    )
    after = role_contract_hash(repo, "Instruction Reviewer")
    assert after != before


def test_unrelated_role_section_does_not_change_role_contract_hash(repo: Path) -> None:
    before = role_contract_hash(repo, "Instruction Reviewer")
    prompt = repo / ".terminus" / "agents" / "PROMPTS.md"
    text = prompt.read_text(encoding="utf-8")
    prompt.write_text(text.replace("Architect contract A.", "Architect contract B."), encoding="utf-8")
    after = role_contract_hash(repo, "Instruction Reviewer")
    assert after == before


def test_unknown_task_is_rejected(repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert generator.main(["missing-task", "instruction"]) == 2
    assert "no task at" in capsys.readouterr().out
