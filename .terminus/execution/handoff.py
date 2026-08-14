"""Build deterministic executor handoffs from canonically authorized invocations."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from .executor import ExecutorMode, canonical_json, validate_executable_invocation
from .handoff_contract import handoff_id, identity_packet
from .invocation_guard import CanonicalInvocationGuard
from .schema_validation import ExecutorSchemaValidator


class ExecutorHandoffBuilder:
    """Project one canonical invocation into a bounded executor-neutral handoff."""

    schema_version = "1.0"

    def __init__(self, root: Path | None = None):
        self.root = (root or Path(__file__).resolve().parents[2]).resolve()
        self.guard = CanonicalInvocationGuard(self.root)
        self.schemas = ExecutorSchemaValidator(self.root)

    def build(
        self,
        invocation: Mapping[str, Any],
        *,
        executor_mode: ExecutorMode | str,
    ) -> dict[str, Any]:
        canonical = self.guard.validate(invocation)
        validate_executable_invocation(canonical)
        mode = ExecutorMode(executor_mode)
        packet = identity_packet(canonical, mode)
        packet["handoff_id"] = handoff_id(canonical, mode)
        self.schemas.validate_handoff(packet)
        return packet

    @staticmethod
    def identity_payload(packet: Mapping[str, Any]) -> str:
        copy = dict(packet)
        copy.pop("handoff_id", None)
        return canonical_json(copy)
