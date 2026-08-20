from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / ".github" / "chat_inline_stage_domain.py"
SPEC = importlib.util.spec_from_file_location("chat_inline_stage_domain", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def _inputs(objective: str, requirements: list[str]) -> dict[str, object]:
    return {
        "required": {
            "APPROVED_WORK_PACKAGE": {
                "ID": "TEST_PACKAGE",
                "ENGINEERING_OBJECTIVE": objective,
            },
            "SOLVER_VISIBLE_REQUIREMENTS": {
                "REQUIRED_END_STATE": requirements,
            },
            "CURRENT_TIME_BUDGET": {
                "enforcement": "ADVISORY_ONLY",
            },
        }
    }


def test_stonevault_domain_and_profile_do_not_inherit_terraform_ansible_details() -> None:
    inputs = _inputs(
        "Make StoneVault crash-safe across WAL replay and checkpoint recovery.",
        [
            "Committed deletes survive restart.",
            "Snapshots and WAL corruption fail closed.",
        ],
    )

    domain = MODULE.derive_human_writing_domain("stonevault-crash-safe-storage", inputs)
    profile = MODULE.build_task_writing_profile("stonevault-crash-safe-storage", inputs)
    rendered = f"{domain} {profile}".lower()

    assert "stonevault" in domain.lower()
    assert "wal" in domain.lower()
    assert "committed deletes survive restart" in rendered
    assert "terraform core" not in rendered
    assert "ansible mutation" not in rendered
    assert "ten documented resource interfaces" not in rendered


def test_task_specific_inputs_produce_distinct_calibration_domains() -> None:
    stonevault = _inputs("Crash-safe storage with WAL recovery.", ["Checkpoint safely."])
    terraform = _inputs(
        "Implement Terraform-managed Ansible resources.",
        ["Terraform Core remains durable state authority."],
    )

    stonevault_domain = MODULE.derive_human_writing_domain(
        "stonevault-crash-safe-storage", stonevault
    )
    terraform_domain = MODULE.derive_human_writing_domain(
        "terraform-ansible-managed-resources", terraform
    )

    assert stonevault_domain != terraform_domain
    assert "terraform" not in stonevault_domain.lower()
    assert "terraform" in terraform_domain.lower()
