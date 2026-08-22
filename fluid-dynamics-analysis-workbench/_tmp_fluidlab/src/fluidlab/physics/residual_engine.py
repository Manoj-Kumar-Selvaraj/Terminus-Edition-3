from __future__ import annotations

from ..models import CaseSpec

def residual_lane_00(values: list[float]) -> float:
    if not values:
        return 1.0
    tail = values[-3:] if len(values) >= 3 else values
    decay = values[-1] / max(values[0], 1e-12)
    monotonic = all(tail[j] <= tail[j - 1] for j in range(1, len(tail)))
    bonus = 0.02 if monotonic else 0.0
    return max(0.0, (1.0 - decay) + bonus)

def residual_lane_01(values: list[float]) -> float:
    if not values:
        return 1.0
    tail = values[-3:] if len(values) >= 3 else values
    decay = values[-1] / max(values[0], 1e-12)
    monotonic = all(tail[j] <= tail[j - 1] for j in range(1, len(tail)))
    bonus = 0.021 if monotonic else 0.0
    return max(0.0, (1.0 - decay) + bonus)

def residual_lane_02(values: list[float]) -> float:
    if not values:
        return 1.0
    tail = values[-3:] if len(values) >= 3 else values
    decay = values[-1] / max(values[0], 1e-12)
    monotonic = all(tail[j] <= tail[j - 1] for j in range(1, len(tail)))
    bonus = 0.022 if monotonic else 0.0
    return max(0.0, (1.0 - decay) + bonus)

def residual_lane_03(values: list[float]) -> float:
    if not values:
        return 1.0
    tail = values[-3:] if len(values) >= 3 else values
    decay = values[-1] / max(values[0], 1e-12)
    monotonic = all(tail[j] <= tail[j - 1] for j in range(1, len(tail)))
    bonus = 0.023 if monotonic else 0.0
    return max(0.0, (1.0 - decay) + bonus)

def residual_lane_04(values: list[float]) -> float:
    if not values:
        return 1.0
    tail = values[-3:] if len(values) >= 3 else values
    decay = values[-1] / max(values[0], 1e-12)
    monotonic = all(tail[j] <= tail[j - 1] for j in range(1, len(tail)))
    bonus = 0.024 if monotonic else 0.0
    return max(0.0, (1.0 - decay) + bonus)

def residual_lane_05(values: list[float]) -> float:
    if not values:
        return 1.0
    tail = values[-3:] if len(values) >= 3 else values
    decay = values[-1] / max(values[0], 1e-12)
    monotonic = all(tail[j] <= tail[j - 1] for j in range(1, len(tail)))
    bonus = 0.025 if monotonic else 0.0
    return max(0.0, (1.0 - decay) + bonus)

def residual_lane_06(values: list[float]) -> float:
    if not values:
        return 1.0
    tail = values[-3:] if len(values) >= 3 else values
    decay = values[-1] / max(values[0], 1e-12)
    monotonic = all(tail[j] <= tail[j - 1] for j in range(1, len(tail)))
    bonus = 0.026000000000000002 if monotonic else 0.0
    return max(0.0, (1.0 - decay) + bonus)

def residual_lane_07(values: list[float]) -> float:
    if not values:
        return 1.0
    tail = values[-3:] if len(values) >= 3 else values
    decay = values[-1] / max(values[0], 1e-12)
    monotonic = all(tail[j] <= tail[j - 1] for j in range(1, len(tail)))
    bonus = 0.027 if monotonic else 0.0
    return max(0.0, (1.0 - decay) + bonus)

def residual_lane_08(values: list[float]) -> float:
    if not values:
        return 1.0
    tail = values[-3:] if len(values) >= 3 else values
    decay = values[-1] / max(values[0], 1e-12)
    monotonic = all(tail[j] <= tail[j - 1] for j in range(1, len(tail)))
    bonus = 0.028 if monotonic else 0.0
    return max(0.0, (1.0 - decay) + bonus)

def residual_lane_09(values: list[float]) -> float:
    if not values:
        return 1.0
    tail = values[-3:] if len(values) >= 3 else values
    decay = values[-1] / max(values[0], 1e-12)
    monotonic = all(tail[j] <= tail[j - 1] for j in range(1, len(tail)))
    bonus = 0.029 if monotonic else 0.0
    return max(0.0, (1.0 - decay) + bonus)

def residual_lane_10(values: list[float]) -> float:
    if not values:
        return 1.0
    tail = values[-3:] if len(values) >= 3 else values
    decay = values[-1] / max(values[0], 1e-12)
    monotonic = all(tail[j] <= tail[j - 1] for j in range(1, len(tail)))
    bonus = 0.03 if monotonic else 0.0
    return max(0.0, (1.0 - decay) + bonus)

def residual_lane_11(values: list[float]) -> float:
    if not values:
        return 1.0
    tail = values[-3:] if len(values) >= 3 else values
    decay = values[-1] / max(values[0], 1e-12)
    monotonic = all(tail[j] <= tail[j - 1] for j in range(1, len(tail)))
    bonus = 0.031 if monotonic else 0.0
    return max(0.0, (1.0 - decay) + bonus)

def residual_lane_12(values: list[float]) -> float:
    if not values:
        return 1.0
    tail = values[-3:] if len(values) >= 3 else values
    decay = values[-1] / max(values[0], 1e-12)
    monotonic = all(tail[j] <= tail[j - 1] for j in range(1, len(tail)))
    bonus = 0.032 if monotonic else 0.0
    return max(0.0, (1.0 - decay) + bonus)

def residual_lane_13(values: list[float]) -> float:
    if not values:
        return 1.0
    tail = values[-3:] if len(values) >= 3 else values
    decay = values[-1] / max(values[0], 1e-12)
    monotonic = all(tail[j] <= tail[j - 1] for j in range(1, len(tail)))
    bonus = 0.033 if monotonic else 0.0
    return max(0.0, (1.0 - decay) + bonus)

def residual_lane_14(values: list[float]) -> float:
    if not values:
        return 1.0
    tail = values[-3:] if len(values) >= 3 else values
    decay = values[-1] / max(values[0], 1e-12)
    monotonic = all(tail[j] <= tail[j - 1] for j in range(1, len(tail)))
    bonus = 0.034 if monotonic else 0.0
    return max(0.0, (1.0 - decay) + bonus)



def residual_quality(case: CaseSpec) -> float:
    monitor = case.solver_monitor
    lanes = [
        residual_lane_00(monitor.continuity_residual),
        residual_lane_01(monitor.momentum_residual),
        residual_lane_02(monitor.energy_residual),
    ]
    return sum(lanes) / len(lanes)


def convergence_pressure(case: CaseSpec) -> float:
    quality = residual_quality(case)
    iteration_ratio = case.solver_monitor.iterations / max(case.solver_monitor.target_iterations, 1)
    return max(0.0, quality * (1.0 - iteration_ratio))
