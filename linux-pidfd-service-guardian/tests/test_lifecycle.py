from __future__ import annotations

import pathlib

import pytest

from conftest import (
    RunningGuardian,
    control,
    kill_if_present,
    launch,
    pid_exists,
    unit,
    wait_until,
    write_manifest,
)


def test_dependents_wait_for_provider_readiness(
    tmp_path: pathlib.Path, guardians: list[RunningGuardian]
) -> None:
    """A spawned provider must not unlock its dependent before readiness arrives."""
    manifest = tmp_path / "services.guardian"
    state = tmp_path / "state"
    gate = state / "provider.gate"
    provider_ready = state / "provider.ready"
    dependent_ready = state / "dependent.ready"
    write_manifest(
        manifest,
        unit(
            "provider",
            "--name",
            "provider",
            "--ready-gate-file",
            str(gate),
            "--ready-file",
            str(provider_ready),
        ),
        unit(
            "dependent",
            "--name",
            "dependent",
            "--ready-file",
            str(dependent_ready),
            dependencies=("provider",),
        ),
    )
    running = launch(manifest, state)
    guardians.append(running)

    status = running.status()
    assert status["provider"]["state"] == "starting"
    assert status["dependent"]["state"] == "stopped"
    assert not dependent_ready.exists()

    gate.touch()
    ready = wait_until(
        lambda: running.status()["dependent"]["state"] == "ready",
        description="dependency chain readiness",
    )
    assert ready
    assert provider_ready.exists()
    assert dependent_ready.exists()

    running.shutdown()
    reopened = launch(manifest, state)
    guardians.append(reopened)
    events = control(reopened.socket, "EVENTS").splitlines()
    stopping = [
        line.split("|unit=", 1)[1].split("|", 1)[0]
        for line in events
        if "|type=unit-stopping|" in line
    ]
    assert stopping[-2:] == ["dependent", "provider"]


def test_runtime_owns_linux_event_descriptors(
    tmp_path: pathlib.Path, guardians: list[RunningGuardian]
) -> None:
    """The live daemon must expose pidfd, epoll, signalfd, and timerfd descriptors."""
    manifest = tmp_path / "services.guardian"
    state = tmp_path / "state"
    write_manifest(manifest, unit("api", "--name", "api"))
    running = launch(manifest, state)
    guardians.append(running)
    wait_until(
        lambda: running.status()["api"]["state"] == "ready",
        description="worker readiness",
    )

    fd_directory = pathlib.Path(f"/proc/{running.process.pid}/fd")
    targets = {
        descriptor.readlink().as_posix()
        for descriptor in fd_directory.iterdir()
        if descriptor.is_symlink()
    }
    assert "anon_inode:[pidfd]" in targets
    assert "anon_inode:[eventpoll]" in targets
    assert "anon_inode:[signalfd]" in targets
    assert "anon_inode:[timerfd]" in targets


@pytest.mark.parametrize("command", ["STOP tree", "SHUTDOWN"])
def test_stop_and_shutdown_contain_the_complete_process_group(
    tmp_path: pathlib.Path,
    guardians: list[RunningGuardian],
    command: str,
) -> None:
    """Stop and shutdown must remove a TERM-resistant descendant with its leader."""
    manifest = tmp_path / "services.guardian"
    state = tmp_path / "state"
    child_file = state / "child.pid"
    term_file = state / "leader.term"
    write_manifest(
        manifest,
        unit(
            "tree",
            "--name",
            "tree",
            "--spawn-child-file",
            str(child_file),
            "--term-file",
            str(term_file),
            grace_ms=80,
        ),
    )
    running = launch(manifest, state)
    guardians.append(running)
    wait_until(child_file.exists, description="descendant pid file")
    child_pid = int(child_file.read_text(encoding="utf-8").strip())
    leader_pid = int(running.status()["tree"]["pid"])

    try:
        expected = "SHUTDOWN" if command == "SHUTDOWN" else "STOP"
        assert control(running.socket, command) == f"OK|command={expected}\n"
        if command == "SHUTDOWN":
            running.process.wait(timeout=8)
        else:
            wait_until(
                lambda: running.status()["tree"]["state"] == "stopped",
                description="unit stop",
            )
        wait_until(
            lambda: not pid_exists(leader_pid) and not pid_exists(child_pid),
            description="complete process-tree cleanup",
        )
    finally:
        kill_if_present(child_pid)


def test_failure_budget_blocks_a_ready_dependent(
    tmp_path: pathlib.Path, guardians: list[RunningGuardian]
) -> None:
    """A provider that fails after readiness must exhaust its budget and block users."""
    manifest = tmp_path / "services.guardian"
    state = tmp_path / "state"
    crash_file = state / "crashes.left"
    crash_file.parent.mkdir(parents=True)
    crash_file.write_text("2\n", encoding="utf-8")
    write_manifest(
        manifest,
        unit(
            "provider",
            "--name",
            "provider",
            "--crash-count-file",
            str(crash_file),
            restart="on-failure",
            restart_limit=1,
        ),
        unit("client", "--name", "client", dependencies=("provider",)),
    )
    running = launch(manifest, state)
    guardians.append(running)

    wait_until(
        lambda: running.status()["provider"]["state"] == "failed",
        description="restart budget exhaustion",
    )
    status = running.status()
    assert status["provider"]["restarts"] == "1"
    assert status["client"]["state"] == "blocked"
