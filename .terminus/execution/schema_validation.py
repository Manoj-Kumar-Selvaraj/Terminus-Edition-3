"""Runtime JSON Schema validation for executor transport packets."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from jsonschema import Draft202012Validator


class ExecutorSchemaValidator:
    """Validate executor handoffs and StageResult envelopes against repo schemas."""

    def __init__(self, root: Path):
        self.root = root.resolve()
        self._handoff_schema = self._load(
            ".terminus/agents/schemas/executor_handoff.schema.json"
        )
        self._result_schema = self._load(
            ".terminus/agents/schemas/stage_result.schema.json"
        )
        self._handoff = Draft202012Validator(self._handoff_schema)
        self._result = Draft202012Validator(self._result_schema)

    def validate_handoff(self, value: Mapping[str, Any]) -> None:
        errors = sorted(self._handoff.iter_errors(dict(value)), key=lambda err: list(err.path))
        if errors:
            raise ValueError("executor handoff schema validation failed: " + errors[0].message)

    def validate_stage_result(self, value: Mapping[str, Any]) -> None:
        errors = sorted(self._result.iter_errors(dict(value)), key=lambda err: list(err.path))
        if errors:
            raise ValueError("stage result schema validation failed: " + errors[0].message)

    def _load(self, relative: str) -> dict[str, Any]:
        value = json.loads((self.root / relative).read_text(encoding="utf-8"))
        if not isinstance(value, dict):
            raise ValueError(f"schema must contain one object: {relative}")
        return value
