"""Executor bridge runtime for manual-chat and shell-free local-command surfaces."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
from pathlib import Path
from typing import Any, Mapping, Sequence

from .executor import (
    ExecutorMode,
    canonical_json,
    stable_id,
    validate_stage_result_shape,
)
from .handoff import ExecutorHandoffBuilder

_MAX_STDOUT_BYTES = 1_048_576
_MAX_STDERR_CHARS = 4000
_ENV_ALLOWLIST = (
    "PATH",
    "PATHEXT",
    "SYSTEMROOT",
    "WINDIR",
    "HOME",
    "USERPROFILE",
    "TEMP",
    "TMP",
    "LANG",
    "LC_ALL",
)


class ExecutorRunner:
    """Prepare or run executors without mutating Terminus workflow state."""

    schema_version = "1.0"

    def __init__(self, root: Path):
        self.root = root.resolve()
        self.handoffs = ExecutorHandoffBuilder()

    def prepare(
        self,
        invocation: Mapping[str, Any],
        *,
        executor_mode: ExecutorMode | str = ExecutorMode.MANUAL_CHAT,
    ) -> dict[str, Any]:
        handoff = self.handoffs.build(invocation, executor_mode=executor_mode)
        return {
            "schema_version": self.schema_version,
            "status": "PREPARED",
            "executor_mode": handoff["executor_mode"],
            "handoff": handoff,
            "stage_result": None,
            "recorded": False,
            "workflow_state_mutated": False,
        }

    def run_local(
        self,
        invocation: Mapping[str, Any],
        argv: Sequence[str],
        *,
        timeout_seconds: int = 600,
        inherit_environment: bool = False,
    ) -> dict[str, Any]:
        if not argv or not all(isinstance(item, str) and item for item in argv):
            raise ValueError("LOCAL_COMMAND requires a non-empty argv sequence")
        if timeout_seconds <= 0:
            raise ValueError("LOCAL_COMMAND timeout_seconds must be positive")

        handoff = self.handoffs.build(
            invocation,
            executor_mode=ExecutorMode.LOCAL_COMMAND,
        )
        argv_list = list(argv)
        command_hash = hashlib.sha256(
            canonical_json(argv_list).encode("utf-8")
        ).hexdigest()
        attempt_payload = {
            "handoff_id": handoff["handoff_id"],
            "command_hash": command_hash,
            "timeout_seconds": timeout_seconds,
            "inherit_environment": inherit_environment,
        }
        attempt_id = stable_id("attempt", attempt_payload)
        env = None if inherit_environment else self._minimal_environment()
        transport = json.dumps(handoff, ensure_ascii=False, sort_keys=True) + "\n"

        try:
            completed = subprocess.run(
                argv_list,
                input=transport,
                text=True,
                capture_output=True,
                timeout=timeout_seconds,
                shell=False,
                cwd=self.root,
                env=env,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            return self._runtime_response(
                handoff=handoff,
                attempt_id=attempt_id,
                status="TIMED_OUT",
                command_hash=command_hash,
                argv_count=len(argv_list),
                return_code=None,
                stderr=self._clip(exc.stderr),
                stage_result=None,
            )

        stdout = completed.stdout or ""
        if len(stdout.encode("utf-8")) > _MAX_STDOUT_BYTES:
            return self._runtime_response(
                handoff=handoff,
                attempt_id=attempt_id,
                status="INVALID_RESULT",
                command_hash=command_hash,
                argv_count=len(argv_list),
                return_code=completed.returncode,
                stderr="executor stdout exceeded 1 MiB transport limit",
                stage_result=None,
            )
        if completed.returncode != 0:
            return self._runtime_response(
                handoff=handoff,
                attempt_id=attempt_id,
                status="COMMAND_FAILED",
                command_hash=command_hash,
                argv_count=len(argv_list),
                return_code=completed.returncode,
                stderr=self._clip(completed.stderr),
                stage_result=None,
            )

        try:
            parsed = json.loads(stdout)
        except json.JSONDecodeError as exc:
            return self._runtime_response(
                handoff=handoff,
                attempt_id=attempt_id,
                status="INVALID_RESULT",
                command_hash=command_hash,
                argv_count=len(argv_list),
                return_code=completed.returncode,
                stderr=f"executor stdout is not one JSON value: {exc}",
                stage_result=None,
            )
        if not isinstance(parsed, dict):
            return self._runtime_response(
                handoff=handoff,
                attempt_id=attempt_id,
                status="INVALID_RESULT",
                command_hash=command_hash,
                argv_count=len(argv_list),
                return_code=completed.returncode,
                stderr="executor stdout must be one StageResult JSON object",
                stage_result=None,
            )
        try:
            validate_stage_result_shape(
                parsed,
                invocation_id=str(invocation["invocation_id"]),
            )
        except ValueError as exc:
            return self._runtime_response(
                handoff=handoff,
                attempt_id=attempt_id,
                status="INVALID_RESULT",
                command_hash=command_hash,
                argv_count=len(argv_list),
                return_code=completed.returncode,
                stderr=str(exc),
                stage_result=None,
            )

        return self._runtime_response(
            handoff=handoff,
            attempt_id=attempt_id,
            status="EXECUTED",
            command_hash=command_hash,
            argv_count=len(argv_list),
            return_code=completed.returncode,
            stderr=self._clip(completed.stderr),
            stage_result=parsed,
        )

    @staticmethod
    def _minimal_environment() -> dict[str, str]:
        return {
            key: value
            for key in _ENV_ALLOWLIST
            if (value := os.environ.get(key)) is not None
        }

    @staticmethod
    def _clip(value: Any) -> str:
        if value is None:
            return ""
        if isinstance(value, bytes):
            text = value.decode("utf-8", errors="replace")
        else:
            text = str(value)
        if len(text) <= _MAX_STDERR_CHARS:
            return text
        return text[:_MAX_STDERR_CHARS] + "...[truncated]"

    def _runtime_response(
        self,
        *,
        handoff: Mapping[str, Any],
        attempt_id: str,
        status: str,
        command_hash: str,
        argv_count: int,
        return_code: int | None,
        stderr: str,
        stage_result: Mapping[str, Any] | None,
    ) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "attempt_id": attempt_id,
            "status": status,
            "executor_mode": ExecutorMode.LOCAL_COMMAND.value,
            "handoff_id": handoff["handoff_id"],
            "invocation_id": handoff["invocation_id"],
            "command": {
                "sha256": command_hash,
                "argv_count": argv_count,
                "shell": False,
            },
            "return_code": return_code,
            "stderr_summary": stderr,
            "stage_result": dict(stage_result) if stage_result is not None else None,
            "recorded": False,
            "workflow_state_mutated": False,
        }
