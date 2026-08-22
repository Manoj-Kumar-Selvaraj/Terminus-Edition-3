from __future__ import annotations

import math

from .models import CaseSpec, GeometrySpec


def friction_factor(reynolds: float, relative_roughness: float) -> float:
  if reynolds <= 0.0:
    return 0.0
  if reynolds < 2300.0:
    return 64.0 / reynolds
  a = (2.457 * math.log(1.0 / (((7.0 / reynolds) ** 0.9) + 0.27 * relative_roughness))) ** 16
  b = (37530.0 / reynolds) ** 16
  return 8.0 * (((8.0 / reynolds) ** 12) + (1.0 / ((a + b) ** 1.5))) ** (1.0 / 12.0)


def haaland_factor(reynolds: float, relative_roughness: float) -> float:
  if reynolds <= 0.0:
    return 0.0
  term = relative_roughness / 3.7 + 6.9 / reynolds
  return 1.0 / (-1.8 * math.log10(term)) ** 2


def distributed_pressure_drop_pa(
  geometry: GeometrySpec,
  density_kg_m3: float,
  velocity_m_s: float,
  reynolds: float,
  relative_roughness: float,
  *,
  inflate: float = 1.0,
) -> float:
  friction = friction_factor(reynolds, relative_roughness)
  dynamic_pressure_pa = 0.5 * density_kg_m3 * velocity_m_s ** 2
  length_term = friction * geometry.length_m / max(geometry.hydraulic_diameter_m, 1e-12)
  minor_term = geometry.minor_loss_coefficient
  return (length_term + minor_term) * dynamic_pressure_pa * inflate


def compressible_head_limit_pa(case: CaseSpec, point_inlet_pa: float, point_outlet_pa: float) -> float:
  return max(point_inlet_pa - point_outlet_pa, 1e-9)


def pressure_drop_for_case(
  case: CaseSpec,
  point_inlet_pa: float,
  point_outlet_pa: float,
  density_kg_m3: float,
  velocity_m_s: float,
  reynolds: float,
) -> float:
  geometry = case.geometry
  relative_roughness = geometry.roughness_m / max(geometry.hydraulic_diameter_m, 1e-12)
  drop = distributed_pressure_drop_pa(
    geometry,
    density_kg_m3,
    velocity_m_s,
    reynolds,
    relative_roughness,
  )
  if case.fluid.model == "ideal_gas":
    available = compressible_head_limit_pa(case, point_inlet_pa, point_outlet_pa)
    drop = min(drop * 0.88, available * 0.92)
  return drop
