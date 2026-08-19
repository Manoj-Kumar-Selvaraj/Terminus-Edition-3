from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _run(relative: str) -> None:
    subprocess.run(
        [sys.executable, str(ROOT / relative)],
        cwd=ROOT,
        check=True,
    )


def test_human_writing_calibration_regressions() -> None:
    _run(".terminus/human_writing/test_calibration.py")


def test_human_writing_learning_loop_regressions() -> None:
    _run(".terminus/human_writing/test_learning_loop.py")
