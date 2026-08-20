"""Durable, commit-bound human decisions for active Terminus task chats."""

from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path
from typing import Any, Mapping

_DECISION_ID_RE = re.compile(r"^hd_[0-9a-f]{64}$")
_TASK_RE = re.compile(r"^[A-Za-z0-9._-]+$")
_COMMIT_RE = re.compile(r"^[0-9a-f]{40,64}$")
_ALLOWED_AUTHORITY = "CHAT_HUMAN_APPROVAL"


def _canonical(value: Mapping[str, Any]) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _hash(prefix: str, value: Mapping[str, Any]) -> str:
    return prefix + hashlib.sha256(_canonical(value)).hexdigest()


def _require_text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a non-empty string")
    return value.strip()


class HumanDecisionStore:
    """Append-only human-decision ledger with deterministic outstanding decisions."""

    schema_version = "1.0"

    def __init__(self, root: Path):
        self.root = root.resolve()
        self.base = self.root / ".terminus" / "human-decisions"

    @staticmethod
    def decision_id_for(request: Mapping[str, Any]) -> str:
        identity = {
            "schema_version": "1.0",
            "task_id": request["task_id"],
            "task_commit": request["task_commit"],
            "stage": request["stage"],
            "decision_type": request["decision_type"],
            "allowed_decisions": list(request["allowed_decisions"]),
            "reason": request["reason"],
            "consequences": request["consequences"],
            "expires_if_task_commit_changes": bool(request["expires_if_task_commit_changes"]),
            "context": request.get("context", {}),
        }
        return _hash("hd_", identity)

    def request(
        self,
        *,
        task_id: str,
        task_commit: str,
        stage: str,
        decision_type: str,
        allowed_decisions: list[str],
        reason: str,
        consequences: str,
        context: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        if not _TASK_RE.fullmatch(task_id):
            raise ValueError("invalid task_id")
        if not _COMMIT_RE.fullmatch(task_commit):
            raise ValueError("task_commit must be an exact hexadecimal commit")
        stage = _require_text(stage, "stage")
        decision_type = _require_text(decision_type, "decision_type")
        reason = _require_text(reason, "reason")
        consequences = _require_text(consequences, "consequences")
        if not isinstance(allowed_decisions, list) or len(allowed_decisions) < 2:
            raise ValueError("allowed_decisions must contain at least two choices")
        normalized = [_require_text(item, "allowed_decision") for item in allowed_decisions]
        if len(set(normalized)) != len(normalized):
            raise ValueError("allowed_decisions must be unique")
        request: dict[str, Any] = {
            "schema_version": self.schema_version,
            "event_type": "HUMAN_DECISION_REQUEST",
            "task_id": task_id,
            "task_commit": task_commit,
            "stage": stage,
            "decision_type": decision_type,
            "allowed_decisions": normalized,
            "reason": reason,
            "consequences": consequences,
            "expires_if_task_commit_changes": True,
            "context": dict(context or {}),
        }
        request["decision_id"] = self.decision_id_for(request)
        existing = self.get(request["decision_id"])
        if existing is not None:
            if existing["request"] != request:
                raise ValueError("decision_id collision with different request")
            return existing
        event = {"sequence": self._next_sequence(task_id), "request": request, "resolution": None}
        self._append(task_id, event)
        return event

    def resolve(
        self,
        *,
        decision_id: str,
        decision: str,
        response_text: str,
        source: str = "ACTIVE_TASK_CHAT",
    ) -> dict[str, Any]:
        if not _DECISION_ID_RE.fullmatch(decision_id):
            raise ValueError("invalid decision_id")
        current = self.get(decision_id)
        if current is None:
            raise ValueError("human decision request does not exist")
        if current.get("resolution") is not None:
            raise ValueError("human decision is already resolved")
        request = current["request"]
        decision = _require_text(decision, "decision")
        if decision not in request["allowed_decisions"]:
            raise ValueError("decision is not allowed for this request")
        if source != "ACTIVE_TASK_CHAT":
            raise ValueError("chat human approval must originate from ACTIVE_TASK_CHAT")
        response_text = _require_text(response_text, "response_text")
        resolution = {
            "schema_version": self.schema_version,
            "event_type": "HUMAN_DECISION_RESOLUTION",
            "decision_id": decision_id,
            "task_id": request["task_id"],
            "task_commit": request["task_commit"],
            "stage": request["stage"],
            "decision_type": request["decision_type"],
            "decision": decision,
            "authority": {
                "type": _ALLOWED_AUTHORITY,
                "source": source,
                "response_sha256": hashlib.sha256(response_text.encode("utf-8")).hexdigest(),
            },
        }
        event = {
            "sequence": self._next_sequence(request["task_id"]),
            "request": request,
            "resolution": resolution,
        }
        self._append(request["task_id"], event)
        return event

    def get(self, decision_id: str) -> dict[str, Any] | None:
        if not _DECISION_ID_RE.fullmatch(decision_id):
            return None
        latest: dict[str, Any] | None = None
        if not self.base.exists():
            return None
        for ledger in sorted(self.base.glob("*/ledger.jsonl")):
            for event in self._load_ledger(ledger):
                request = event.get("request")
                if isinstance(request, Mapping) and request.get("decision_id") == decision_id:
                    latest = event
        return latest

    def outstanding(self, *, task_id: str, task_commit: str | None = None) -> list[dict[str, Any]]:
        ledger = self._ledger(task_id)
        if not ledger.exists():
            return []
        by_id: dict[str, dict[str, Any]] = {}
        for event in self._load_ledger(ledger):
            request = event.get("request")
            if not isinstance(request, Mapping):
                continue
            decision_id = request.get("decision_id")
            if isinstance(decision_id, str):
                by_id[decision_id] = event
        result: list[dict[str, Any]] = []
        for event in by_id.values():
            if event.get("resolution") is not None:
                continue
            request = event["request"]
            if task_commit is not None and request.get("task_commit") != task_commit:
                continue
            result.append(event)
        return sorted(result, key=lambda item: int(item["sequence"]))

    def require_resolved(
        self,
        *,
        decision_id: str,
        task_id: str,
        task_commit: str,
        stage: str,
        decision_type: str,
        accepted_decisions: set[str],
    ) -> dict[str, Any]:
        event = self.get(decision_id)
        if event is None or event.get("resolution") is None:
            raise ValueError("human decision is not resolved")
        request = event["request"]
        resolution = event["resolution"]
        if request.get("task_id") != task_id or resolution.get("task_id") != task_id:
            raise ValueError("human decision belongs to a different task")
        if request.get("task_commit") != task_commit or resolution.get("task_commit") != task_commit:
            raise ValueError("human decision is stale for the current task commit")
        if request.get("stage") != stage or resolution.get("stage") != stage:
            raise ValueError("human decision belongs to a different stage")
        if request.get("decision_type") != decision_type or resolution.get("decision_type") != decision_type:
            raise ValueError("human decision has the wrong decision type")
        if resolution.get("decision") not in accepted_decisions:
            raise ValueError("human decision does not authorize advancement")
        authority = resolution.get("authority")
        if not isinstance(authority, Mapping) or authority.get("type") != _ALLOWED_AUTHORITY:
            raise ValueError("human decision lacks CHAT_HUMAN_APPROVAL authority")
        if authority.get("source") != "ACTIVE_TASK_CHAT":
            raise ValueError("human decision is not bound to the active task chat")
        return event

    def _ledger(self, task_id: str) -> Path:
        if not _TASK_RE.fullmatch(task_id):
            raise ValueError("invalid task_id")
        return self.base / task_id / "ledger.jsonl"

    def _next_sequence(self, task_id: str) -> int:
        ledger = self._ledger(task_id)
        return len(self._load_ledger(ledger)) + 1 if ledger.exists() else 1

    def _load_ledger(self, path: Path) -> list[dict[str, Any]]:
        events: list[dict[str, Any]] = []
        if not path.exists():
            return events
        previous_hash = "GENESIS"
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            item = json.loads(line)
            if item.get("previous_event_hash") != previous_hash:
                raise ValueError("human decision ledger hash chain is invalid")
            supplied = item.get("event_hash")
            identity = dict(item)
            identity.pop("event_hash", None)
            actual = hashlib.sha256(_canonical(identity)).hexdigest()
            if supplied != actual:
                raise ValueError("human decision ledger event hash is invalid")
            previous_hash = supplied
            events.append(item)
        return events

    def _append(self, task_id: str, event: Mapping[str, Any]) -> None:
        ledger = self._ledger(task_id)
        ledger.parent.mkdir(parents=True, exist_ok=True)
        events = self._load_ledger(ledger)
        previous_hash = events[-1]["event_hash"] if events else "GENESIS"
        payload = dict(event)
        payload["previous_event_hash"] = previous_hash
        payload["event_hash"] = hashlib.sha256(_canonical(payload)).hexdigest()
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n"
        with ledger.open("a", encoding="utf-8") as handle:
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
