from __future__ import annotations

from ..models import CaseSpec, OperatingPointSpec


def wall_heat_flux(point: OperatingPointSpec, bulk_k: float, h_w_m2k: float) -> float:
    delta_t = point.wall_temperature_k - bulk_k
    return h_w_m2k * delta_t


def axial_conduction_correction(
    case: CaseSpec,
    bulk_k: float,
    outlet_k: float,
) -> float:
    geometry = case.geometry
    conductivity = case.fluid.thermal_conductivity_w_mk
    area = geometry.heat_exchange_area_m2
    length = geometry.length_m
    if length <= 0.0:
        return bulk_k
    u_value = conductivity * area / max(length, 1e-9)
    gradient = (outlet_k - bulk_k) * u_value / max(case.fluid.cp_j_kgk * area, 1e-9)
    return bulk_k + 0.05 * gradient


def refined_bulk_temperature(
    case: CaseSpec,
    point: OperatingPointSpec,
    preliminary_bulk_k: float,
    outlet_k: float,
    h_w_m2k: float,
) -> float:
    wall_flux = wall_heat_flux(point, preliminary_bulk_k, h_w_m2k)
    rise = point.heat_load_w / max(point.mass_flow_kg_s * case.fluid.cp_j_kgk, 1e-9)
    conduction = axial_conduction_correction(case, preliminary_bulk_k, outlet_k)
    mixed = 0.5 * (point.inlet_temperature_k + outlet_k)
    correction = wall_flux / max(h_w_m2k, 1e-9) * 0.02
    return max(250.0, min(2000.0, 0.6 * mixed + 0.25 * conduction + 0.15 * (preliminary_bulk_k + correction)))
