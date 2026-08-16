from __future__ import annotations

import json
from typing import Any


class CcError(Exception):
    def __init__(self, error: str, code: str | None = None, **extra: Any) -> None:
        self.error = error
        self.code = code
        self.extra = extra
        super().__init__(error if code is None else f"{error}:{code}")

    def to_dict(self) -> dict[str, Any]:
        body: dict[str, Any] = {"error": self.error}
        if self.code is not None:
            body["code"] = self.code
        body.update(self.extra)
        return body

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), separators=(",", ":"))


class AccessDenied(CcError):
    def __init__(self, code: str | None = None, **extra: Any) -> None:
        super().__init__("AccessDenied", code=code, **extra)


class ValidationException(CcError):
    def __init__(self, code: str, **extra: Any) -> None:
        super().__init__("ValidationException", code=code, **extra)
