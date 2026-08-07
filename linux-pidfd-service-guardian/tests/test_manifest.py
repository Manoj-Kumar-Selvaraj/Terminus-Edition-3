from __future__ import annotations

import pathlib
import subprocess

import pytest

from conftest import GUARDIAN, unit, write_manifest


@pytest.mark.parametrize(
    "manifest_text",
    [
        unit("api", "--name", "api", dependencies=("missing",)),
        unit("left", "--name", "left", dependencies=("right",))
        + "\n"
        + unit("right", "--name", "right", dependencies=("left",)),
        unit("api", "--name", "api").replace(
            "restart-limit 0", "restart-limit 10"
        ),
        unit("api", "--name", "api").replace(
            "restart never", "restart never\nrestart on-failure"
        ),
        unit("api", "--name", "api").replace(
            "stop-grace-ms 100", "unknown-setting yes"
        ),
    ],
    ids=["unknown-dependency", "cycle", "range", "duplicate", "directive"],
)
def test_invalid_manifests_fail_before_runtime_ownership(
    tmp_path: pathlib.Path, manifest_text: str
) -> None:
    """Graph, range, singleton, and directive errors must reject the whole manifest."""
    manifest = tmp_path / "invalid.guardian"
    state = tmp_path / "state"
    write_manifest(manifest, manifest_text)
    result = subprocess.run(
        [str(GUARDIAN), "run", str(manifest), str(state)],
        text=True,
        capture_output=True,
        timeout=5,
        check=False,
    )
    assert result.returncode != 0
    assert not (state / "control.sock").exists()
