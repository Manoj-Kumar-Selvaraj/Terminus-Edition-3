from __future__ import annotations

from ..models import CaseSpec
from .residual_engine import convergence_pressure, residual_quality


def residual_trend(values: list[float]) -> dict[str, float]:
    if not values:
        return {"initial": 0.0, "final": 0.0, "decay_ratio": 1.0, "monotonic": 0.0}
    tail = values[-3:] if len(values) >= 3 else values
    monotonic = 1.0 if all(tail[index] <= tail[index - 1] for index in range(1, len(tail))) else 0.0
    return {
        "initial": values[0],
        "final": values[-1],
        "decay_ratio": values[-1] / max(values[0], 1e-12),
        "monotonic": monotonic,
    }


def convergence_diagnostics(case: CaseSpec) -> dict[str, float]:
    monitor = case.solver_monitor
    continuity = residual_trend(monitor.continuity_residual)
    momentum = residual_trend(monitor.momentum_residual)
    energy = residual_trend(monitor.energy_residual)
    quality = residual_quality(case)
    pressure = convergence_pressure(case)
    final = max(continuity["final"], momentum["final"], energy["final"])
    return {
        "quality": quality,
        "pressure": pressure,
        "final_residual": final,
        "continuity_decay": continuity["decay_ratio"],
        "momentum_decay": momentum["decay_ratio"],
        "energy_decay": energy["decay_ratio"],
        "monotonic_score": (continuity["monotonic"] + momentum["monotonic"] + energy["monotonic"]) / 3.0,
    }
