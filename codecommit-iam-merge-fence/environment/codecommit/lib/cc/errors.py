from __future__ import annotations

import json


class CcError(Exception):
    def __init__(self, error: str, code: str | None = None) -> None:
        super().__init__(error)
        self.error = error
        self.code = code

    def to_json(self) -> str:
        payload = {"error": self.error}
        if self.code:
            payload["code"] = self.code
        return json.dumps(payload, separators=(",", ":"))
