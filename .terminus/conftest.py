from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path
from urllib.parse import quote

import pytest

import retrieval.policy as retrieval_policy

ROOT = Path(__file__).resolve().parent.parent
_RECORD_REFERENCE_FIXTURE = ".terminus/tests/fixtures/record_reference_ids.json"
_PRODUCER_LINEAGE_FIXTURE = "execution-record-test/lineage-fixture.txt"


def _git(*args: str, text: bool = True):
    return subprocess.run(
        ["git", "-C", str(ROOT), *args],
        check=True,
        capture_output=True,
        text=text,
    ).stdout


def _resolved_test_ref(kind: str, identity: str) -> dict[str, str]:
    commit = str(_git("rev-parse", "HEAD")).strip()
    raw = _git("show", f"{commit}:{_RECORD_REFERENCE_FIXTURE}", text=False)
    digest = "sha256:" + hashlib.sha256(raw).hexdigest()
    return {
        "kind": kind,
        "ref": (
            f"git:{commit}:{_RECORD_REFERENCE_FIXTURE}#"
            f"{quote(identity, safe='')}"
        ),
        "content_hash": digest,
    }


def _patch_producer_lineage_fixture(
    request: pytest.FixtureRequest,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Separate task lineage from the synthetic PR merge-head control plane."""
    module = request.module
    merge_head = str(_git("rev-parse", "HEAD")).strip()
    fixture_commit = str(
        _git("log", "-1", "--format=%H", "--", _PRODUCER_LINEAGE_FIXTURE)
    ).strip()
    fixture_parent = str(_git("rev-parse", f"{fixture_commit}^")).strip()
    original_git = module._git

    def test_git(*args: str) -> str:
        if args == ("rev-parse", "HEAD^"):
            return fixture_parent
        return original_git(*args)

    def test_head() -> str:
        return fixture_commit

    def test_invocation(
        stage_id: str,
        *,
        task_commit: str | None = None,
    ) -> dict[str, object]:
        policy = module.RetrievalPolicy(ROOT)
        role_id = module.ExecutionAuthority(policy).primary_role_for_stage(stage_id)
        stage = policy.stages[stage_id]
        inputs = {
            str(field): {"ref": f"test:{field}"}
            for field in stage["input_contract"]["required_fields"]
        }
        return module.StageInvocationBuilder(ROOT, policy).build(
            module.InvocationContext(
                stage_id=stage_id,
                role_id=role_id,
                task_id="execution-record-test",
                task_commit=task_commit or fixture_commit,
                control_plane_commit=merge_head,
            ),
            inputs,
        )

    monkeypatch.setattr(module, "_git", test_git)
    monkeypatch.setattr(module, "_head", test_head)
    monkeypatch.setattr(module, "_invocation", test_invocation)


@pytest.fixture(autouse=True)
def _control_plane_test_compatibility(
    request: pytest.FixtureRequest,
    monkeypatch: pytest.MonkeyPatch,
):
    if request.node.name == "test_review_result_is_current_packet_bound_evidence":
        monkeypatch.setattr(
            retrieval_policy,
            "current_role_contract_hash",
            lambda _root, _role: "role-contract-hash",
        )
    if request.module.__name__.endswith("test_execution_record"):
        monkeypatch.setattr(request.module, "_eref", _resolved_test_ref)
    if request.node.name == "test_producer_may_advance_task_commit_on_descendant_lineage":
        _patch_producer_lineage_fixture(request, monkeypatch)
    yield
