#!/usr/bin/env python3
"""One-use asserted migration for PR #4. Deletes itself after applying."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def replace(relative: str, old: str, new: str) -> None:
    path = ROOT / relative
    text = path.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise SystemExit(
            f"{relative}: expected exactly one occurrence, found {count}: {old!r}"
        )
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


replace(
    ".terminus/reviewers/REVIEWER_CHECKLIST.md",
    "The existing local controller currently uses a custom five-run difficulty policy. Until those are reconciled, record a `POLICY_CONFLICT` rather than treating five runs as equivalent to the checklist's ten-run solvability definition.",
    "The local controller is now reconciled with this definition: GPT-5.5 ×5 plus Claude Opus 4.8 ×5 form the combined 10 official trials. A five-run suite is diagnostic only and must not be represented as the final ten-run solvability result. The 5-vs-10 question is therefore not a `POLICY_CONFLICT` by itself.",
)

replace(
    ".terminus/agents/CREATOR_PROMPTS.md",
    "For `large_system` tasks, numeric targets are authoring constraints, not permission to manufacture complexity. If the target cannot be met through meaningful system behavior, return `SCENARIO_TOO_SMALL` rather than pad the task.",
    "For `large_system_strict` tasks, numeric targets are hard authoring constraints in addition to structural-authenticity checks. If the target cannot be met through meaningful system behavior, return `SCENARIO_TOO_SMALL` rather than pad or silently downgrade the task. The legacy `large_system` profile uses numeric targets diagnostically only when the controller records why strict scale is inappropriate.",
)

replace(
    ".terminus/AGENT_SYSTEM.md",
    "For `large_system` and the explicit alias `large_system_strict`, the project-owner authoring requirements are hard constraints **and** structural authenticity must pass:",
    "For `large_system_strict`, the project-owner authoring requirements are hard constraints **and** structural authenticity must pass:",
)
replace(
    ".terminus/AGENT_SYSTEM.md",
    "A non-strict coupled-system profile may use scale numbers diagnostically only when the controller explicitly records why strict large-system scale is inappropriate. It must still pass structural authenticity.",
    "The legacy `large_system` profile may use scale numbers diagnostically only when the controller explicitly records why strict scale is inappropriate. New tasks requested to meet the large-system numbers must use `large_system_strict`. Both profiles still require structural authenticity.",
)

replace(
    ".terminus/validate_review_freshness.py",
    'return data.get("profile") == "large_system_strict"',
    'return data.get("profile") == "large_system_strict"',
)

workflow = ROOT / ".github/workflows/terminus-agent-system-ci.yml"
workflow_text = workflow.read_text(encoding="utf-8")
workflow_text = workflow_text.replace("permissions:\n  contents: write\n", "permissions:\n  contents: read\n", 1)
start = workflow_text.find("      # PR4_MIGRATION_BEGIN\n")
end_marker = "      # PR4_MIGRATION_END\n"
end = workflow_text.find(end_marker)
if start < 0 or end < 0 or end < start:
    raise SystemExit("terminus-agent-system-ci.yml: migration marker block not found")
end += len(end_marker)
workflow.write_text(workflow_text[:start] + workflow_text[end:], encoding="utf-8")

Path(__file__).unlink()
