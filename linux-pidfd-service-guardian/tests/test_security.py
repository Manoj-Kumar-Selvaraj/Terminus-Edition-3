from __future__ import annotations

import os
import pathlib
import stat
import subprocess

from conftest import (
    BIN,
    GUARDIAN,
    RunningGuardian,
    control,
    launch,
    unit,
    wait_until,
    write_manifest,
)


def test_control_socket_uses_peer_credentials_despite_public_mode(
    tmp_path: pathlib.Path, guardians: list[RunningGuardian]
) -> None:
    """Socket permissions may permit connection, while another uid still gets denied."""
    root = pathlib.Path(f"/tmp/guardian-peer-{os.getpid()}")
    root.mkdir(mode=0o777, exist_ok=True)
    root.chmod(0o777)
    manifest = root / "services.guardian"
    state = root / "state"
    write_manifest(manifest, unit("api", "--name", "api"))
    manifest.chmod(0o644)
    running = launch(manifest, state)
    guardians.append(running)
    state.chmod(0o755)

    socket_mode = stat.S_IMODE(running.socket.stat().st_mode)
    assert socket_mode == 0o666
    assert control(running.socket, "STATUS", uid=65534) == "ERR|code=ACCESS_DENIED\n"
    assert running.status()["api"]["state"] == "ready"


def test_state_directory_lock_is_singleton_and_non_disruptive(
    tmp_path: pathlib.Path, guardians: list[RunningGuardian]
) -> None:
    """A second owner must fail while the original daemon and socket stay healthy."""
    manifest = tmp_path / "services.guardian"
    state = tmp_path / "state"
    write_manifest(manifest, unit("api", "--name", "api"))
    running = launch(manifest, state)
    guardians.append(running)
    original_pid = running.status()["api"]["pid"]

    contender = subprocess.run(
        [str(GUARDIAN), "run", str(manifest), str(state)],
        text=True,
        capture_output=True,
        timeout=5,
        check=False,
    )
    assert contender.returncode != 0
    assert "already running" in contender.stderr
    assert running.process.poll() is None
    assert running.status()["api"]["pid"] == original_pid


def test_exec_failure_is_reported_without_phantom_process(
    tmp_path: pathlib.Path, guardians: list[RunningGuardian]
) -> None:
    """An absolute but missing executable must become a failed unit with pid zero."""
    manifest = tmp_path / "services.guardian"
    state = tmp_path / "state"
    broken = unit("missing", "--name", "missing").replace(
        f"exec {BIN / 'guardian-worker'}", "exec /app/guardian/bin/not-present"
    )
    write_manifest(manifest, broken)
    running = launch(manifest, state)
    guardians.append(running)

    failed = wait_until(
        lambda: (
            status
            if (status := running.status()["missing"])["state"] == "failed"
            else None
        ),
        description="exec failure state",
    )
    assert isinstance(failed, dict)
    assert failed["pid"] == "0"
    events = control(running.socket, "EVENTS")
    assert "|type=unit-failed|unit=missing|pid=0|detail=exec" in events
