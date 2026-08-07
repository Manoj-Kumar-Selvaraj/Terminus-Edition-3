from __future__ import annotations

import pathlib
import subprocess

from conftest import (
    GUARDIAN,
    RunningGuardian,
    control,
    launch,
    unit,
    wait_until,
    write_manifest,
)


def event_sequences(text: str) -> list[int]:
    """Extract committed sequence numbers from the public event stream."""
    values: list[int] = []
    for line in text.splitlines():
        fields = dict(part.split("=", 1) for part in line.split("|")[1:])
        values.append(int(fields["sequence"]))
    return values


def test_reload_is_transactional_and_keeps_live_runtime_state(
    tmp_path: pathlib.Path, guardians: list[RunningGuardian]
) -> None:
    """Invalid and unchanged reloads must preserve the live pid and consumed budget."""
    manifest = tmp_path / "services.guardian"
    state = tmp_path / "state"
    crash_file = state / "crashes.left"
    crash_file.parent.mkdir(parents=True)
    crash_file.write_text("2\n", encoding="utf-8")
    valid = unit(
        "api",
        "--name",
        "api",
        "--crash-count-file",
        str(crash_file),
        restart="on-failure",
        restart_limit=2,
    )
    write_manifest(manifest, valid)
    running = launch(manifest, state)
    guardians.append(running)

    wait_until(
        lambda: running.status()["api"]["state"] == "ready",
        description="worker after two restarts",
    )
    before = running.status()["api"]
    assert before["restarts"] == "2"

    manifest.write_text("unit broken\nexec relative\nend\n", encoding="utf-8")
    assert control(running.socket, "RELOAD") == "ERR|code=INVALID_MANIFEST\n"
    rejected = running.status()["api"]
    assert rejected == before

    write_manifest(manifest, valid)
    assert control(running.socket, "RELOAD") == "OK|command=RELOAD\n"
    unchanged = running.status()["api"]
    assert unchanged["pid"] == before["pid"]
    assert unchanged["state"] == "ready"
    assert unchanged["restarts"] == "2"


def test_torn_journal_tail_recovers_once_and_stays_reopenable(
    tmp_path: pathlib.Path, guardians: list[RunningGuardian]
) -> None:
    """Recovery must discard a partial tail before new durable records are appended."""
    manifest = tmp_path / "services.guardian"
    state = tmp_path / "state"
    write_manifest(manifest, unit("api", "--name", "api"))

    first = launch(manifest, state)
    guardians.append(first)
    wait_until(
        lambda: first.status()["api"]["state"] == "ready",
        description="first daemon readiness",
    )
    first.shutdown()
    journal = state / "events.bin"
    with journal.open("ab") as output:
        output.write(b"TORN-JOURNAL-TAIL")
        output.flush()

    second = launch(manifest, state)
    guardians.append(second)
    wait_until(
        lambda: second.status()["api"]["state"] == "ready",
        description="recovered daemon readiness",
    )
    sequences = event_sequences(control(second.socket, "EVENTS"))
    assert sequences == list(range(1, len(sequences) + 1))
    second.shutdown()

    third = launch(manifest, state)
    guardians.append(third)
    wait_until(
        lambda: third.status()["api"]["state"] == "ready",
        description="journal reopening after recovery",
    )
    final_sequences = event_sequences(control(third.socket, "EVENTS"))
    assert final_sequences == list(range(1, len(final_sequences) + 1))
    assert len(final_sequences) > len(sequences)


def test_corruption_inside_committed_history_fails_closed(
    tmp_path: pathlib.Path, guardians: list[RunningGuardian]
) -> None:
    """Damaging an early committed record must fail startup instead of erasing history."""
    manifest = tmp_path / "services.guardian"
    state = tmp_path / "state"
    write_manifest(manifest, unit("api", "--name", "api"))
    running = launch(manifest, state)
    guardians.append(running)
    wait_until(
        lambda: running.status()["api"]["state"] == "ready",
        description="daemon readiness before corruption",
    )
    running.shutdown()

    journal = state / "events.bin"
    with journal.open("r+b") as stream:
        stream.seek(20)
        original = stream.read(1)
        assert original
        stream.seek(20)
        stream.write(bytes([original[0] ^ 0x5A]))
        stream.flush()

    result = subprocess.run(
        [str(GUARDIAN), "run", str(manifest), str(state)],
        text=True,
        capture_output=True,
        timeout=5,
        check=False,
    )
    assert result.returncode != 0
    assert "corruption" in result.stderr.lower()


def test_removing_provider_stops_its_dependent_closure_first(
    tmp_path: pathlib.Path, guardians: list[RunningGuardian]
) -> None:
    """A reload removal must stop dependents before the provider leaves service."""
    manifest = tmp_path / "services.guardian"
    state = tmp_path / "state"
    provider = unit("db", "--name", "db")
    client = unit("api", "--name", "api", dependencies=("db",))
    write_manifest(manifest, provider, client)
    running = launch(manifest, state)
    guardians.append(running)
    wait_until(
        lambda: all(
            item["state"] == "ready" for item in running.status().values()
        ),
        description="graph readiness before removal",
    )

    write_manifest(manifest, unit("replacement", "--name", "replacement"))
    assert control(running.socket, "RELOAD") == "OK|command=RELOAD\n"
    wait_until(
        lambda: running.status()["db"]["state"] == "stopped"
        and running.status()["api"]["state"] == "stopped",
        description="removed dependency closure",
    )
    stopping = [
        line.split("|unit=", 1)[1].split("|", 1)[0]
        for line in control(running.socket, "EVENTS").splitlines()
        if "|type=unit-stopping|" in line
    ]
    assert stopping[-2:] == ["api", "db"]


def test_changed_unit_restarts_without_replacing_unchanged_provider(
    tmp_path: pathlib.Path, guardians: list[RunningGuardian]
) -> None:
    """A valid reload must replace only changed units after providers remain ready."""
    manifest = tmp_path / "services.guardian"
    state = tmp_path / "state"
    provider = unit("db", "--name", "db")
    api_v1 = unit("api", "--name", "api-v1", dependencies=("db",))
    write_manifest(manifest, provider, api_v1)
    running = launch(manifest, state)
    guardians.append(running)
    wait_until(
        lambda: all(
            item["state"] == "ready" for item in running.status().values()
        ),
        description="initial graph readiness",
    )
    before = running.status()

    api_v2 = unit("api", "--name", "api-v2", dependencies=("db",))
    write_manifest(manifest, provider, api_v2)
    assert control(running.socket, "RELOAD") == "OK|command=RELOAD\n"
    wait_until(
        lambda: running.status()["api"]["state"] == "ready"
        and running.status()["api"]["pid"] != before["api"]["pid"],
        description="changed unit replacement",
    )
    after = running.status()
    assert after["db"]["pid"] == before["db"]["pid"]
    assert after["api"]["pid"] != before["api"]["pid"]
