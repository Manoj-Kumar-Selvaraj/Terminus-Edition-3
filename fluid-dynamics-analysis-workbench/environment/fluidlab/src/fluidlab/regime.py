from __future__ import annotations

from .friction_models import distributed_pressure_drop_pa
from .heat_transfer import classify_flow_regime, heat_transfer_coefficient_w_m2k
from .models import CaseSpec


def regime_metrics(case: CaseSpec, state: dict[str, float]) -> dict[str, float | str]:
    fluid = case.fluid
    geometry = case.geometry
    reynolds = (
        state["density_kg_m3"]
        * state["velocity_m_s"]
        * geometry.flow_area_m2
        / max(fluid.dynamic_viscosity_pa_s, 1e-12)
    )
    relative_roughness = geometry.roughness_m / max(geometry.hydraulic_diameter_m, 1e-12)
    pressure_drop_pa = distributed_pressure_drop_pa(
        geometry,
        state["density_kg_m3"],
        state["velocity_m_s"],
        reynolds,
        relative_roughness,
    )
    mach = state["velocity_m_s"] / max(state["sound_speed_m_s"], 1e-9)
    cfl = state["velocity_m_s"] * case.solver_monitor.time_step_s / max(geometry.characteristic_cell_length_m, 1e-12)
    flow_regime = classify_flow_regime(reynolds)
    heat_transfer_coefficient = heat_transfer_coefficient_w_m2k(case, reynolds, state["prandtl"])
    return {
        "reynolds": reynolds,
        "friction_factor": pressure_drop_pa / max(0.5 * state["density_kg_m3"] * state["velocity_m_s"] ** 2, 1e-9),
        "pressure_drop_pa": pressure_drop_pa,
        "mach": mach,
        "cfl": cfl,
        "heat_transfer_coefficient_w_m2k": heat_transfer_coefficient,
        "flow_regime": flow_regime,
    }
