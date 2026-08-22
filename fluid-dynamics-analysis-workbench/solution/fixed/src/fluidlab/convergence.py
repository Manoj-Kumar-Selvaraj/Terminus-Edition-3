from __future__ import annotations

from .models import CaseSpec
from .physics.convergence_diagnostics import convergence_diagnostics
from .physics.residual_engine import convergence_pressure


def _residual_summary(values: list[float]) -> dict[str, float]:
    tail = values[-3:] if len(values) >= 3 else values
    return {
        "initial": values[0],
        "final": values[-1],
        "tail_mean": sum(tail) / len(tail),
        "decay_ratio": values[-1] / max(values[0], 1e-12),
    }


def convergence_summary(case: CaseSpec) -> dict[str, object]:
    monitor = case.solver_monitor
    diagnostics = convergence_diagnostics(case)
    continuity = _residual_summary(monitor.continuity_residual)
    momentum = _residual_summary(monitor.momentum_residual)
    energy = _residual_summary(monitor.energy_residual)
    final_residual = float(diagnostics["final_residual"])
    converged = (
        final_residual <= case.limits.max_final_residual
        and monitor.mass_imbalance_percent <= case.limits.max_mass_imbalance_percent
        and monitor.energy_imbalance_percent <= case.limits.max_energy_imbalance_percent
        and monitor.iterations <= monitor.target_iterations
        and diagnostics["quality"] >= 0.0
    )
    return {
        "converged": converged,
        "iterations": monitor.iterations,
        "target_iterations": monitor.target_iterations,
        "mass_imbalance_percent": monitor.mass_imbalance_percent,
        "energy_imbalance_percent": monitor.energy_imbalance_percent,
        "residuals": {
            "continuity": continuity,
            "momentum": momentum,
            "energy": energy,
        },
        "final_residual": final_residual,
        "convergence_pressure": convergence_pressure(case),
        "diagnostics": diagnostics,
    }
