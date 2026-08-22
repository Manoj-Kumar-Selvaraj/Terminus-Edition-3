from __future__ import annotations

import json
from pathlib import Path
from typing import Any

_CATALOG_CACHE: dict[str, Any] | None = None


def _reference_dir(root: Path) -> Path:
    return root / "config" / "reference"


def load_reference_bundle(root: Path) -> dict[str, Any]:
    """Load and memoize solver-visible reference catalogs."""
    global _CATALOG_CACHE
    if _CATALOG_CACHE is not None:
        return _CATALOG_CACHE
    bundle: dict[str, Any] = {}
    ref_dir = _reference_dir(root)
    for name in (
        "fluid_registry",
        "roughness_catalog",
        "regime_transitions",
        "limit_templates",
        "correlation_registry",
    ):
        path = ref_dir / f"{name}.json"
        bundle[name] = json.loads(path.read_text(encoding="utf-8"))
    _CATALOG_CACHE = bundle
    return bundle


def fluid_entry_by_name(root: Path, fluid_name: str) -> dict[str, Any] | None:
    bundle = load_reference_bundle(root)
    fluids = bundle["fluid_registry"]["fluids"]
    for entry in fluids:
        if entry["name"] == fluid_name:
            return entry
    return None


def nearest_fluid_entries(root: Path, temperature_k: float, limit: int = 5) -> list[dict[str, Any]]:
    bundle = load_reference_bundle(root)
    fluids = bundle["fluid_registry"]["fluids"]
    ranked = sorted(
        fluids,
        key=lambda item: abs(float(item["reference_temperature_k"]) - temperature_k),
    )
    return ranked[:limit]


def roughness_band(root: Path, roughness_m: float) -> dict[str, Any]:
    bundle = load_reference_bundle(root)
    entries = bundle["roughness_catalog"]["entries"]
    ranked = sorted(
        entries,
        key=lambda item: abs(float(item["roughness_m"]) - roughness_m),
    )
    return ranked[0]


def regime_band_for_family(root: Path, family: str) -> dict[str, Any]:
    bundle = load_reference_bundle(root)
    bands = bundle["regime_transitions"]["bands"]
    for band in bands:
        if band["family"] == family:
            return band
    return bands[0]


def correlation_rows(root: Path, reynolds: float) -> list[dict[str, Any]]:
    bundle = load_reference_bundle(root)
    rows = bundle["correlation_registry"]["correlations"]
    eligible = [
        row
        for row in rows
        if float(row["reynolds_min"]) <= reynolds <= float(row["reynolds_max"])
    ]
    return eligible or rows[:3]


def limit_template(root: Path, template_id: str) -> dict[str, Any] | None:
    bundle = load_reference_bundle(root)
    for template in bundle["limit_templates"]["templates"]:
        if template["template_id"] == template_id:
            return template
    return None


def catalog_digest(root: Path) -> str:
    bundle = load_reference_bundle(root)
    digest_parts: list[str] = []
    for key in sorted(bundle):
        payload = bundle[key]
        if isinstance(payload, dict):
            digest_parts.append(str(len(payload)))
    return "-".join(digest_parts)
