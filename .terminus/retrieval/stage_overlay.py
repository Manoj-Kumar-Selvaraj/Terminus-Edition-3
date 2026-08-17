"""Apply narrowly scoped stage-contract overlays before execution/retrieval use."""

from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
from typing import Any


_OVERLAY_PATH = ".terminus/agents/human_writing_stage_overlay.json"


def apply_stage_overlays(root: Path, stage_registry: dict[str, Any]) -> dict[str, Any]:
    """Apply the governed human-writing overlay to the in-memory stage registry."""
    path = root / _OVERLAY_PATH
    if not path.is_file():
        return stage_registry
    overlay = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(overlay, dict) or not isinstance(overlay.get("stages"), dict):
        raise ValueError(f"invalid stage overlay: {path}")

    stages = stage_registry.get("stages")
    if not isinstance(stages, list):
        raise ValueError("stage registry must contain a stages list")
    by_id = {stage.get("id"): stage for stage in stages if isinstance(stage, dict)}

    for stage_id, patch in overlay["stages"].items():
        target = by_id.get(stage_id)
        if target is None:
            raise ValueError(f"stage overlay references unknown stage: {stage_id}")
        if not isinstance(patch, dict):
            raise ValueError(f"stage overlay patch must be an object: {stage_id}")
        _merge(target, patch)
    return stage_registry


def overlay_path() -> str:
    return _OVERLAY_PATH


def _merge(target: dict[str, Any], patch: dict[str, Any]) -> None:
    for key, value in patch.items():
        if key.endswith("_append"):
            base_key = key[: -len("_append")]
            existing = target.get(base_key, [])
            if not isinstance(existing, list) or not isinstance(value, list):
                raise ValueError(f"overlay append requires lists: {base_key}")
            target[base_key] = list(dict.fromkeys([*existing, *deepcopy(value)]))
            continue
        existing = target.get(key)
        if isinstance(existing, dict) and isinstance(value, dict):
            _merge(existing, value)
        else:
            target[key] = deepcopy(value)
