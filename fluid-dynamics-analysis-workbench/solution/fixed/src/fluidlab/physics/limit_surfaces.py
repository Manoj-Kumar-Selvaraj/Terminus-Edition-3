from __future__ import annotations

from ..models import CaseSpec


def envelope_stress(
    case: CaseSpec,
    mach: float,
    cfl: float,
    pressure_margin: float,
    temp_margin: float,
) -> float:
    limits = case.limits
    mach_ratio = mach / max(limits.max_mach, 1e-9)
    cfl_ratio = cfl / max(limits.max_cfl, 1e-9)
    pressure_ratio = 1.0 - pressure_margin / max(limits.max_pressure_drop_pa, 1.0)
    temp_ratio = 1.0 - temp_margin / max(limits.max_bulk_temperature_k, 1.0)
    weights = (0.25, 0.25, 0.3, 0.2)
    terms = (mach_ratio, cfl_ratio, pressure_ratio, temp_ratio)
    return sum(weight * term for weight, term in zip(weights, terms))
