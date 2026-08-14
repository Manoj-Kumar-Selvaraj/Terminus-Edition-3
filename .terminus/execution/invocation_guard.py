"""Pre-execution canonical invocation authorization for executor handoffs."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from .record import ExecutionRecordBuilder


class CanonicalInvocationGuard:
    """Reuse the recorder's canonical invocation validation before execution.

    This class deliberately exposes validation only. It never builds execution
    records, writes ledgers, or resolves workflow state.
    """

    def __init__(self, root: Path):
        self.root = root.resolve()
        self._recorder = ExecutionRecordBuilder(self.root)

    def validate(self, invocation: Mapping[str, Any]) -> dict[str, Any]:
        """Return the canonicalized READY invocation or fail closed."""

        return self._recorder._validate_invocation(invocation)
