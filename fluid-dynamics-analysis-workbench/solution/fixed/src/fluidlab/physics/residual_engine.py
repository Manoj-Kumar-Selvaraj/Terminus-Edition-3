from __future__ import annotations

from ..models import CaseSpec


def _residual_quality(values: list[float]) -> float:
    if not values:
        return 0.0
    tail = values[-3:] if len(values) >= 3 else values
    decay = values[-1] / max(values[0], 1e-12)
    monotonic = all(tail[index] <= tail[index - 1] for index in range(1, len(tail)))
    bonus = 0.02 if monotonic else 0.0
    return max(0.0, (1.0 - decay) + bonus)


def residual_quality(case: CaseSpec) -> float:
    monitor = case.solver_monitor
    samples = (
        _residual_quality(monitor.continuity_residual),
        _residual_quality(monitor.momentum_residual),
        _residual_quality(monitor.energy_residual),
    )
    return sum(samples) / len(samples)


def convergence_pressure(case: CaseSpec) -> float:
    quality = residual_quality(case)
    iteration_ratio = case.solver_monitor.iterations / max(case.solver_monitor.target_iterations, 1)
    return max(0.0, quality * (1.0 - iteration_ratio))
