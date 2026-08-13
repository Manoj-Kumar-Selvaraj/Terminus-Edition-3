"""Resolve and validate immutable evidence references used by execution records."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
from pathlib import Path, PurePosixPath
from typing import Any, Mapping
from urllib.parse import unquote

_SHA = re.compile(r"^[0-9a-f]{40,64}$")
_SHA256 = re.compile(r"^sha256:[0-9a-f]{64}$")
_GIT_KINDS = frozenset(
    {"ARTIFACT", "PACKET", "RESULT", "FILE", "RUN", "EXTERNAL", "OTHER"}
)
_EXTERNAL_KINDS = frozenset({"ARTIFACT", "RUN", "EXTERNAL", "OTHER"})


class EvidenceReferenceVerifier:
    """Validate evidence references against Git objects or content-addressed identities."""

    def __init__(self, root: Path):
        self.root = root.resolve()

    def validate(self, value: Mapping[str, Any], index: int) -> dict[str, Any]:
        kind = value.get("kind")
        ref = value.get("ref")
        content_hash = value.get("content_hash")
        if not isinstance(kind, str) or not isinstance(ref, str):
            raise ValueError(f"evidence_refs[{index}] kind/ref are invalid")
        ref = ref.strip()
        if not ref:
            raise ValueError(f"evidence_refs[{index}] has invalid ref")
        if content_hash is not None and (
            not isinstance(content_hash, str) or not _SHA256.fullmatch(content_hash)
        ):
            raise ValueError(f"evidence_refs[{index}] has invalid content_hash")

        if ref.startswith("git:"):
            if kind not in _GIT_KINDS:
                raise ValueError(
                    f"evidence_refs[{index}] kind {kind} cannot use a git evidence reference"
                )
            return self._validate_git(kind, ref, content_hash, index)
        if ref.startswith("commit:"):
            if kind != "COMMIT":
                raise ValueError(
                    f"evidence_refs[{index}] commit reference requires kind COMMIT"
                )
            return self._validate_commit(ref, content_hash, index)
        if ref.startswith("run:") or ref.startswith("external:"):
            if kind not in _EXTERNAL_KINDS:
                raise ValueError(
                    f"evidence_refs[{index}] kind {kind} cannot use external evidence"
                )
            return self._validate_external(kind, ref, content_hash, index)
        raise ValueError(
            f"evidence_refs[{index}] must use git:, commit:, run:, or external: identity"
        )

    @staticmethod
    def is_resolved(value: Mapping[str, Any]) -> bool:
        """Return whether one ref resolves to immutable repository bytes/commit identity."""
        ref = value.get("ref")
        return isinstance(ref, str) and (
            ref.startswith("git:") or ref.startswith("commit:")
        )

    @staticmethod
    def identity(value: Mapping[str, Any]) -> str | None:
        """Return the exact identity carried by one validated evidence reference."""
        ref = value.get("ref")
        if not isinstance(ref, str):
            return None
        if ref.startswith("git:"):
            _location, marker, fragment = ref[len("git:") :].partition("#")
            return unquote(fragment).strip() if marker and fragment.strip() else None
        if ref.startswith("commit:"):
            value = ref[len("commit:") :].strip()
            return value if value else None
        if ref.startswith("run:") or ref.startswith("external:"):
            identity, _marker, _digest = ref.rpartition("#")
            _prefix, separator, rest = identity.partition(":")
            _provider, separator2, item_id = rest.partition(":")
            if separator and separator2 and item_id.strip():
                return item_id.strip()
        return None

    def _validate_git(
        self,
        kind: str,
        ref: str,
        content_hash: Any,
        index: int,
    ) -> dict[str, Any]:
        if not isinstance(content_hash, str):
            raise ValueError(f"evidence_refs[{index}] git evidence requires content_hash")
        body = ref[len("git:") :]
        location, separator, fragment = body.partition("#")
        commit, colon, encoded_path = location.partition(":")
        path = unquote(encoded_path)
        if not colon or not _SHA.fullmatch(commit) or not path:
            raise ValueError(f"evidence_refs[{index}] has invalid git reference")
        posix_path = PurePosixPath(path)
        if (
            path.startswith("/")
            or "\\" in path
            or any(part == ".." for part in posix_path.parts)
        ):
            raise ValueError(f"evidence_refs[{index}] git path is unsafe")
        if kind in {"RUN", "EXTERNAL"} and not (separator and fragment.strip()):
            raise ValueError(
                f"evidence_refs[{index}] git {kind.lower()} evidence requires identity fragment"
            )
        self._require_commit(commit, index)
        raw = subprocess.run(
            ["git", "-C", str(self.root), "show", f"{commit}:{path}"],
            check=False,
            capture_output=True,
        )
        if raw.returncode != 0:
            raise ValueError(f"evidence_refs[{index}] git object does not exist")
        actual = "sha256:" + hashlib.sha256(raw.stdout).hexdigest()
        if actual != content_hash:
            raise ValueError(f"evidence_refs[{index}] git content_hash mismatch")
        if separator and fragment:
            identity = unquote(fragment).strip()
            if not identity:
                raise ValueError(f"evidence_refs[{index}] has empty git identity fragment")
            if not self._contains_identity(raw.stdout, identity):
                raise ValueError(
                    f"evidence_refs[{index}] git artifact does not contain identity {identity}"
                )
        return {"kind": kind, "ref": ref, "content_hash": content_hash}

    def _validate_commit(
        self,
        ref: str,
        content_hash: Any,
        index: int,
    ) -> dict[str, Any]:
        commit = ref[len("commit:") :].strip()
        if not _SHA.fullmatch(commit):
            raise ValueError(f"evidence_refs[{index}] has invalid commit reference")
        self._require_commit(commit, index)
        expected = "sha256:" + hashlib.sha256(commit.encode("utf-8")).hexdigest()
        if content_hash is not None and content_hash != expected:
            raise ValueError(f"evidence_refs[{index}] commit content_hash mismatch")
        return {"kind": "COMMIT", "ref": ref, "content_hash": expected}

    @staticmethod
    def _validate_external(
        kind: str,
        ref: str,
        content_hash: Any,
        index: int,
    ) -> dict[str, Any]:
        """Validate a self-addressed external identity; it is not repository-resolved."""
        if not isinstance(content_hash, str):
            raise ValueError(
                f"evidence_refs[{index}] external evidence requires content_hash"
            )
        identity, marker, digest = ref.rpartition("#")
        if not marker or not identity or digest != content_hash:
            raise ValueError(
                f"evidence_refs[{index}] external ref must end with its content_hash"
            )
        prefix, separator, rest = identity.partition(":")
        provider, separator2, item_id = rest.partition(":")
        if (
            prefix not in {"run", "external"}
            or not separator
            or not separator2
            or not provider.strip()
            or not item_id.strip()
        ):
            raise ValueError(f"evidence_refs[{index}] has invalid external identity")
        return {"kind": kind, "ref": ref, "content_hash": content_hash}

    def _require_commit(self, commit: str, index: int) -> None:
        result = subprocess.run(
            ["git", "-C", str(self.root), "cat-file", "-e", f"{commit}^{{commit}}"],
            capture_output=True,
        )
        if result.returncode != 0:
            raise ValueError(f"evidence_refs[{index}] commit is not present in repository")

    @staticmethod
    def _contains_identity(raw: bytes, identity: str) -> bool:
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            return False
        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            return identity in text

        def walk(value: Any) -> bool:
            if isinstance(value, str):
                return value == identity
            if isinstance(value, Mapping):
                return any(walk(item) for item in value.values())
            if isinstance(value, list):
                return any(walk(item) for item in value)
            return False

        return walk(payload)
