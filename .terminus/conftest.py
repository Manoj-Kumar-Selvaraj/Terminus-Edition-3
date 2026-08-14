from __future__ import annotations

import hashlib
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from urllib.parse import quote

import pytest

import retrieval.policy as retrieval_policy

ROOT = Path(__file__).resolve().parent.parent
_RECORD_REFERENCE_FIXTURE = ".terminus/tests/fixtures/record_reference_ids.json"
_PRODUCER_LINEAGE_FIXTURE = "execution-record-test/lineage-fixture.txt"
_AUTHORITY_ISSUERS = (
    "terminus-human-authority",
    "terminus-automation-authority",
    "terminus-review-authority",
    "terminus-execution-authority",
    "terminus-learning-authority",
)
_AUTHORITY_TMP = tempfile.TemporaryDirectory(prefix="terminus-authority-tests-")
_AUTHORITY_ROOT = Path(_AUTHORITY_TMP.name)
_AUTHORITY_KEY = _AUTHORITY_ROOT / "test-authority"
subprocess.run(
    ["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-f", str(_AUTHORITY_KEY)],
    check=True,
    capture_output=True,
)
_public_key = _AUTHORITY_KEY.with_suffix(".pub").read_text(encoding="utf-8").strip()
_public_material = " ".join(_public_key.split()[:2])
_ALLOWED_SIGNERS = _AUTHORITY_ROOT / "allowed_signers"
_ALLOWED_SIGNERS.write_text(
    "\n".join(f"{issuer} {_public_material}" for issuer in _AUTHORITY_ISSUERS) + "\n",
    encoding="utf-8",
)
os.environ["TERMINUS_AUTHORITY_ALLOWED_SIGNERS"] = str(_ALLOWED_SIGNERS)
os.environ["TERMINUS_TEST_AUTHORITY_PRIVATE_KEY"] = str(_AUTHORITY_KEY)
sys.path.insert(0, str(ROOT / ".terminus" / "tests"))

from authority_helpers import sign_receipt  # noqa: E402
from feedback.ingestion import FeedbackIngestor  # noqa: E402
from feedback.model import FeedbackSource, Severity  # noqa: E402


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
        "ref": f"git:{commit}:{_RECORD_REFERENCE_FIXTURE}#{quote(identity, safe='')}",
        "content_hash": digest,
    }


def _policy_conflict_value() -> dict[str, object]:
    source = ".terminus/agents/PROTOCOL.md"
    text = (ROOT / source).read_text(encoding="utf-8")
    decision_key = "RULE_RESOLUTION_ACTION"
    entries = [
        (
            "packet-authenticity",
            "Hand-written packets are not acceptance evidence.",
            "REJECT_HAND_WRITTEN_PACKET",
        ),
        (
            "stale-review",
            "`STALE` is never PASS.",
            "REJECT_STALE_REVIEW",
        ),
    ]
    rules: list[dict[str, object]] = []
    for rule_id, rule_text, required_value in entries:
        assert rule_text in text
        rules.append(
            {
                "source": source,
                "source_commit": str(_git("rev-parse", "HEAD")).strip(),
                "rule_id": rule_id,
                "rule_text": rule_text,
                "rule_hash": "sha256:" + hashlib.sha256(rule_text.encode("utf-8")).hexdigest(),
                "decision_key": decision_key,
                "required_value": required_value,
            }
        )
    return {
        "affected_gate": "RULE_RESOLUTION",
        "decision_key": decision_key,
        "conflict_statement": "Authenticated semantic authority asserts mutually exclusive values for the same normalized decision.",
        "rules": rules,
    }


def _patch_producer_lineage_fixture(
    request: pytest.FixtureRequest,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = request.module
    merge_head = str(_git("rev-parse", "HEAD")).strip()
    fixture_commit = str(_git("log", "-1", "--format=%H", "--", _PRODUCER_LINEAGE_FIXTURE)).strip()
    fixture_parent = str(_git("rev-parse", f"{fixture_commit}^")).strip()
    original_git = module._git

    def test_git(*args: str) -> str:
        if args == ("rev-parse", "HEAD^"):
            return fixture_parent
        return original_git(*args)

    def test_head() -> str:
        return fixture_commit

    def test_invocation(stage_id: str, *, task_commit: str | None = None) -> dict[str, object]:
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


def _install_authenticated_human_fixture(
    request: pytest.FixtureRequest,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    name = request.node.name.lower()
    if name == "test_feedback_hash_binds_full_human_event" or any(
        marker in name for marker in ("unsigned", "unauthenticated", "human_asserted")
    ):
        return
    original = FeedbackIngestor.capture

    def capture(self: FeedbackIngestor, **kwargs):
        source_kind = FeedbackSource(kwargs.get("source_type"))
        if (
            source_kind is FeedbackSource.HUMAN_REVIEW
            and kwargs.get("authority_receipt") is None
            and kwargs.get("source_binding") is None
            and kwargs.get("captured_at")
        ):
            producer = str(kwargs["producer"]).strip()
            source: dict[str, object] = {"type": "HUMAN_REVIEW", "producer": producer}
            if kwargs.get("run_id") is not None:
                source["run_id"] = kwargs["run_id"]
            if kwargs.get("external_ref"):
                source["external_ref"] = kwargs["external_ref"]
            observation: dict[str, object] = {
                "severity": Severity(kwargs["severity"]).value,
                "message": str(kwargs["message"]).strip(),
            }
            for key in ("category", "stage_hint", "role_hint", "test_id", "metric"):
                if kwargs.get(key):
                    observation[key] = kwargs[key]
            if kwargs.get("value") is not None:
                observation["value"] = kwargs["value"]
            if kwargs.get("expected") is not None:
                observation["expected"] = kwargs["expected"]
            claim = FeedbackIngestor.authority_claim(
                source=source,
                task={"task_id": kwargs["task_id"], "task_commit": kwargs["task_commit"]},
                observation=observation,
                captured_at=str(kwargs["captured_at"]),
                source_binding=None,
            )
            kwargs["authority_receipt"] = sign_receipt(
                "HUMAN_FEEDBACK", f"human:{producer}", claim
            )
        return original(self, **kwargs)

    monkeypatch.setattr(FeedbackIngestor, "capture", capture)


@pytest.fixture(autouse=True)
def _control_plane_test_compatibility(
    request: pytest.FixtureRequest,
    monkeypatch: pytest.MonkeyPatch,
):
    _install_authenticated_human_fixture(request, monkeypatch)
    if hasattr(request.module, "_policy_conflict_value"):
        monkeypatch.setattr(request.module, "_policy_conflict_value", _policy_conflict_value)
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
