"""Advisory file lock used to serialize mutations of shared JSON state.

The lock is a directory-based sentinel so it behaves the same way on any
filesystem the lab runs on, and it recovers from a holder that died without
releasing.
"""

from __future__ import annotations

import os
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from cc.errors import CcError
from cc.home import locks_dir

DEFAULT_TIMEOUT = 10.0
POLL_INTERVAL = 0.01
STALE_AFTER = 30.0


def _lock_path(name: str) -> Path:
    return locks_dir() / f"{name}.lock"


def _age(path: Path) -> float:
    try:
        return max(0.0, time.time() - path.stat().st_mtime)
    except OSError:
        return 0.0


def _try_acquire(path: Path) -> bool:
    try:
        handle = os.open(str(path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        if _age(path) > STALE_AFTER:
            _release(path)
        return False
    try:
        os.write(handle, str(os.getpid()).encode("ascii"))
    finally:
        os.close(handle)
    return True


def _release(path: Path) -> None:
    try:
        path.unlink()
    except FileNotFoundError:
        return


@contextmanager
def guard(name: str, timeout: float = DEFAULT_TIMEOUT) -> Iterator[None]:
    """Hold the named lock for the duration of the block."""
    locks_dir().mkdir(parents=True, exist_ok=True)
    path = _lock_path(name)
    deadline = time.monotonic() + timeout
    while not _try_acquire(path):
        if time.monotonic() >= deadline:
            raise CcError("LOCK_TIMEOUT", f"could not acquire {name} lock")
        time.sleep(POLL_INTERVAL)
    try:
        yield
    finally:
        _release(path)
