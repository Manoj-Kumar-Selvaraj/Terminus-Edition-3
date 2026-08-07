from __future__ import annotations

import os
import pathlib
import signal
import subprocess
import time
from collections.abc import Callable, Iterator
from dataclasses import dataclass

import pytest


APP = pathlib.Path("/app/guardian")
BIN = APP / "bin"
GUARDIAN = BIN / "guardian"
CONTROL = BIN / "guardianctl"
WORKER = BIN / "guardian-worker"


@pytest.fixture(scope="session", autouse=True)
def native_build() -> None:
    """Rebuild the submitted native sources before exercising runtime behavior."""
    result = subprocess.run(
        [str(BIN / "build-guardian")],
        cwd=APP,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=180,
        check=False,
    )
    assert result.returncode == 0, result.stdout
    for executable in (GUARDIAN, CONTROL, WORKER):
        assert executable.is_file()
        assert executable.read_bytes()[:4] == b"\x7fELF"


def wait_until(
    predicate: Callable[[], object],
    *,
    timeout: float = 10.0,
    description: str = "condition",
) -> object:
    """Poll a state transition with a generous correctness timeout."""
    deadline = time.monotonic() + timeout
    last_error: BaseException | None = None
    while time.monotonic() < deadline:
        try:
            result = predicate()
            if result:
                return result
        except (FileNotFoundError, ConnectionError, subprocess.SubprocessError) as error:
            last_error = error
        time.sleep(0.02)
    detail = f"; last error: {last_error}" if last_error else ""
    raise AssertionError(f"timed out waiting for {description}{detail}")


def unit(
    name: str,
    *arguments: str,
    dependencies: tuple[str, ...] = (),
    restart: str = "never",
    restart_limit: int = 0,
    grace_ms: int = 100,
) -> str:
    """Render one public-contract manifest unit for a real worker process."""
    lines = [f"unit {name}", f"exec {WORKER}"]
    lines.extend(f"arg {argument}" for argument in arguments)
    lines.extend(f"depends {dependency}" for dependency in dependencies)
    lines.extend(
        [
            f"restart {restart}",
            f"restart-limit {restart_limit}",
            f"stop-grace-ms {grace_ms}",
            "end",
        ]
    )
    return "\n".join(lines) + "\n"


def write_manifest(path: pathlib.Path, *units: str) -> None:
    """Write a complete manifest with a stable final newline."""
    path.write_text("\n".join(units), encoding="utf-8")


def control(socket: pathlib.Path, command: str, *, uid: int | None = None) -> str:
    """Send a control packet, optionally under a different Unix identity."""
    argv = [str(CONTROL), str(socket), *command.split()]
    if uid is not None:
        argv = [
            "setpriv",
            f"--reuid={uid}",
            f"--regid={uid}",
            "--clear-groups",
            *argv,
        ]
    # Brief retries absorb transient peer-reset races under host load without
    # changing the public control contract the tests assert.
    last_stderr = ""
    for attempt in range(8):
        result = subprocess.run(
            argv,
            text=True,
            capture_output=True,
            timeout=5,
            check=False,
        )
        if result.returncode == 0:
            return result.stdout
        last_stderr = result.stderr
        if "Connection reset by peer" not in last_stderr and "Connection refused" not in last_stderr:
            break
        time.sleep(0.05 * (attempt + 1))
    assert False, last_stderr


def parse_status(text: str) -> dict[str, dict[str, str]]:
    """Decode the public status lines without depending on implementation layout."""
    units: dict[str, dict[str, str]] = {}
    for line in text.splitlines():
        fields = line.split("|")
        assert fields[0] == "UNIT", line
        values = dict(field.split("=", 1) for field in fields[1:])
        units[values["name"]] = values
    return units


@dataclass
class RunningGuardian:
    """Own a daemon process and its public runtime paths for one test."""

    manifest: pathlib.Path
    state: pathlib.Path
    process: subprocess.Popen[str]

    @property
    def socket(self) -> pathlib.Path:
        return self.state / "control.sock"

    def status(self) -> dict[str, dict[str, str]]:
        return parse_status(control(self.socket, "STATUS"))

    def shutdown(self) -> None:
        if self.process.poll() is not None:
            return
        try:
            control(self.socket, "SHUTDOWN")
            self.process.wait(timeout=8)
        except (AssertionError, subprocess.SubprocessError):
            self.process.send_signal(signal.SIGKILL)
            self.process.wait(timeout=3)


def launch(manifest: pathlib.Path, state: pathlib.Path) -> RunningGuardian:
    """Launch the real foreground supervisor and wait for its socket."""
    state.mkdir(parents=True, exist_ok=True)
    process = subprocess.Popen(
        [str(GUARDIAN), "run", str(manifest), str(state)],
        cwd=APP,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        start_new_session=True,
    )
    running = RunningGuardian(manifest, state, process)

    def available() -> bool:
        if process.poll() is not None:
            stdout, stderr = process.communicate()
            raise AssertionError(
                f"guardian exited {process.returncode}: {stdout}\n{stderr}"
            )
        return running.socket.exists() and bool(running.status())

    wait_until(available, description="guardian control socket")
    return running


@pytest.fixture
def guardians() -> Iterator[list[RunningGuardian]]:
    """Clean up every daemon started by a test, even after an assertion fails."""
    active: list[RunningGuardian] = []
    yield active
    for guardian in reversed(active):
        guardian.shutdown()
        if guardian.process.stdout:
            guardian.process.stdout.close()
        if guardian.process.stderr:
            guardian.process.stderr.close()


def pid_exists(pid: int) -> bool:
    """Report whether a Linux pid still has a procfs entry."""
    return pathlib.Path(f"/proc/{pid}").exists()


def kill_if_present(pid: int) -> None:
    """Remove a leaked fixture child so one failure cannot affect later tests."""
    if not pid_exists(pid):
        return
    try:
        os.kill(pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    try:
        wait_until(lambda: not pid_exists(pid), timeout=2, description="fixture cleanup")
    except AssertionError:
        pass
