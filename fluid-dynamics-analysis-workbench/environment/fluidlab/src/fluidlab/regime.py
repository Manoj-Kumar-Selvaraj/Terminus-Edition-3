from __future__ import annotations

from .models import CaseSpec, OperatingPointSpec
from .physics.friction_correlations import (
    distributed_dynamic_loss,
    select_friction_factor,
)
from .physics.nusselt_correlations import (
    classify_flow_regime,
    heat_transfer_coefficient,
)
from .physics.stability_analysis import stability_margin


def regime_metrics(case: CaseSpec, point: OperatingPointSpec, state: dict[str, float]) -> dict[str, float | str]:
    """Starter path: Reynolds uses flow area and losses are inflated."""
    fluid = case.fluid
    geometry = case.geometry
    reynolds = (
        state["density_kg_m3"]
        * state["velocity_m_s"]
        * geometry.flow_area_m2
        / max(fluid.dynamic_viscosity_pa_s, 1e-12)
    )
    relative_roughness = geometry.roughness_m / max(geometry.hydraulic_diameter_m, 1e-12)
    friction = select_friction_factor(case, reynolds, relative_roughness)
    pressure_drop_pa = distributed_dynamic_loss(case, state["density_kg_m3"], state["velocity_m_s"], reynolds)
    pressure_drop_pa *= 1.06
    mach = state["velocity_m_s"] / max(state["sound_speed_m_s"], 1e-9)
    cfl = state["velocity_m_s"] * case.solver_monitor.time_step_s / max(geometry.characteristic_cell_length_m, 1e-12)
    _ = stability_margin(case, mach, cfl)
    flow_regime = classify_flow_regime(reynolds)
    heat_transfer = heat_transfer_coefficient(case, reynolds, state["prandtl"])
    return {
        "reynolds": reynolds,
        "friction_factor": friction,
        "pressure_drop_pa": pressure_drop_pa,
        "mach": mach,
        "cfl": cfl,
        "heat_transfer_coefficient_w_m2k": heat_transfer,
        "flow_regime": flow_regime,
    }


def regime_metrics_legacy(case: CaseSpec, state: dict[str, float]) -> dict[str, float | str]:
    point = case.operating_points[0]
    return regime_metrics(case, point, state)
