from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any


def _collect_strings(value: Any) -> list[str]:
    if isinstance(value, str):
        text = value.strip()
        return [text] if text else []
    if isinstance(value, Mapping):
        collected: list[str] = []
        for key in sorted(value):
            collected.extend(_collect_strings(value[key]))
        return collected
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        collected = []
        for item in value:
            collected.extend(_collect_strings(item))
        return collected
    return []


def derive_human_writing_domain(task_id: str, inputs: Mapping[str, Any]) -> str:
    """Build a deterministic task-specific calibration query from solver-visible inputs."""
    required = inputs.get("required", {})
    source = {
        "task_id": task_id,
        "approved_work_package": required.get("APPROVED_WORK_PACKAGE", {}),
        "solver_visible_requirements": required.get("SOLVER_VISIBLE_REQUIREMENTS", {}),
    }
    parts = [task_id.replace("-", " "), *_collect_strings(source)]
    return " ".join(dict.fromkeys(part for part in parts if part.strip()))


def build_task_writing_profile(task_id: str, inputs: Mapping[str, Any]) -> dict[str, Any]:
    """Create a task-specific profile using only solver-visible request inputs."""
    required = inputs.get("required", {})
    work_package = required.get("APPROVED_WORK_PACKAGE", {})
    requirements = required.get("SOLVER_VISIBLE_REQUIREMENTS", {})
    must_preserve = list(
        dict.fromkeys(_collect_strings(work_package) + _collect_strings(requirements))
    )
    if not must_preserve:
        must_preserve = [f"solver-visible requirements for {task_id}"]
    return {
        "voice": "direct platform engineering change request",
        "structure": [
            "state the approved engineering objective first",
            "preserve exact public contracts and hard safety/state constraints",
            "reference solver-visible technical contracts instead of reproducing hidden verifier rows",
            "keep implementation-neutral observable outcomes",
        ],
        "must_preserve": must_preserve,
        "avoid": [
            "invented incidents or personal claims",
            "rubric-like hidden-test enumeration",
            "style-driven omission of lifecycle constraints",
            "copied distinctive source wording",
            "task details copied from unrelated calibration domains",
        ],
    }
