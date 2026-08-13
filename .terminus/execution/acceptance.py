"""Machine-checkable value predicates for stage advancement."""

from __future__ import annotations

import json
from collections.abc import Mapping as ABCMapping
from pathlib import Path
from typing import Any, Mapping


class StageAcceptancePredicates:
    """Validate status-specific acceptance predicates before ADVANCE is recorded."""

    version = "1.0"
    allowed_ops = frozenset(
        {
            "eq",
            "in",
            "empty",
            "nonempty",
            "length_eq",
            "lt",
            "lte",
            "gt",
            "gte",
            "all_gte",
            "eq_path",
        }
    )

    def __init__(self, root: Path):
        self.root = root.resolve()
        self.registry = self._load()
        self._validate_registry()

    def predicates_for(self, stage_id: str, status: str) -> list[dict[str, Any]]:
        stage = self.registry["stages"].get(stage_id, {})
        if not isinstance(stage, dict):
            raise ValueError(f"acceptance predicate stage {stage_id} must be an object")
        raw = stage.get(status, [])
        if not isinstance(raw, list):
            raise ValueError(f"acceptance predicates for {stage_id}/{status} must be an array")
        return [dict(item) for item in raw]

    def validate(self, stage_id: str, status: str, outputs: Mapping[str, Any]) -> None:
        """Raise ValueError when a declared advancement predicate is not satisfied."""
        for predicate in self.predicates_for(stage_id, status):
            path = str(predicate["path"])
            op = str(predicate["op"])
            observed = self._resolve(outputs, path)
            expected = predicate.get("value")
            if op == "eq_path":
                assert isinstance(expected, str)
                comparison = self._resolve(outputs, expected)
                passed = observed == comparison
                expected_display: Any = {"path": expected, "value": comparison}
            else:
                passed = self._evaluate(op, observed, expected)
                expected_display = expected
            if not passed:
                raise ValueError(
                    f"acceptance predicate failed for {stage_id}/{status}: "
                    f"{path} {op} {expected_display!r}; observed {observed!r}"
                )

    def _load(self) -> dict[str, Any]:
        path = self.root / ".terminus" / "agents" / "stage_acceptance_predicates.json"
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("stage_acceptance_predicates.json must contain one object")
        return payload

    def _validate_registry(self) -> None:
        if set(self.registry) != {"predicate_version", "stages"}:
            raise ValueError("acceptance predicate registry has unexpected top-level fields")
        if self.registry.get("predicate_version") != self.version:
            raise ValueError("unsupported acceptance predicate version")
        stages = self.registry.get("stages")
        if not isinstance(stages, dict):
            raise ValueError("acceptance predicate stages must be an object")
        for stage_id, statuses in stages.items():
            if not isinstance(stage_id, str) or not stage_id:
                raise ValueError("acceptance predicate stage IDs must be non-empty strings")
            if not isinstance(statuses, dict):
                raise ValueError(f"acceptance predicate stage {stage_id} must be an object")
            for status, predicates in statuses.items():
                if not isinstance(status, str) or not status:
                    raise ValueError("acceptance predicate statuses must be non-empty strings")
                if not isinstance(predicates, list):
                    raise ValueError(f"acceptance predicates for {stage_id}/{status} must be an array")
                for index, predicate in enumerate(predicates):
                    self._validate_predicate(stage_id, status, index, predicate)

    def _validate_predicate(
        self, stage_id: str, status: str, index: int, predicate: Any
    ) -> None:
        if not isinstance(predicate, dict):
            raise ValueError(
                f"acceptance predicate {stage_id}/{status}[{index}] must be an object"
            )
        if set(predicate) - {"path", "op", "value"}:
            raise ValueError(
                f"acceptance predicate {stage_id}/{status}[{index}] has unknown fields"
            )
        path = predicate.get("path")
        op = predicate.get("op")
        if not isinstance(path, str) or not path.strip():
            raise ValueError(
                f"acceptance predicate {stage_id}/{status}[{index}] requires path"
            )
        if op not in self.allowed_ops:
            raise ValueError(
                f"acceptance predicate {stage_id}/{status}[{index}] has invalid op"
            )
        if op in {
            "eq",
            "in",
            "length_eq",
            "lt",
            "lte",
            "gt",
            "gte",
            "all_gte",
            "eq_path",
        } and "value" not in predicate:
            raise ValueError(
                f"acceptance predicate {stage_id}/{status}[{index}] requires value"
            )
        if op == "in" and (
            not isinstance(predicate.get("value"), list) or not predicate["value"]
        ):
            raise ValueError(
                f"acceptance predicate {stage_id}/{status}[{index}] in-value must be non-empty"
            )
        if op == "length_eq" and (
            not isinstance(predicate.get("value"), int) or predicate["value"] < 0
        ):
            raise ValueError(
                f"acceptance predicate {stage_id}/{status}[{index}] length must be non-negative"
            )
        if op in {"lt", "lte", "gt", "gte", "all_gte"} and not self._is_number(
            predicate.get("value")
        ):
            raise ValueError(
                f"acceptance predicate {stage_id}/{status}[{index}] numeric op requires numeric value"
            )
        if op == "eq_path" and (
            not isinstance(predicate.get("value"), str) or not predicate["value"].strip()
        ):
            raise ValueError(
                f"acceptance predicate {stage_id}/{status}[{index}] eq_path requires a non-empty path"
            )

    @staticmethod
    def _resolve(outputs: Mapping[str, Any], path: str) -> Any:
        current: Any = outputs
        for part in path.split("."):
            if not isinstance(current, Mapping) or part not in current:
                raise ValueError(f"acceptance predicate path is missing: {path}")
            current = current[part]
        return current

    @classmethod
    def _evaluate(cls, op: str, observed: Any, expected: Any) -> bool:
        if op == "eq":
            return observed == expected
        if op == "in":
            return observed in expected
        if op == "empty":
            return observed in (None, False, "", [], {})
        if op == "nonempty":
            return observed not in (None, False, "", [], {})
        if op == "length_eq":
            try:
                return len(observed) == expected
            except TypeError:
                return False
        if op in {"lt", "lte", "gt", "gte"}:
            if not cls._is_number(observed) or not cls._is_number(expected):
                return False
            if op == "lt":
                return observed < expected
            if op == "lte":
                return observed <= expected
            if op == "gt":
                return observed > expected
            return observed >= expected
        if op == "all_gte":
            if isinstance(observed, ABCMapping):
                values = list(observed.values())
            elif isinstance(observed, (list, tuple, set, frozenset)):
                values = list(observed)
            else:
                return False
            return bool(values) and all(
                cls._is_number(item) and item >= expected for item in values
            )
        if op == "eq_path":
            raise ValueError("eq_path is evaluated against the complete output object")
        raise ValueError(f"unsupported acceptance predicate op: {op}")

    @staticmethod
    def _is_number(value: Any) -> bool:
        return isinstance(value, (int, float)) and not isinstance(value, bool)
