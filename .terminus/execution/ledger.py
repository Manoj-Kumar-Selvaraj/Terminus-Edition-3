"""Append-only hash-chained persistence for immutable Terminus execution records."""

from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path
from typing import Any, Mapping

_TASK_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
_RECORD_ID = re.compile(r"^rec_[0-9a-f]{64}$")
_INVOCATION_ID = re.compile(r"^inv_[0-9a-f]{64}$")
_EVENT_ID = re.compile(r"^evt_[0-9a-f]{64}$")
_SHA = re.compile(r"^[0-9a-f]{40,64}$")
_SHA256 = re.compile(r"^sha256:[0-9a-f]{64}$")


class ExecutionLedger:
    """Persist immutable canonical records and a deterministic append-only event chain."""

    schema_version = "1.0"

    def __init__(self, root: Path, task_id: str):
        self.root = root.resolve()
        self.task_id = self._validate_task_id(task_id)
        self.directory = self.root / ".terminus" / "executions" / self.task_id
        self.ledger_path = self.directory / "ledger.jsonl"

    @staticmethod
    def _validate_task_id(task_id: str) -> str:
        if not isinstance(task_id, str) or not _TASK_ID.fullmatch(task_id):
            raise ValueError("task_id must be a safe repository-local identifier")
        return task_id

    @staticmethod
    def _canonical_json(value: Mapping[str, Any]) -> bytes:
        return (
            json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
        ).encode("utf-8")

    @staticmethod
    def _compact_json(value: Mapping[str, Any]) -> str:
        return json.dumps(
            value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        )

    @staticmethod
    def _sha256(data: bytes) -> str:
        return "sha256:" + hashlib.sha256(data).hexdigest()

    @classmethod
    def _event_id(cls, payload: Mapping[str, Any]) -> str:
        return "evt_" + hashlib.sha256(
            cls._compact_json(payload).encode("utf-8")
        ).hexdigest()

    @staticmethod
    def _atomic_write(path: Path, data: bytes) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_name(path.name + ".tmp")
        tmp.write_bytes(data)
        os.replace(tmp, path)

    def record_path(self, invocation_id: str) -> Path:
        if not isinstance(invocation_id, str) or not _INVOCATION_ID.fullmatch(
            invocation_id
        ):
            raise ValueError("invalid invocation_id for execution record path")
        return self.directory / f"{invocation_id}.result.json"

    def append(self, record: Mapping[str, Any]) -> dict[str, Any]:
        """Persist one record only after full canonical invocation/result replay."""
        from .record import ExecutionRecordBuilder

        replayed = ExecutionRecordBuilder(self.root).validate_persisted_record(record)
        value = self._normalize_record(replayed)
        events = self.load(validate_record_files=True)
        for event in events:
            if event["record_id"] == value["record_id"]:
                expected_path = self._relative_record_path(value["invocation_id"])
                record_bytes = self._canonical_json(value)
                if (
                    event["record_path"] != expected_path
                    or event["record_hash"] != self._sha256(record_bytes)
                ):
                    raise ValueError(
                        "existing ledger event conflicts with record identity"
                    )
                return event

        record_path = self.record_path(value["invocation_id"])
        record_bytes = self._canonical_json(value)
        if record_path.exists():
            if record_path.read_bytes() != record_bytes:
                raise ValueError(
                    "immutable execution record path already contains different content"
                )
        else:
            self._atomic_write(record_path, record_bytes)

        lineage = value["task_lineage"]
        relative = self._relative_record_path(value["invocation_id"])
        payload: dict[str, Any] = {
            "schema_version": self.schema_version,
            "sequence": len(events) + 1,
            "previous_event_id": events[-1]["event_id"] if events else None,
            "record_id": value["record_id"],
            "invocation_id": value["invocation_id"],
            "stage_id": value["stage_id"],
            "task_id": self.task_id,
            "input_task_commit": lineage["input_task_commit"],
            "output_task_commit": lineage["output_task_commit"],
            "control_plane_commit": value["authority"]["control_plane_commit"],
            "record_path": relative,
            "record_hash": self._sha256(record_bytes),
        }
        event = {"event_id": self._event_id(payload), **payload}
        rendered_lines = [self._compact_json(item) for item in [*events, event]]
        self._atomic_write(
            self.ledger_path,
            ("\n".join(rendered_lines) + "\n").encode("utf-8"),
        )
        return event

    def load(self, *, validate_record_files: bool = True) -> list[dict[str, Any]]:
        if not self.ledger_path.exists():
            return []
        events: list[dict[str, Any]] = []
        seen_events: set[str] = set()
        seen_records: set[str] = set()
        for line_number, raw in enumerate(
            self.ledger_path.read_text(encoding="utf-8").splitlines(), start=1
        ):
            if not raw.strip():
                raise ValueError(f"blank execution-ledger line at {line_number}")
            try:
                value = json.loads(raw)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"invalid ledger JSON at line {line_number}"
                ) from exc
            if not isinstance(value, dict):
                raise ValueError(f"ledger line {line_number} must be an object")
            event = self._validate_event(value, line_number, events)
            if event["event_id"] in seen_events:
                raise ValueError("duplicate execution ledger event_id")
            if event["record_id"] in seen_records:
                raise ValueError("duplicate execution record_id in ledger")
            seen_events.add(event["event_id"])
            seen_records.add(event["record_id"])
            if validate_record_files:
                self._validate_record_reference(event)
            events.append(event)
        return events

    def _validate_event(
        self,
        value: Mapping[str, Any],
        line_number: int,
        prior: list[dict[str, Any]],
    ) -> dict[str, Any]:
        required = {
            "schema_version",
            "event_id",
            "sequence",
            "previous_event_id",
            "record_id",
            "invocation_id",
            "stage_id",
            "task_id",
            "input_task_commit",
            "output_task_commit",
            "control_plane_commit",
            "record_path",
            "record_hash",
        }
        if set(value) != required:
            raise ValueError(
                f"ledger line {line_number} fields differ from canonical event schema"
            )
        if value["schema_version"] != self.schema_version:
            raise ValueError("unsupported execution ledger schema_version")
        if value["task_id"] != self.task_id:
            raise ValueError("execution ledger task_id mismatch")
        if value["sequence"] != line_number:
            raise ValueError("execution ledger sequence is not contiguous")
        expected_previous = prior[-1]["event_id"] if prior else None
        if value["previous_event_id"] != expected_previous:
            raise ValueError("execution ledger previous_event_id chain is broken")
        if not isinstance(value["event_id"], str) or not _EVENT_ID.fullmatch(
            value["event_id"]
        ):
            raise ValueError("invalid execution ledger event_id")
        if not isinstance(value["record_id"], str) or not _RECORD_ID.fullmatch(
            value["record_id"]
        ):
            raise ValueError("invalid execution ledger record_id")
        if not isinstance(
            value["invocation_id"], str
        ) or not _INVOCATION_ID.fullmatch(value["invocation_id"]):
            raise ValueError("invalid execution ledger invocation_id")
        if not isinstance(value["stage_id"], str) or not value["stage_id"]:
            raise ValueError("invalid execution ledger stage_id")
        for key in (
            "input_task_commit",
            "output_task_commit",
            "control_plane_commit",
        ):
            if not isinstance(value[key], str) or not _SHA.fullmatch(value[key]):
                raise ValueError(f"invalid execution ledger {key}")
        expected_path = self._relative_record_path(value["invocation_id"])
        if value["record_path"] != expected_path:
            raise ValueError("execution ledger record_path is not canonical")
        if not isinstance(value["record_hash"], str) or not _SHA256.fullmatch(
            value["record_hash"]
        ):
            raise ValueError("invalid execution ledger record_hash")
        payload = dict(value)
        event_id = payload.pop("event_id")
        if event_id != self._event_id(payload):
            raise ValueError("execution ledger event_id hash mismatch")
        return dict(value)

    def _validate_record_reference(self, event: Mapping[str, Any]) -> None:
        from .record import ExecutionRecordBuilder

        path = (self.root / event["record_path"]).resolve()
        if self.root not in path.parents:
            raise ValueError("execution ledger record path escapes repository root")
        if not path.is_file():
            raise ValueError(
                f"execution ledger record is missing: {event['record_path']}"
            )
        raw = path.read_bytes()
        if self._sha256(raw) != event["record_hash"]:
            raise ValueError("execution ledger record content hash mismatch")
        try:
            value = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError("execution ledger record JSON is invalid") from exc
        if not isinstance(value, dict):
            raise ValueError("execution ledger record must be an object")
        value = ExecutionRecordBuilder(self.root).validate_persisted_record(value)
        if value.get("record_id") != event["record_id"]:
            raise ValueError("execution ledger event/record record_id mismatch")
        if value.get("invocation_id") != event["invocation_id"]:
            raise ValueError("execution ledger event/record invocation_id mismatch")
        if value.get("stage_id") != event["stage_id"]:
            raise ValueError("execution ledger event/record stage_id mismatch")
        authority = value.get("authority")
        lineage = value.get("task_lineage")
        if not isinstance(authority, dict) or not isinstance(lineage, dict):
            raise ValueError("execution record authority/task_lineage is invalid")
        if authority.get("task_id") != self.task_id:
            raise ValueError("execution record task_id does not match ledger")
        if lineage.get("input_task_commit") != event["input_task_commit"]:
            raise ValueError(
                "execution record input_task_commit does not match ledger"
            )
        if lineage.get("output_task_commit") != event["output_task_commit"]:
            raise ValueError(
                "execution record output_task_commit does not match ledger"
            )
        if authority.get("task_commit") != event["input_task_commit"]:
            raise ValueError(
                "execution record authority task_commit must equal ledger input_task_commit"
            )
        if authority.get("control_plane_commit") != event["control_plane_commit"]:
            raise ValueError(
                "execution record control_plane_commit does not match ledger"
            )

    def _normalize_record(self, record: Mapping[str, Any]) -> dict[str, Any]:
        try:
            value = json.loads(
                json.dumps(
                    record,
                    sort_keys=True,
                    separators=(",", ":"),
                    ensure_ascii=False,
                )
            )
        except (TypeError, ValueError) as exc:
            raise ValueError("execution record must be JSON-compatible") from exc
        if not isinstance(value, dict):
            raise ValueError("execution record must be one object")
        record_id = value.get("record_id")
        invocation_id = value.get("invocation_id")
        stage_id = value.get("stage_id")
        authority = value.get("authority")
        lineage = value.get("task_lineage")
        if not isinstance(record_id, str) or not _RECORD_ID.fullmatch(record_id):
            raise ValueError("execution record has invalid record_id")
        if not isinstance(invocation_id, str) or not _INVOCATION_ID.fullmatch(
            invocation_id
        ):
            raise ValueError("execution record has invalid invocation_id")
        if not isinstance(stage_id, str) or not stage_id:
            raise ValueError("execution record has invalid stage_id")
        if not isinstance(authority, dict) or not isinstance(lineage, dict):
            raise ValueError(
                "execution record has invalid authority/task_lineage"
            )
        if authority.get("task_id") != self.task_id:
            raise ValueError(
                "durable task ledger requires matching record authority.task_id"
            )
        input_commit = lineage.get("input_task_commit")
        output_commit = lineage.get("output_task_commit")
        control_commit = authority.get("control_plane_commit")
        for label, commit in (
            ("input_task_commit", input_commit),
            ("output_task_commit", output_commit),
            ("control_plane_commit", control_commit),
        ):
            if not isinstance(commit, str) or not _SHA.fullmatch(commit):
                raise ValueError(f"durable task ledger requires exact {label}")
        if authority.get("task_commit") != input_commit:
            raise ValueError(
                "record authority.task_commit must equal task_lineage.input_task_commit"
            )
        changed = lineage.get("task_changed")
        if not isinstance(changed, bool) or changed != (
            input_commit != output_commit
        ):
            raise ValueError(
                "task_lineage.task_changed is inconsistent with commit lineage"
            )
        return value

    def _relative_record_path(self, invocation_id: str) -> str:
        return f".terminus/executions/{self.task_id}/{invocation_id}.result.json"
