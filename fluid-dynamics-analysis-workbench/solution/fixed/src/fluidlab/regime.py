from __future__ import annotations

import math

from .models import CaseSpec, OperatingPointSpec


def _friction_factor(reynolds: float, relative_roughness: float) -> float:
    if reynolds <= 0.0:
        return 0.0
    if reynolds < 2300.0:
        return 64.0 / reynolds
    a = (2.457 * math.log(1.0 / (((7.0 / reynolds) ** 0.9) + 0.27 * relative_roughness))) ** 16
    b = (37530.0 / reynolds) ** 16
    return 8.0 * (((8.0 / reynolds) ** 12) + (1.0 / ((a + b) ** 1.5))) ** (1.0 / 12.0)


def regime_metrics(
    case: CaseSpec,
    point: OperatingPointSpec,
    state: dict[str, float],
) -> dict[str, float | str]:
    fluid = case.fluid
    geometry = case.geometry
    reynolds = (
        state["density_kg_m3"]
        * state["velocity_m_s"]
        * geometry.hydraulic_diameter_m
        / max(fluid.dynamic_viscosity_pa_s, 1e-12)
    )
    relative_roughness = geometry.roughness_m / max(geometry.hydraulic_diameter_m, 1e-12)
    friction_factor = _friction_factor(reynolds, relative_roughness)
    dynamic_pressure_pa = 0.5 * state["density_kg_m3"] * state["velocity_m_s"] ** 2
    pressure_drop_pa = (
        (friction_factor * geometry.length_m / max(geometry.hydraulic_diameter_m, 1e-12))
        + geometry.minor_loss_coefficient
    ) * dynamic_pressure_pa
    if case.fluid.model == "ideal_gas":
        available_head_pa = max(
            point.inlet_total_pressure_pa - point.outlet_static_pressure_pa,
            1e-9,
        )
        pressure_drop_pa = min(pressure_drop_pa * 0.88, available_head_pa * 0.92)
    mach = state["velocity_m_s"] / max(state["sound_speed_m_s"], 1e-9)
    cfl = state["velocity_m_s"] * case.solver_monitor.time_step_s / max(geometry.characteristic_cell_length_m, 1e-12)
    if reynolds < 2300.0:
        flow_regime = "laminar"
        nusselt = 3.66
    elif reynolds < 4000.0:
        flow_regime = "transitional"
        nusselt = 0.021 * (reynolds ** 0.8) * (state["prandtl"] ** 0.4)
    else:
        flow_regime = "turbulent"
        nusselt = 0.023 * (reynolds ** 0.8) * (state["prandtl"] ** 0.4)
    heat_transfer_coefficient = (
        nusselt * fluid.thermal_conductivity_w_mk / max(geometry.hydraulic_diameter_m, 1e-12)
    )
    return {
        "reynolds": reynolds,
        "friction_factor": friction_factor,
        "pressure_drop_pa": pressure_drop_pa,
        "mach": mach,
        "cfl": cfl,
        "heat_transfer_coefficient_w_m2k": heat_transfer_coefficient,
        "flow_regime": flow_regime,
    }
