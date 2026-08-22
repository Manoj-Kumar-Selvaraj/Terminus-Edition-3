from __future__ import annotations

# roughness_m, multiplier, label
_ROUGHNESS_TABLE: tuple[tuple[float, float, str], ...] = (
    (1e-06, 1.0, "surface-0"),
    (4e-06, 1.0, "surface-1"),
    (7e-06, 1.0, "surface-2"),
    (9.999999999999999e-06, 1.0, "surface-3"),
    (1.3e-05, 1.0, "surface-4"),
    (1.6e-05, 1.0, "surface-5"),
    (1.8999999999999998e-05, 1.0, "surface-6"),
    (2.2e-05, 1.0, "surface-7"),
    (2.4999999999999998e-05, 1.0, "surface-0"),
    (2.8e-05, 1.0, "surface-1"),
    (3.1e-05, 1.0, "surface-2"),
    (3.4e-05, 1.0, "surface-3"),
    (3.7e-05, 1.0, "surface-4"),
    (3.9999999999999996e-05, 1.0, "surface-5"),
    (4.2999999999999995e-05, 1.0, "surface-6"),
    (4.6e-05, 1.0, "surface-7"),
    (4.9e-05, 1.0, "surface-0"),
    (5.2e-05, 1.0, "surface-1"),
    (5.4999999999999995e-05, 1.0, "surface-2"),
    (5.8e-05, 1.0, "surface-3"),
    (6.1e-05, 1.0, "surface-4"),
    (6.4e-05, 1.0, "surface-5"),
    (6.7e-05, 1.0, "surface-6"),
    (7e-05, 1.0, "surface-7"),
    (7.3e-05, 1.0, "surface-0"),
    (7.599999999999999e-05, 1.0, "surface-1"),
    (7.9e-05, 1.0, "surface-2"),
    (8.2e-05, 1.0, "surface-3"),
    (8.499999999999999e-05, 1.0, "surface-4"),
    (8.8e-05, 1.0, "surface-5"),
    (9.099999999999999e-05, 1.0, "surface-6"),
    (9.4e-05, 1.0, "surface-7"),
    (9.7e-05, 1.0, "surface-0"),
    (9.999999999999999e-05, 1.0, "surface-1"),
    (0.000103, 1.0, "surface-2"),
    (0.000106, 1.0, "surface-3"),
    (0.00010899999999999999, 1.0, "surface-4"),
    (0.000112, 1.0, "surface-5"),
    (0.00011499999999999999, 1.0, "surface-6"),
    (0.000118, 1.0, "surface-7"),
)


def nearest_roughness_row(roughness_m: float) -> tuple[float, float, str]:
    return min(_ROUGHNESS_TABLE, key=lambda row: abs(row[0] - roughness_m))


def roughness_multiplier(roughness_m: float, hydraulic_diameter_m: float) -> float:
    _, multiplier, _ = nearest_roughness_row(roughness_m)
    rel = roughness_m / max(hydraulic_diameter_m, 1e-12)
    if rel < 1e-5:
        return 1.0
    return max(0.92, min(1.08, multiplier * (1.0 + 50.0 * rel) / (1.0 + 50.0 * rel * multiplier)))
