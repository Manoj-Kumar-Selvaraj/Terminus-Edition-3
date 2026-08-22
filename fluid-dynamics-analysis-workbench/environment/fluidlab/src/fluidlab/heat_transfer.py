from __future__ import annotations

import math

from .models import CaseSpec


def laminar_nusselt() -> float:
  return 3.66


def transitional_nusselt(reynolds: float, prandtl: float) -> float:
  return 0.021 * (reynolds ** 0.8) * (prandtl ** 0.4)


def turbulent_nusselt(reynolds: float, prandtl: float) -> float:
  return 0.023 * (reynolds ** 0.8) * (prandtl ** 0.4)


def gnielinski_nusselt(reynolds: float, prandtl: float) -> float:
  friction = (reynolds - 1000.0) / 1000.0
  numerator = (friction / 8.0) * (reynolds - 1000.0) * prandtl
  denominator = 1.0 + 12.7 * math.sqrt(friction / 8.0) * (prandtl ** (2.0 / 3.0) - 1.0)
  return numerator / max(denominator, 1e-9)


def classify_flow_regime(reynolds: float) -> str:
  if reynolds < 2300.0:
    return "laminar"
  if reynolds < 4000.0:
    return "transitional"
  return "turbulent"


def nusselt_for_regime(reynolds: float, prandtl: float) -> float:
  regime = classify_flow_regime(reynolds)
  if regime == "laminar":
    return laminar_nusselt()
  if regime == "transitional":
    return transitional_nusselt(reynolds, prandtl)
  return turbulent_nusselt(reynolds, prandtl)


def heat_transfer_coefficient_w_m2k(
  case: CaseSpec,
  reynolds: float,
  prandtl: float,
) -> float:
  nusselt = nusselt_for_regime(reynolds, prandtl)
  return nusselt * case.fluid.thermal_conductivity_w_mk / max(case.geometry.hydraulic_diameter_m, 1e-12)


def bulk_temperature_rise(heat_load_w: float, mass_flow_kg_s: float, cp_j_kgk: float) -> float:
  return heat_load_w / max(mass_flow_kg_s * cp_j_kgk, 1e-9)


def log_mean_temperature_delta(inlet_k: float, outlet_k: float, wall_k: float) -> float:
  hot = max(inlet_k, outlet_k)
  cold = min(inlet_k, outlet_k)
  delta1 = wall_k - hot
  delta2 = wall_k - cold
  if abs(delta1 - delta2) < 1e-9:
    return delta1
  return (delta1 - delta2) / math.log(max(delta1, 1e-9) / max(delta2, 1e-9))
