from __future__ import annotations

import math

from .models import CaseSpec, OperatingPointSpec
from .physics.property_registry import (
    catalog_property_delta,
    density_correction_factor,
    property_consistency_score,
)
from .physics.transport_models import (
    liquid_density_with_expansion,
    representative_gas_density,
)


def temperature_rise_k(point: OperatingPointSpec, cp_j_kgk: float) -> float:
    return point.heat_load_w / max(point.mass_flow_kg_s * cp_j_kgk, 1e-9)


def bulk_temperature_k(inlet_k: float, rise_k: float) -> float:
    return inlet_k + 0.5 * rise_k


def compute_state(case: CaseSpec, point: OperatingPointSpec) -> dict[str, float]:
    fluid = case.fluid
    geometry = case.geometry
    rise = temperature_rise_k(point, fluid.cp_j_kgk)
    outlet_temperature_k = point.inlet_temperature_k + rise
    bulk = bulk_temperature_k(point.inlet_temperature_k, rise)
    if fluid.model == "ideal_gas":
        density_kg_m3 = representative_gas_density(
            point.inlet_total_pressure_pa,
            point.outlet_static_pressure_pa,
            bulk,
            fluid.gas_constant_j_kgk,
            fluid.gamma,
        )
        sound_speed_m_s = math.sqrt(max(fluid.gamma * fluid.gas_constant_j_kgk * bulk, 1e-9))
    else:
        density_kg_m3 = liquid_density_with_expansion(
            fluid.density_kg_m3,
            bulk,
            fluid.reference_temperature_k,
            fluid.thermal_expansion_per_k,
        )
        sound_speed_m_s = 1450.0
    density_kg_m3 *= density_correction_factor(fluid, bulk)
    density_kg_m3 = max(density_kg_m3, 1e-6)
    velocity_m_s = point.mass_flow_kg_s / max(density_kg_m3 * geometry.flow_area_m2, 1e-9)
    prandtl = fluid.cp_j_kgk * fluid.dynamic_viscosity_pa_s / max(fluid.thermal_conductivity_w_mk, 1e-9)
    return {
        "temperature_rise_k": rise,
        "bulk_temperature_k": bulk,
        "outlet_temperature_k": outlet_temperature_k,
        "density_kg_m3": density_kg_m3,
        "velocity_m_s": velocity_m_s,
        "sound_speed_m_s": sound_speed_m_s,
        "prandtl": prandtl,
        "catalog_property_delta": catalog_property_delta(case, bulk),
        "property_consistency_score": property_consistency_score(fluid, bulk),
    }
