from __future__ import annotations

from ..models import CaseSpec
from .correlation_policy import nusselt_policy_factor


def blended_nusselt(reynolds: float, prandtl: float) -> float:
    if reynolds < 2300.0:
        return 3.66
    if reynolds < 4000.0:
        return 0.021 * (reynolds ** 0.8) * (prandtl ** 0.4)
    return 0.023 * (reynolds ** 0.8) * (prandtl ** 0.4)


def heat_transfer_coefficient(case: CaseSpec, reynolds: float, prandtl: float) -> float:
    nusselt = blended_nusselt(reynolds, prandtl) * nusselt_policy_factor(case, reynolds, prandtl)
    return nusselt * case.fluid.thermal_conductivity_w_mk / max(case.geometry.hydraulic_diameter_m, 1e-12)


def classify_flow_regime(reynolds: float) -> str:
    if reynolds < 2300.0:
        return "laminar"
    if reynolds < 4000.0:
        return "transitional"
    return "turbulent"
