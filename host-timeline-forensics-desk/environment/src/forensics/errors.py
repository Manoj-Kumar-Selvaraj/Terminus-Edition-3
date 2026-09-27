"""Typed domain and infrastructure errors used across service boundaries."""


class ForensicError(Exception):
    """Base error carrying a stable machine-readable code."""

    code = "FORENSIC_ERROR"
    retryable = False

    def __init__(self, message: str, *, details: dict | None = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}

    def as_dict(self) -> dict:
        return {"code": self.code, "message": self.message[:512], "details": self.details}


class NotFound(ForensicError):
    code = "NOT_FOUND"


class Forbidden(ForensicError):
    code = "FORBIDDEN"


class Conflict(ForensicError):
    code = "CONFLICT"


class InvalidRequest(ForensicError):
    code = "INVALID_REQUEST"


class InvalidTransition(ForensicError):
    code = "INVALID_TRANSITION"


class StaleAttempt(Conflict):
    code = "STALE_ATTEMPT"


class EventConflict(Conflict):
    code = "EVENT_CONFLICT"


class IntegrityFailure(ForensicError):
    code = "INTEGRITY_FAILURE"


class PolicyDenied(Forbidden):
    code = "POLICY_DENIED"


class BudgetExceeded(ForensicError):
    code = "BUDGET_EXCEEDED"


class RetryableInfrastructure(ForensicError):
    code = "INFRASTRUCTURE_RETRYABLE"
    retryable = True


class DatabaseUnavailable(RetryableInfrastructure):
    code = "DATABASE_UNAVAILABLE"


class LabUnavailable(RetryableInfrastructure):
    code = "COLLECTION_LAB_UNAVAILABLE"


class EvidenceStoreUnavailable(RetryableInfrastructure):
    code = "EVIDENCE_STORE_UNAVAILABLE"
