from __future__ import annotations

import hashlib
import subprocess
import sys
from pathlib import Path
from urllib.parse import quote

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / ".terminus"))

from execution.evidence_refs import EvidenceReferenceVerifier  # noqa: E402

_FIXTURE = ".terminus/tests/fixtures/record_reference_ids.json"


def _git(*args: str, text: bool = True):
    return subprocess.run(
        ["git", "-C", str(ROOT), *args],
        check=True,
        capture_output=True,
        text=text,
    ).stdout


def _ref(kind: str, identity: str) -> dict[str, str]:
    commit = str(_git("rev-parse", "HEAD")).strip()
    raw = _git("show", f"{commit}:{_FIXTURE}", text=False)
    return {
        "kind": kind,
        "ref": f"git:{commit}:{_FIXTURE}#{quote(identity, safe='')}",
        "content_hash": "sha256:" + hashlib.sha256(raw).hexdigest(),
    }


def test_repository_reference_matches_bytes_and_identity() -> None:
    verifier = EvidenceReferenceVerifier(ROOT)
    value = verifier.validate(_ref("RESULT", "q4-review"), 0)
    assert verifier.is_resolved(value)
    assert verifier.identity(value) == "q4-review"


def test_repository_reference_checks_hash_and_identity() -> None:
    verifier = EvidenceReferenceVerifier(ROOT)
    wrong = _ref("RESULT", "q4-review")
    wrong["content_hash"] = "sha256:" + ("0" * 64)
    with pytest.raises(ValueError, match="content_hash mismatch"):
        verifier.validate(wrong, 0)

    absent = _ref("RESULT", "reference-not-present")
    with pytest.raises(ValueError, match="does not contain identity"):
        verifier.validate(absent, 0)


def test_external_reference_remains_non_repository_reference() -> None:
    verifier = EvidenceReferenceVerifier(ROOT)
    digest = "sha256:" + hashlib.sha256(b"external-record").hexdigest()
    value = verifier.validate(
        {
            "kind": "RUN",
            "ref": f"run:test:harbor-run-1#{digest}",
            "content_hash": digest,
        },
        0,
    )
    assert verifier.identity(value) == "harbor-run-1"
    assert not verifier.is_resolved(value)
