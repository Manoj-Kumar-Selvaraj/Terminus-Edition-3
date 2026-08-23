from __future__ import annotations

from .models import CaseSpec


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
    continuity = _residual_summary(monitor.continuity_residual)
    momentum = _residual_summary(monitor.momentum_residual)
    energy = _residual_summary(monitor.energy_residual)
    final_residual = max(continuity["final"], momentum["final"], energy["final"])
    converged = (
        final_residual <= case.limits.max_final_residual
        and monitor.mass_imbalance_percent <= case.limits.max_mass_imbalance_percent
        and monitor.energy_imbalance_percent <= case.limits.max_energy_imbalance_percent
        and monitor.iterations <= monitor.target_iterations
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
    }
