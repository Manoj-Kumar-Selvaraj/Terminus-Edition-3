from __future__ import annotations

import os
import time
from pathlib import Path


class FileLock:
    """Best-effort exclusive lock using a lockfile beside the target."""

    def __init__(self, target: Path, timeout_sec: float = 10.0) -> None:
        self.target = target
        self.lock_path = target.with_suffix(target.suffix + ".lock")
        self.timeout_sec = timeout_sec
        self._fd: int | None = None

    def acquire(self) -> None:
        self.lock_path.parent.mkdir(parents=True, exist_ok=True)
        deadline = time.time() + self.timeout_sec
        while True:
            try:
                self._fd = os.open(str(self.lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                os.write(self._fd, str(os.getpid()).encode())
                return
            except FileExistsError:
                if time.time() >= deadline:
                    raise TimeoutError(f"lock timeout: {self.lock_path}")
                time.sleep(0.05)

    def release(self) -> None:
        if self._fd is not None:
            os.close(self._fd)
            self._fd = None
        try:
            self.lock_path.unlink(missing_ok=True)
        except OSError:
            pass

    def __enter__(self) -> "FileLock":
        self.acquire()
        return self

    def __exit__(self, *args: object) -> None:
        self.release()
