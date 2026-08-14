"""Append-only durable registries for feedback and learned artifacts."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any, Iterable, Mapping

from .model import canonical_json, content_hash


class AppendOnlyRegistry:
    """Small JSONL registry with a tamper-evident hash chain."""

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
        for lineno, line in enumerate(self.path.read_text(encoding="utf-8").splitlines(), start=1):
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


class LearningStore:
    """Named registries used by the unified feedback plane."""

    def __init__(self, root: Path, state_root: Path | None = None):
        base = state_root or root / ".terminus" / "learning" / "state"
        self.feedback = AppendOnlyRegistry(base / "feedback.jsonl")
        self.findings = AppendOnlyRegistry(base / "findings.jsonl")
        self.lessons = AppendOnlyRegistry(base / "lessons.jsonl")
        self.patterns = AppendOnlyRegistry(base / "patterns.jsonl")
        self.remediations = AppendOnlyRegistry(base / "remediations.jsonl")

    def heads(self) -> dict[str, str]:
        return {
            "feedback": self.feedback.head(),
            "findings": self.findings.head(),
            "lessons": self.lessons.head(),
            "patterns": self.patterns.head(),
            "remediations": self.remediations.head(),
        }
