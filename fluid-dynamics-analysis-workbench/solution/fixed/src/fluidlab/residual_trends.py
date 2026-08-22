from __future__ import annotations

from .models import CaseSpec


def residual_tail_mean(values: list[float], tail: int = 3) -> float:
  sample = values[-tail:] if len(values) >= tail else values
  return sum(sample) / len(sample)


def residual_decay_ratio(values: list[float]) -> float:
  return values[-1] / max(values[0], 1e-12)


def monotonic_tail(values: list[float], tail: int = 4) -> bool:
  sample = values[-tail:] if len(values) >= tail else values
  return all(sample[index] <= sample[index - 1] for index in range(1, len(sample)))


def convergence_quality_score(case: CaseSpec) -> float:
  monitor = case.solver_monitor
  continuity = monitor.continuity_residual
  momentum = monitor.momentum_residual
  energy = monitor.energy_residual
  decay = (
    residual_decay_ratio(continuity)
    + residual_decay_ratio(momentum)
    + residual_decay_ratio(energy)
  ) / 3.0
  monotonic = sum(
    [
      1.0 if monotonic_tail(continuity) else 0.0,
      1.0 if monotonic_tail(momentum) else 0.0,
      1.0 if monotonic_tail(energy) else 0.0,
    ]
  ) / 3.0
  iteration_ratio = monitor.iterations / max(monitor.target_iterations, 1)
  return max(0.0, min(1.0, (1.0 - decay) * 0.5 + monotonic * 0.3 + (1.0 - iteration_ratio) * 0.2))


def extended_residual_summary(case: CaseSpec) -> dict[str, object]:
  monitor = case.solver_monitor
  continuity = monitor.continuity_residual
  momentum = monitor.momentum_residual
  energy = monitor.energy_residual
  return {
    "continuity_tail_mean": residual_tail_mean(continuity),
    "momentum_tail_mean": residual_tail_mean(momentum),
    "energy_tail_mean": residual_tail_mean(energy),
    "continuity_decay": residual_decay_ratio(continuity),
    "momentum_decay": residual_decay_ratio(momentum),
    "energy_decay": residual_decay_ratio(energy),
    "quality_score": convergence_quality_score(case),
    "monotonic_continuity": monotonic_tail(continuity),
    "monotonic_momentum": monotonic_tail(momentum),
    "monotonic_energy": monotonic_tail(energy),
  }
