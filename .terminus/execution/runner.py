"""Executor bridge runtime for manual-chat and isolated local-command surfaces."""

from __future__ import annotations

import hashlib
import json
import os
import signal
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any, Mapping, Sequence

from .executor import (
    ExecutorMode,
    canonical_json,
    stable_id,
    validate_stage_result_shape,
)
from .handoff import ExecutorHandoffBuilder
from .sandbox import LocalExecutorSandbox, SandboxProjection, SandboxUnavailable
from .schema_validation import ExecutorSchemaValidator

_MAX_STDOUT_BYTES = 1_048_576
_MAX_STDERR_BYTES = 262_144
_MAX_STDERR_CHARS = 4000
_ENV_ALLOWLIST = (
    "PATH",
    "LANG",
    "LC_ALL",
    "LC_CTYPE",
)


class ExecutorRunner:
    """Prepare or run executors without granting workflow-state authority."""

    schema_version = "1.0"

    def __init__(self, root: Path):
        self.root = root.resolve()
        self.handoffs = ExecutorHandoffBuilder(self.root)
        self.schemas = ExecutorSchemaValidator(self.root)

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
        env = dict(os.environ) if inherit_environment else self._minimal_environment()
        transport = json.dumps(handoff, ensure_ascii=False, sort_keys=True) + "\n"
        sandbox = LocalExecutorSandbox(self.root)
        projection: SandboxProjection | None = None

        try:
            projection = sandbox.prepare(invocation, argv_list)
            process = self._run_bounded(
                projection.wrapped_argv,
                transport,
                timeout_seconds=timeout_seconds,
                cwd=projection.workspace,
                env=env,
            )
        except SandboxUnavailable as exc:
            return self._runtime_response(
                handoff=handoff,
                attempt_id=attempt_id,
                status="SANDBOX_UNAVAILABLE",
                command_hash=command_hash,
                argv_count=len(argv_list),
                return_code=None,
                stderr=str(exc),
                stage_result=None,
                projection=None,
            )
        finally:
            sandbox.close()

        if process["status"] != "COMPLETED":
            return self._runtime_response(
                handoff=handoff,
                attempt_id=attempt_id,
                status=str(process["status"]),
                command_hash=command_hash,
                argv_count=len(argv_list),
                return_code=process["return_code"],
                stderr=str(process["stderr"]),
                stage_result=None,
                projection=projection,
            )
        if process["return_code"] != 0:
            return self._runtime_response(
                handoff=handoff,
                attempt_id=attempt_id,
                status="COMMAND_FAILED",
                command_hash=command_hash,
                argv_count=len(argv_list),
                return_code=process["return_code"],
                stderr=str(process["stderr"]),
                stage_result=None,
                projection=projection,
            )

        stdout = str(process["stdout"])
        try:
            parsed = json.loads(stdout)
        except json.JSONDecodeError as exc:
            return self._runtime_response(
                handoff=handoff,
                attempt_id=attempt_id,
                status="INVALID_RESULT",
                command_hash=command_hash,
                argv_count=len(argv_list),
                return_code=process["return_code"],
                stderr=f"executor stdout is not one JSON value: {exc}",
                stage_result=None,
                projection=projection,
            )
        if not isinstance(parsed, dict):
            return self._runtime_response(
                handoff=handoff,
                attempt_id=attempt_id,
                status="INVALID_RESULT",
                command_hash=command_hash,
                argv_count=len(argv_list),
                return_code=process["return_code"],
                stderr="executor stdout must be one StageResult JSON object",
                stage_result=None,
                projection=projection,
            )
        try:
            self.schemas.validate_stage_result(parsed)
            validate_stage_result_shape(
                parsed,
                invocation_id=str(invocation["invocation_id"]),
                handoff_id=str(handoff["handoff_id"]),
            )
            if parsed["output_task_commit"] != invocation["authority"]["task_commit"]:
                raise ValueError(
                    "LOCAL_COMMAND is read-only and must return the bound input task commit"
                )
        except ValueError as exc:
            return self._runtime_response(
                handoff=handoff,
                attempt_id=attempt_id,
                status="INVALID_RESULT",
                command_hash=command_hash,
                argv_count=len(argv_list),
                return_code=process["return_code"],
                stderr=str(exc),
                stage_result=None,
                projection=projection,
            )

        return self._runtime_response(
            handoff=handoff,
            attempt_id=attempt_id,
            status="EXECUTED",
            command_hash=command_hash,
            argv_count=len(argv_list),
            return_code=process["return_code"],
            stderr=str(process["stderr"]),
            stage_result=parsed,
            projection=projection,
        )

    def _run_bounded(
        self,
        argv: Sequence[str],
        input_text: str,
        *,
        timeout_seconds: int,
        cwd: Path,
        env: Mapping[str, str],
    ) -> dict[str, Any]:
        with tempfile.TemporaryFile() as stdin_file, tempfile.TemporaryFile() as stdout_file, tempfile.TemporaryFile() as stderr_file:
            stdin_file.write(input_text.encode("utf-8"))
            stdin_file.seek(0)
            process = subprocess.Popen(
                list(argv),
                stdin=stdin_file,
                stdout=stdout_file,
                stderr=stderr_file,
                cwd=cwd,
                env=dict(env),
                shell=False,
                start_new_session=True,
            )
            deadline = time.monotonic() + timeout_seconds
            status = "COMPLETED"
            reason = ""
            while process.poll() is None:
                stdout_size = os.fstat(stdout_file.fileno()).st_size
                stderr_size = os.fstat(stderr_file.fileno()).st_size
                if stdout_size > _MAX_STDOUT_BYTES:
                    status = "OUTPUT_LIMIT_EXCEEDED"
                    reason = "executor stdout exceeded 1 MiB transport limit"
                    self._kill_process_group(process)
                    break
                if stderr_size > _MAX_STDERR_BYTES:
                    status = "OUTPUT_LIMIT_EXCEEDED"
                    reason = "executor stderr exceeded 256 KiB diagnostic limit"
                    self._kill_process_group(process)
                    break
                if time.monotonic() >= deadline:
                    status = "TIMED_OUT"
                    reason = "executor exceeded timeout"
                    self._kill_process_group(process)
                    break
                time.sleep(0.02)
            process.wait()
            stdout_file.seek(0)
            stderr_file.seek(0)
            stdout = stdout_file.read(_MAX_STDOUT_BYTES + 1).decode("utf-8", errors="replace")
            stderr = stderr_file.read(_MAX_STDERR_BYTES + 1).decode("utf-8", errors="replace")
            if reason:
                stderr = reason + ("; " + stderr if stderr else "")
            return {
                "status": status,
                "return_code": process.returncode,
                "stdout": stdout,
                "stderr": self._clip(stderr),
            }

    @staticmethod
    def _kill_process_group(process: subprocess.Popen[bytes]) -> None:
        if process.poll() is not None:
            return
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except (ProcessLookupError, PermissionError):
            process.kill()

    @staticmethod
    def _minimal_environment() -> dict[str, str]:
        return {
            key: value
            for key in _ENV_ALLOWLIST
            if (value := os.environ.get(key)) is not None
        }

    @staticmethod
    def _clip(value: Any) -> str:
        text = "" if value is None else str(value)
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
        projection: SandboxProjection | None,
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
            "sandbox": None
            if projection is None
            else {
                "backend": projection.backend,
                "read_only": True,
                "authoritative_repository_mounted": False,
                "projection_sha256": projection.projection_hash,
                "authorized_file_count": projection.authorized_file_count,
            },
            "return_code": return_code,
            "stderr_summary": self._clip(stderr),
            "stage_result": dict(stage_result) if stage_result is not None else None,
            "recorded": False,
            "workflow_state_mutated": False,
        }
