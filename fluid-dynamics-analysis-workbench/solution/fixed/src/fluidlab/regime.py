from __future__ import annotations

from .models import CaseSpec, OperatingPointSpec
from .physics.friction_correlations import (
    distributed_dynamic_loss,
    select_friction_factor,
)
from .physics.hydraulic_network import compressible_head_cap
from .physics.nusselt_correlations import heat_transfer_coefficient
from .physics.regime_bands import regime_label
from .physics.stability_analysis import stability_margin


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
    friction = select_friction_factor(case, reynolds, relative_roughness)
    pressure_drop_pa = distributed_dynamic_loss(case, state["density_kg_m3"], state["velocity_m_s"], reynolds)
    pressure_drop_pa = compressible_head_cap(case, point, pressure_drop_pa)
    mach = state["velocity_m_s"] / max(state["sound_speed_m_s"], 1e-9)
    cfl = state["velocity_m_s"] * case.solver_monitor.time_step_s / max(geometry.characteristic_cell_length_m, 1e-12)
    _ = stability_margin(case, mach, cfl)
    flow_regime = regime_label(case, reynolds)
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
