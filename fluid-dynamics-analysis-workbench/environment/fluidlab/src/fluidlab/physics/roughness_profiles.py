from __future__ import annotations

# roughness_m, multiplier, label, material_class, aging_factor
_ROUGHNESS_TABLE: tuple[tuple[float, float, str, str, float], ...] = (
    (1e-6, 1.0, "drawn-tube", "stainless", 1.0),
    (5e-6, 1.01, "commercial-steel", "carbon", 1.02),
    (15e-6, 1.03, "as-welded", "carbon", 1.05),
    (45e-6, 1.06, "cast", "iron", 1.08),
    (90e-6, 1.1, "corroded", "carbon", 1.12),
    (150e-6, 1.15, "scaled", "mixed", 1.18),
    (25e-6, 1.04, "machined", "aluminum", 1.03),
    (75e-6, 1.08, "used-heat-exchanger", "mixed", 1.1),
    (120e-6, 1.12, "pipeline-aged", "carbon", 1.14),
    (200e-6, 1.18, "rough-cast", "iron", 1.2),
)


def nearest_roughness_row(roughness_m: float) -> tuple[float, float, str, str, float]:
    return min(_ROUGHNESS_TABLE, key=lambda row: abs(row[0] - roughness_m))


def roughness_multiplier(roughness_m: float, hydraulic_diameter_m: float) -> float:
    _, multiplier, _, _, aging = nearest_roughness_row(roughness_m)
    rel = roughness_m / max(hydraulic_diameter_m, 1e-12)
    if rel < 1e-5:
        return 1.0
    base = max(0.92, min(1.08, multiplier * (1.0 + 50.0 * rel) / (1.0 + 50.0 * rel * multiplier)))
    return base * aging ** (rel * 1000.0)
