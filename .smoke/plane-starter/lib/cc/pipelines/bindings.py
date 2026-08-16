"""Pipeline bindings loaded from ``ops/pipelines.json``."""

from __future__ import annotations

from typing import Any

from cc.home import pipeline_bindings
from cc.models import PipelineBinding
from cc.util import normalize_ref


def all_bindings() -> list[PipelineBinding]:
    """Every configured binding, enabled or not, in file order."""
    return [PipelineBinding.from_dict(body) for body in pipeline_bindings()]


def enabled_bindings() -> list[PipelineBinding]:
    return [binding for binding in all_bindings() if binding.enabled]


def for_ref(repo: str, ref: str) -> list[PipelineBinding]:
    """Enabled bindings that watch this repository and ref."""
    target = normalize_ref(ref)
    return [
        binding
        for binding in enabled_bindings()
        if binding.repo == repo and normalize_ref(binding.ref) == target
    ]


def is_bound(repo: str, ref: str) -> bool:
    return bool(for_ref(repo, ref))


def pipelines_for(repo: str, ref: str) -> list[str]:
    """Pipeline names a delivery on this ref would start."""
    return [binding.pipeline for binding in for_ref(repo, ref)]


def parked_for(repo: str, ref: str) -> list[str]:
    """Bindings that match but are disabled, so an operator can see them."""
    target = normalize_ref(ref)
    return [
        binding.pipeline
        for binding in all_bindings()
        if binding.repo == repo and normalize_ref(binding.ref) == target and not binding.enabled
    ]


def describe(repo: str) -> dict[str, Any]:
    """Binding summary for one repository."""
    entries = [binding for binding in all_bindings() if binding.repo == repo]
    return {
        "repo": repo,
        "bindings": [
            {"pipeline": binding.pipeline, "ref": binding.ref, "enabled": binding.enabled}
            for binding in entries
        ],
        "enabled": sum(1 for binding in entries if binding.enabled),
    }
