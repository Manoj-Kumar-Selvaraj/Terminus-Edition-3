from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from cc.store.lock import FileLock
from cc.util import dump_json, load_json


class JsonStore:
    def __init__(self, path: Path, default_factory: Callable[[], Any]) -> None:
        self.path = path
        self.default_factory = default_factory

    def read(self) -> Any:
        return load_json(self.path, self.default_factory())

    def write(self, data: Any) -> None:
        with FileLock(self.path):
            dump_json(self.path, data)

    def update(self, mutator: Callable[[Any], Any]) -> Any:
        with FileLock(self.path):
            data = load_json(self.path, self.default_factory())
            data = mutator(data)
            dump_json(self.path, data)
            return data
