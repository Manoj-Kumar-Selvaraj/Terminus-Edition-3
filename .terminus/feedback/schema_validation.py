"""Runtime JSON-schema validation for feedback, findings and learning artifacts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from jsonschema import Draft202012Validator

_SCHEMA_FILES = {
    "feedback": "feedback_event.schema.json",
    "finding": "finding.schema.json",
    "remediation": "remediation_packet.schema.json",
    "lesson": "lesson.schema.json",
    "pattern": "pattern.schema.json",
}


class LearningSchemaValidator:
    def __init__(self, root: Path):
        self.root = root.resolve()
        schema_root = self.root / ".terminus" / "agents" / "schemas"
        self.validators = {
            name: Draft202012Validator(
                json.loads((schema_root / filename).read_text(encoding="utf-8"))
            )
            for name, filename in _SCHEMA_FILES.items()
        }

    def validate(self, kind: str, value: Mapping[str, Any]) -> None:
        if kind not in self.validators:
            raise ValueError(f"unknown learning schema kind: {kind}")
        errors = sorted(self.validators[kind].iter_errors(dict(value)), key=lambda e: list(e.path))
        if errors:
            details = "; ".join(
                f"{'.'.join(str(p) for p in error.path) or '<root>'}: {error.message}"
                for error in errors[:8]
            )
            raise ValueError(f"{kind} schema validation failed: {details}")
