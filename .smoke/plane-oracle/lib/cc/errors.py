"""Structured control-plane errors.

Every operator surface (CLI and HTTP API) reports failures through these
classes so that the emitted envelope and the HTTP status stay in step.
"""

from __future__ import annotations

from typing import Any

KIND_STATUS = {
    "ValidationException": 400,
    "AccessDenied": 403,
    "NotFound": 404,
    "ConflictException": 409,
    "GitError": 500,
    "InternalFailure": 500,
}


class CcError(Exception):
    """Base class for every error the control plane reports to a caller."""

    kind = "InternalFailure"

    def __init__(self, code: str, message: str = "", **details: Any) -> None:
        self.code = code
        self.message = message or code
        self.details = {key: value for key, value in details.items() if value is not None}
        super().__init__(f"{self.kind}/{self.code}: {self.message}")

    @property
    def status(self) -> int:
        return KIND_STATUS.get(self.kind, 500)

    def payload(self) -> dict[str, Any]:
        body: dict[str, Any] = {
            "error": self.kind,
            "code": self.code,
            "message": self.message,
        }
        if self.details:
            body["details"] = dict(sorted(self.details.items()))
        return body


class AccessDenied(CcError):
    """The evaluated policy set does not permit the request."""

    kind = "AccessDenied"


class ValidationException(CcError):
    """The request is well formed but violates a control-plane rule."""

    kind = "ValidationException"


class NotFound(CcError):
    """A named repository, pull request, or route does not exist."""

    kind = "NotFound"


class GitError(CcError):
    """An underlying git invocation failed."""

    kind = "GitError"


def as_cc_error(exc: BaseException) -> CcError:
    """Wrap an arbitrary exception so callers always see a structured error."""
    if isinstance(exc, CcError):
        return exc
    return CcError("INTERNAL_FAILURE", str(exc) or exc.__class__.__name__)
