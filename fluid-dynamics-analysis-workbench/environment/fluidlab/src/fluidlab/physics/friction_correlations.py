from __future__ import annotations

import math

from ..models import CaseSpec
from .correlation_policy import friction_policy_factor
from .roughness_profiles import roughness_multiplier


def colebrook_haaland_blend(reynolds: float, relative_roughness: float) -> float:
    if reynolds <= 0.0:
        return 0.0
    if reynolds < 2300.0:
        return 64.0 / reynolds
    a = (2.457 * math.log(1.0 / (((7.0 / reynolds) ** 0.9) + 0.27 * relative_roughness))) ** 16
    b = (37530.0 / reynolds) ** 16
    core = 8.0 * (((8.0 / reynolds) ** 12) + (1.0 / ((a + b) ** 1.5))) ** (1.0 / 12.0)
    return core


def select_friction_factor(case: CaseSpec, reynolds: float, relative_roughness: float) -> float:
    base = colebrook_haaland_blend(reynolds, relative_roughness)
    policy = friction_policy_factor(case, reynolds, relative_roughness)
    roughness = roughness_multiplier(case.geometry.roughness_m, case.geometry.hydraulic_diameter_m)
    return base * policy * roughness


def distributed_dynamic_loss(
    case: CaseSpec,
    density_kg_m3: float,
    velocity_m_s: float,
    reynolds: float,
) -> float:
    from .segment_hydraulics import segmented_dynamic_loss

    return segmented_dynamic_loss(case, density_kg_m3, velocity_m_s, reynolds)
