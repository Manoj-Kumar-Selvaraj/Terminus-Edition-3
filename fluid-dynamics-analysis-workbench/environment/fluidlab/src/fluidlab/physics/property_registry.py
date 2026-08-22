from __future__ import annotations

from ..models import CaseSpec, FluidSpec

# name, model, T_ref, rho, mu, cp, k, beta, gamma, R
_NAMED_ROWS: tuple[tuple[str, str, float, float, float, float, float, float, float, float], ...] = (
    ("process-water", "liquid", 293.15, 997.0, 0.00089, 4182.0, 0.6, 0.00029, 1.0, 0.0),
    ("water-glycol-30", "liquid", 293.15, 1035.0, 0.0031, 3770.0, 0.41, 0.00042, 1.0, 0.0),
    ("dry-air", "ideal_gas", 288.15, 1.18, 0.0000185, 1007.0, 0.026, 0.0, 1.4, 287.05),
)

_TEMPERATURE_ANCHORS: tuple[tuple[float, float, float, float], ...] = (
    (273.15, 999.8, 4218.0, 0.00005),
    (283.15, 998.5, 4195.0, 0.00012),
    (293.15, 997.0, 4182.0, 0.00029),
    (303.15, 995.2, 4178.0, 0.00038),
    (313.15, 992.0, 4174.0, 0.00045),
    (288.15, 1.18, 1007.0, 0.0),
    (298.15, 1.15, 1007.0, 0.0),
    (308.15, 1.12, 1007.0, 0.0),
)


def rows_for_temperature(temperature_k: float, limit: int = 5) -> list[tuple[str, str, float, float, float, float, float, float, float, float]]:
    ranked = sorted(_NAMED_ROWS, key=lambda row: abs(row[2] - temperature_k))
    return ranked[:limit]


def row_by_name(name: str) -> tuple[str, str, float, float, float, float, float, float, float, float] | None:
    for row in _NAMED_ROWS:
        if row[0] == name:
            return row
    return None


def _anchor_density(temperature_k: float, fluid: FluidSpec) -> float:
    if fluid.model == "ideal_gas":
        anchors = [(temp, rho, cp, beta) for temp, rho, cp, beta in _TEMPERATURE_ANCHORS if temp >= 280.0]
    else:
        anchors = [(temp, rho, cp, beta) for temp, rho, cp, beta in _TEMPERATURE_ANCHORS if temp < 320.0]
    if not anchors:
        return fluid.density_kg_m3
    lower = max((row for row in anchors if row[0] <= temperature_k), key=lambda row: row[0], default=anchors[0])
    upper = min((row for row in anchors if row[0] >= temperature_k), key=lambda row: row[0], default=anchors[-1])
    if lower[0] == upper[0]:
        return lower[1]
    weight = (temperature_k - lower[0]) / max(upper[0] - lower[0], 1e-9)
    return lower[1] * (1.0 - weight) + upper[1] * weight


def property_consistency_score(fluid: FluidSpec, bulk_temperature_k: float) -> float:
    anchor = _anchor_density(bulk_temperature_k, fluid)
    density_ratio = fluid.density_kg_m3 / max(anchor, 1e-9)
    cp_ratio = fluid.cp_j_kgk / max(fluid.cp_j_kgk, 1e-9)
    deviation = abs(density_ratio - 1.0) + abs(cp_ratio - 1.0) * 0.1
    return max(0.0, 1.0 - min(deviation, 1.0))


def density_correction_factor(fluid: FluidSpec, bulk_temperature_k: float) -> float:
    row = row_by_name(fluid.name)
    anchor = _anchor_density(bulk_temperature_k, fluid)
    if row is not None:
        _, _, t_ref, rho_ref, _, _, _, beta, _, _ = row
        delta = bulk_temperature_k - t_ref
        thermal = 1.0 - beta * delta
        catalog = rho_ref / max(anchor, 1e-9)
        return max(0.96, min(1.04, 0.5 * thermal + 0.5 * catalog))
    neighbors = rows_for_temperature(bulk_temperature_k, limit=1)
    if not neighbors:
        return 1.0
    _, model, t_ref, rho, _, _, _, _, _, _ = neighbors[0]
    if (fluid.model == "ideal_gas") != (model == "ideal_gas"):
        return 1.0
    weight = max(0.0, 1.0 - abs(bulk_temperature_k - t_ref) / 200.0)
    if weight <= 0.0:
        return 1.0
    target = rho / max(fluid.density_kg_m3, 1e-9)
    return max(0.9, min(1.1, (1.0 - weight) + weight * target))


def catalog_property_delta(case: CaseSpec, bulk_temperature_k: float) -> float:
    anchor = _anchor_density(bulk_temperature_k, case.fluid)
    return abs(anchor - case.fluid.density_kg_m3) + abs(case.fluid.cp_j_kgk - case.fluid.cp_j_kgk) * 0.0


def registry_digest() -> str:
    return f"rows={len(_NAMED_ROWS)} anchors={len(_TEMPERATURE_ANCHORS)}"
