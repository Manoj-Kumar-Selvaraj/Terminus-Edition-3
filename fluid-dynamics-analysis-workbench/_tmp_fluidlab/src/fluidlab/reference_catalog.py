from __future__ import annotations

from .models import CaseSpec, FluidSpec
from .physics.property_registry import (
    catalog_property_delta,
    density_correction_factor,
    property_consistency_score,
    registry_digest,
    rows_for_temperature,
    row_by_name,
)

__all__ = [
    "catalog_property_delta",
    "density_correction_factor",
    "property_consistency_score",
    "registry_digest",
    "rows_for_temperature",
    "row_by_name",
    "nearest_fluid_entries",
    "roughness_band",
    "regime_band_for_family",
    "correlation_rows",
    "load_reference_bundle",
]


def nearest_fluid_entries(_root: object, temperature_k: float, limit: int = 5) -> list[dict[str, object]]:
    rows = rows_for_temperature(temperature_k, limit=limit)
    return [
        {
            "name": row[0],
            "model": row[1],
            "reference_temperature_k": row[2],
            "density_kg_m3": row[3],
            "cp_j_kgk": row[5],
        }
        for row in rows
    ]


def roughness_band(_root: object, roughness_m: float) -> dict[str, object]:
    from .physics.roughness_profiles import nearest_roughness_row

    roughness, multiplier, label = nearest_roughness_row(roughness_m)
    return {"roughness_m": roughness, "multiplier": multiplier, "label": label}


def regime_band_for_family(_root: object, family: str) -> dict[str, object]:
    from .physics.regime_bands import band_for_family

    laminar, transitional, turbulent = band_for_family(family)
    return {
        "family": family,
        "laminar_upper": laminar,
        "transitional_upper": transitional,
        "turbulent_lower": turbulent,
    }


def correlation_rows(_root: object, reynolds: float) -> list[dict[str, object]]:
    from .physics.correlation_atlas import atlas_selector_00, atlas_selector_01

    return [
        {"reynolds_min": 0.0, "reynolds_max": 1e9, "coeff_a": atlas_selector_00(reynolds, 1e-5, 0.03)},
        {"reynolds_min": 0.0, "reynolds_max": 1e9, "coeff_a": atlas_selector_01(reynolds, 1e-5, 0.03)},
    ]


def load_reference_bundle(_root: object) -> dict[str, object]:
    return {"property_registry": {"rows": registry_digest()}}
