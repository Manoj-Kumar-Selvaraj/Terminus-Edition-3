from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path
from urllib.parse import quote

import pytest

import retrieval.policy as retrieval_policy

ROOT = Path(__file__).resolve().parent.parent
_RECORD_REFERENCE_FIXTURE = ".terminus/tests/fixtures/record_reference_ids.json"


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
    yield
