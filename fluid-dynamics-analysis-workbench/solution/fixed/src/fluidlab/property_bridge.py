from __future__ import annotations

import math

from .models import CaseSpec, OperatingPointSpec
from .physics.fluid_property_models import effective_properties
from .physics.property_registry import (
    catalog_property_delta,
    density_correction_factor,
    property_consistency_score,
)
from .physics.thermal_balance import refined_bulk_temperature
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
    props = effective_properties(fluid, point.inlet_temperature_k)
    cp = props["cp_j_kgk"]
    rise = temperature_rise_k(point, cp)
    outlet_temperature_k = point.inlet_temperature_k + rise
    preliminary_bulk = bulk_temperature_k(point.inlet_temperature_k, rise)
    bulk = refined_bulk_temperature(
        case,
        point,
        preliminary_bulk,
        outlet_temperature_k,
        props["thermal_conductivity_w_mk"] * 10.0 / max(geometry.hydraulic_diameter_m, 1e-12),
    )
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
    prandtl = cp * props["dynamic_viscosity_pa_s"] / max(props["thermal_conductivity_w_mk"], 1e-9)
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
