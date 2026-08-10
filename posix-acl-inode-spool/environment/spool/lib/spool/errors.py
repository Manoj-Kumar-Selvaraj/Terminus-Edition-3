from __future__ import annotations

import json


class VfsError(Exception):
    def __init__(self, error: str, code: str | None = None, path: str | None = None) -> None:
        super().__init__(error)
        self.error = error
        self.code = code
        self.path = path

    def to_json(self) -> str:
        payload: dict[str, str] = {"error": self.error}
        if self.code:
            payload["code"] = self.code
        if self.path:
            payload["path"] = self.path
        return json.dumps(payload, separators=(",", ":"))
