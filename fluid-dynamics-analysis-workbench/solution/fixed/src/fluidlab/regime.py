from __future__ import annotations

from .friction_models import pressure_drop_for_case
from .heat_transfer import classify_flow_regime, heat_transfer_coefficient_w_m2k
from .models import CaseSpec, OperatingPointSpec


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
    pressure_drop_pa = pressure_drop_for_case(
        case,
        point.inlet_total_pressure_pa,
        point.outlet_static_pressure_pa,
        state["density_kg_m3"],
        state["velocity_m_s"],
        reynolds,
    )
    mach = state["velocity_m_s"] / max(state["sound_speed_m_s"], 1e-9)
    cfl = state["velocity_m_s"] * case.solver_monitor.time_step_s / max(geometry.characteristic_cell_length_m, 1e-12)
    flow_regime = classify_flow_regime(reynolds)
    heat_transfer_coefficient = heat_transfer_coefficient_w_m2k(case, reynolds, state["prandtl"])
    dynamic_pressure = max(0.5 * state["density_kg_m3"] * state["velocity_m_s"] ** 2, 1e-9)
    return {
        "reynolds": reynolds,
        "friction_factor": pressure_drop_pa / dynamic_pressure,
        "pressure_drop_pa": pressure_drop_pa,
        "mach": mach,
        "cfl": cfl,
        "heat_transfer_coefficient_w_m2k": heat_transfer_coefficient,
        "flow_regime": flow_regime,
    }
