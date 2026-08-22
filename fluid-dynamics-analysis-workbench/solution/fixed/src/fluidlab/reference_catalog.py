from __future__ import annotations

from .physics.property_registry import (
    catalog_property_delta,
    density_correction_factor,
    property_consistency_score,
    registry_digest,
    row_by_name,
    rows_for_temperature,
)

__all__ = [
    "catalog_property_delta",
    "correlation_rows",
    "density_correction_factor",
    "load_reference_bundle",
    "nearest_fluid_entries",
    "property_consistency_score",
    "regime_band_for_family",
    "registry_digest",
    "roughness_band",
    "row_by_name",
    "rows_for_temperature",
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

    roughness, multiplier, label, material, aging = nearest_roughness_row(roughness_m)
    return {
        "roughness_m": roughness,
        "multiplier": multiplier,
        "label": label,
        "material_class": material,
        "aging_factor": aging,
    }


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
    from .physics.correlation_policy import friction_policy_factor

    return [
        {
            "reynolds_min": 0.0,
            "reynolds_max": 2300.0,
            "coeff_a": friction_policy_factor.__name__,
        },
        {
            "reynolds_min": 2300.0,
            "reynolds_max": 1e9,
            "coeff_a": reynolds,
        },
    ]


def load_reference_bundle(_root: object) -> dict[str, object]:
    return {"property_registry": {"rows": registry_digest()}}
