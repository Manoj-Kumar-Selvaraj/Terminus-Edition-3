from __future__ import annotations

import math

from .models import CaseSpec, OperatingPointSpec


def compute_state(case: CaseSpec, point: OperatingPointSpec) -> dict[str, float]:
    fluid = case.fluid
    geometry = case.geometry
    temperature_rise = point.heat_load_w / max(point.mass_flow_kg_s * fluid.cp_j_kgk, 1e-9)
    outlet_temperature_k = point.inlet_temperature_k + temperature_rise
    bulk_temperature_k = point.inlet_temperature_k + 0.5 * temperature_rise
    reference_delta = bulk_temperature_k - fluid.reference_temperature_k
    if fluid.model == "ideal_gas":
        representative_pressure = 0.5 * (point.inlet_total_pressure_pa + point.outlet_static_pressure_pa)
        density_kg_m3 = representative_pressure / max(fluid.gas_constant_j_kgk * bulk_temperature_k, 1e-9)
        sound_speed_m_s = math.sqrt(max(fluid.gamma * fluid.gas_constant_j_kgk * bulk_temperature_k, 1e-9))
    else:
        density_kg_m3 = fluid.density_kg_m3 * (1.0 - fluid.thermal_expansion_per_k * reference_delta)
        sound_speed_m_s = 1450.0
    density_kg_m3 = max(density_kg_m3, 1e-6)
    velocity_m_s = point.mass_flow_kg_s / max(density_kg_m3 * geometry.flow_area_m2, 1e-9)
    prandtl = fluid.cp_j_kgk * fluid.dynamic_viscosity_pa_s / max(fluid.thermal_conductivity_w_mk, 1e-9)
    return {
        "temperature_rise_k": temperature_rise,
        "bulk_temperature_k": bulk_temperature_k,
        "outlet_temperature_k": outlet_temperature_k,
        "density_kg_m3": density_kg_m3,
        "velocity_m_s": velocity_m_s,
        "sound_speed_m_s": sound_speed_m_s,
        "prandtl": prandtl,
    }
