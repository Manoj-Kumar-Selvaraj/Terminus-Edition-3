"""Append-only durable registries for feedback and learned artifacts."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any, Iterable, Mapping

from .model import canonical_json, content_hash


class AppendOnlyRegistry:
    """Small JSONL registry with a tamper-evident hash chain.

    This primitive is persistence only. Semantic authority is intentionally
    supplied by typed control-plane components and revalidated by consumers.
    LearningStore therefore exposes read-only views rather than these writable
    registry objects.
    """

    def __init__(self, path: Path):
        self.path = path

    def read(self) -> list[dict[str, Any]]:
        return [row["payload"] for row in self._verified_rows()]

    def read_through(self, chain_head: str) -> list[dict[str, Any]]:
        if chain_head == "GENESIS":
            return []
        selected: list[dict[str, Any]] = []
        for row in self._verified_rows():
            selected.append(row["payload"])
            if row["chain_hash"] == chain_head:
                return selected
        raise ValueError(f"registry chain head is unavailable: {chain_head}")

    def head(self) -> str:
        rows = self._verified_rows()
        return str(rows[-1]["chain_hash"]) if rows else "GENESIS"

    def latest_by(
        self, identity_field: str, *, chain_head: str | None = None
    ) -> list[dict[str, Any]]:
        latest: dict[str, dict[str, Any]] = {}
        order: list[str] = []
        payloads = self.read() if chain_head is None else self.read_through(chain_head)
        for payload in payloads:
            identity = payload.get(identity_field)
            if not isinstance(identity, str) or not identity:
                raise ValueError(
                    f"registry payload missing identity field {identity_field}"
                )
            if identity not in latest:
                order.append(identity)
            latest[identity] = payload
        return [latest[identity] for identity in order]

    def get_latest(
        self, identity_field: str, identity: str, *, chain_head: str | None = None
    ) -> dict[str, Any] | None:
        payloads = self.read() if chain_head is None else self.read_through(chain_head)
        for payload in reversed(payloads):
            if payload.get(identity_field) == identity:
                return payload
        return None

    def append(self, payload: Mapping[str, Any]) -> str:
        rows = self._verified_rows()
        previous = rows[-1]["chain_hash"] if rows else "GENESIS"
        row = {
            "previous_chain_hash": previous,
            "payload": dict(payload),
        }
        row["chain_hash"] = content_hash(row)
        rows.append(row)
        self._replace(rows)
        return str(row["chain_hash"])

    def extend(self, values: Iterable[Mapping[str, Any]]) -> None:
        for value in values:
            self.append(value)

    def _verified_rows(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        rows: list[dict[str, Any]] = []
        previous = "GENESIS"
        for lineno, line in enumerate(
            self.path.read_text(encoding="utf-8").splitlines(), start=1
        ):
            if not line.strip():
                continue
            row = json.loads(line)
            if not isinstance(row, dict):
                raise ValueError(f"registry row {lineno} is not an object")
            if row.get("previous_chain_hash") != previous:
                raise ValueError(f"registry hash chain mismatch at line {lineno}")
            payload = row.get("payload")
            expected = content_hash(
                {"previous_chain_hash": previous, "payload": payload}
            )
            if row.get("chain_hash") != expected:
                raise ValueError(f"registry content hash mismatch at line {lineno}")
            if not isinstance(payload, dict):
                raise ValueError(f"registry payload {lineno} is not an object")
            rows.append(row)
            previous = expected
        return rows

    def _replace(self, rows: list[Mapping[str, Any]]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        serialized = "".join(canonical_json(row) + "\n" for row in rows)
        fd, temp_name = tempfile.mkstemp(
            prefix=self.path.name + ".", dir=str(self.path.parent)
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(serialized)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp_name, self.path)
        finally:
            if os.path.exists(temp_name):
                os.unlink(temp_name)


class ReadOnlyRegistry:
    """Read-only facade used by control-plane consumers.

    Deliberately omits append/extend so a caller holding LearningStore cannot
    turn hash-chain persistence into semantic transition authority.
    """

    def __init__(self, registry: AppendOnlyRegistry):
        self._registry = registry

    @property
    def path(self) -> Path:
        return self._registry.path

    def read(self) -> list[dict[str, Any]]:
        return self._registry.read()

    def read_through(self, chain_head: str) -> list[dict[str, Any]]:
        return self._registry.read_through(chain_head)

    def head(self) -> str:
        return self._registry.head()

    def latest_by(
        self, identity_field: str, *, chain_head: str | None = None
    ) -> list[dict[str, Any]]:
        return self._registry.latest_by(identity_field, chain_head=chain_head)

    def get_latest(
        self, identity_field: str, identity: str, *, chain_head: str | None = None
    ) -> dict[str, Any] | None:
        return self._registry.get_latest(
            identity_field, identity, chain_head=chain_head
        )


class LearningStore:
    """Private task feedback state plus portable generalized knowledge.

    Writable registries remain encapsulated. Typed control-plane components use
    the record_* methods below, while all ordinary consumers receive read-only
    registry views and must independently validate semantic authority.
    """

    def __init__(
        self,
        root: Path,
        state_root: Path | None = None,
        knowledge_root: Path | None = None,
    ):
        private = state_root or root / ".terminus" / "learning" / "state"
        knowledge = knowledge_root or root / ".terminus" / "learning" / "knowledge"
        self._feedback = AppendOnlyRegistry(private / "feedback.jsonl")
        self._findings = AppendOnlyRegistry(private / "findings.jsonl")
        self._remediations = AppendOnlyRegistry(private / "remediations.jsonl")
        self._lessons = AppendOnlyRegistry(knowledge / "lessons.jsonl")
        self._patterns = AppendOnlyRegistry(knowledge / "patterns.jsonl")
        self.feedback = ReadOnlyRegistry(self._feedback)
        self.findings = ReadOnlyRegistry(self._findings)
        self.remediations = ReadOnlyRegistry(self._remediations)
        self.lessons = ReadOnlyRegistry(self._lessons)
        self.patterns = ReadOnlyRegistry(self._patterns)

    def record_feedback(self, payload: Mapping[str, Any]) -> str:
        return self._feedback.append(payload)

    def record_finding(self, payload: Mapping[str, Any]) -> str:
        return self._findings.append(payload)

    def record_remediation(self, payload: Mapping[str, Any]) -> str:
        return self._remediations.append(payload)

    def record_lesson(self, payload: Mapping[str, Any]) -> str:
        return self._lessons.append(payload)

    def record_pattern(self, payload: Mapping[str, Any]) -> str:
        return self._patterns.append(payload)

    def heads(self) -> dict[str, str]:
        return {
            "feedback": self._feedback.head(),
            "findings": self._findings.head(),
            "lessons": self._lessons.head(),
            "patterns": self._patterns.head(),
            "remediations": self._remediations.head(),
        }
