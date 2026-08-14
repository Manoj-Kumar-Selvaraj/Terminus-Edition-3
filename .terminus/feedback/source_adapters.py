"""Convenience adapters for the supported feedback-producing systems."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .ingestion import FeedbackIngestor
from .model import FeedbackSource, Severity


class FeedbackAdapters:
    def __init__(self, root: Path, ingestor: FeedbackIngestor | None = None):
        self.ingestor = ingestor or FeedbackIngestor(root)

    def human_review(self, **kwargs: Any) -> dict[str, Any]:
        return self._capture(FeedbackSource.HUMAN_REVIEW, **kwargs)

    def independent_review(self, **kwargs: Any) -> dict[str, Any]:
        return self._capture(FeedbackSource.INDEPENDENT_REVIEW, **kwargs)

    def reviewer_review(self, **kwargs: Any) -> dict[str, Any]:
        return self._capture(FeedbackSource.REVIEWER_REVIEW, **kwargs)

    def portal_ci(self, **kwargs: Any) -> dict[str, Any]:
        return self._capture(FeedbackSource.PORTAL_CI, **kwargs)

    def repository_ci(self, **kwargs: Any) -> dict[str, Any]:
        return self._capture(FeedbackSource.REPOSITORY_CI, **kwargs)

    def llmaj(self, **kwargs: Any) -> dict[str, Any]:
        return self._capture(FeedbackSource.LLMAJ, **kwargs)

    def model_diagnostic(self, **kwargs: Any) -> dict[str, Any]:
        return self._capture(FeedbackSource.MODEL_DIAGNOSTIC, **kwargs)

    def model_trial(self, **kwargs: Any) -> dict[str, Any]:
        return self._capture(FeedbackSource.MODEL_TRIAL, **kwargs)

    def difficulty(self, **kwargs: Any) -> dict[str, Any]:
        return self._capture(FeedbackSource.DIFFICULTY, **kwargs)

    def final_review(self, **kwargs: Any) -> dict[str, Any]:
        return self._capture(FeedbackSource.FINAL_REVIEW, **kwargs)

    def submission_result(self, **kwargs: Any) -> dict[str, Any]:
        return self._capture(FeedbackSource.SUBMISSION_RESULT, **kwargs)

    def runtime(self, **kwargs: Any) -> dict[str, Any]:
        return self._capture(FeedbackSource.RUNTIME, **kwargs)

    def _capture(self, source: FeedbackSource, **kwargs: Any) -> dict[str, Any]:
        severity = kwargs.pop("severity", Severity.MEDIUM)
        return self.ingestor.capture(source_type=source, severity=severity, **kwargs)
