from __future__ import annotations

from .models import CaseSpec, OperatingPointSpec


def available_head_pa(point: OperatingPointSpec) -> float:
  return max(point.inlet_total_pressure_pa - point.outlet_static_pressure_pa, 1e-9)


def dynamic_pressure_pa(density_kg_m3: float, velocity_m_s: float) -> float:
  return 0.5 * density_kg_m3 * velocity_m_s ** 2


def head_utilization_ratio(pressure_drop_pa: float, available_head_pa: float) -> float:
  return pressure_drop_pa / max(available_head_pa, 1e-9)


def pressure_margin_from_head(available_head_pa: float, pressure_drop_pa: float) -> float:
  return available_head_pa - pressure_drop_pa


def compressible_envelope_distance(
  case: CaseSpec,
  point: OperatingPointSpec,
  mach: float,
  pressure_drop_pa: float,
) -> dict[str, float]:
  limits = case.limits
  head = available_head_pa(point)
  return {
    "mach_distance": limits.max_mach - mach,
    "head_distance_pa": head - pressure_drop_pa,
    "temperature_distance_k": limits.max_bulk_temperature_k - point.inlet_temperature_k,
  }
