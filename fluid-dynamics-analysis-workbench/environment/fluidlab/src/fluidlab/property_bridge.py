from __future__ import annotations

import math
from pathlib import Path

from .models import CaseSpec, OperatingPointSpec
from .reference_catalog import nearest_fluid_entries


def temperature_rise_k(point: OperatingPointSpec, cp_j_kgk: float) -> float:
  return point.heat_load_w / max(point.mass_flow_kg_s * cp_j_kgk, 1e-9)


def bulk_temperature_k(inlet_k: float, rise_k: float) -> float:
  return inlet_k + 0.5 * rise_k


def liquid_density_kg_m3(
  reference_density: float,
  bulk_temperature_k: float,
  reference_temperature_k: float,
  thermal_expansion_per_k: float,
) -> float:
  delta = bulk_temperature_k - reference_temperature_k
  return reference_density * (1.0 - thermal_expansion_per_k * delta)


def ideal_gas_density_kg_m3(
  inlet_total_pressure_pa: float,
  outlet_static_pressure_pa: float,
  bulk_temperature_k: float,
  gas_constant_j_kgk: float,
) -> float:
  representative_pressure = 0.5 * (inlet_total_pressure_pa + outlet_static_pressure_pa)
  return representative_pressure / max(gas_constant_j_kgk * bulk_temperature_k, 1e-9)


def ideal_gas_sound_speed(gamma: float, gas_constant_j_kgk: float, bulk_temperature_k: float) -> float:
  return math.sqrt(max(gamma * gas_constant_j_kgk * bulk_temperature_k, 1e-9))


def catalog_property_delta(root: Path, case: CaseSpec, bulk_temperature_k: float) -> float:
  nearest = nearest_fluid_entries(root, bulk_temperature_k, limit=1)
  if not nearest:
    return 0.0
  entry = nearest[0]
  density_delta = abs(float(entry["density_kg_m3"]) - case.fluid.density_kg_m3)
  cp_delta = abs(float(entry["cp_j_kgk"]) - case.fluid.cp_j_kgk)
  return density_delta + cp_delta


def compute_state(
  root: Path,
  case: CaseSpec,
  point: OperatingPointSpec,
) -> dict[str, float]:
  fluid = case.fluid
  geometry = case.geometry
  rise = temperature_rise_k(point, fluid.cp_j_kgk)
  outlet_temperature_k = point.inlet_temperature_k + rise
  bulk = bulk_temperature_k(point.inlet_temperature_k, rise)
  if fluid.model == "ideal_gas":
    density_kg_m3 = ideal_gas_density_kg_m3(
      point.inlet_total_pressure_pa,
      point.outlet_static_pressure_pa,
      bulk,
      fluid.gas_constant_j_kgk,
    )
    sound_speed_m_s = ideal_gas_sound_speed(fluid.gamma, fluid.gas_constant_j_kgk, bulk)
  else:
    density_kg_m3 = liquid_density_kg_m3(
      fluid.density_kg_m3,
      bulk,
      fluid.reference_temperature_k,
      fluid.thermal_expansion_per_k,
    )
    sound_speed_m_s = 1450.0
  density_kg_m3 = max(density_kg_m3, 1e-6)
  velocity_m_s = point.mass_flow_kg_s / max(density_kg_m3 * geometry.flow_area_m2, 1e-9)
  prandtl = fluid.cp_j_kgk * fluid.dynamic_viscosity_pa_s / max(fluid.thermal_conductivity_w_mk, 1e-9)
  catalog_delta = catalog_property_delta(root, case, bulk)
  return {
    "temperature_rise_k": rise,
    "bulk_temperature_k": bulk,
    "outlet_temperature_k": outlet_temperature_k,
    "density_kg_m3": density_kg_m3,
    "velocity_m_s": velocity_m_s,
    "sound_speed_m_s": sound_speed_m_s,
    "prandtl": prandtl,
    "catalog_property_delta": catalog_delta,
  }
