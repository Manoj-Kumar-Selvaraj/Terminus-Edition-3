from __future__ import annotations

from .models import CaseSpec, OperatingPointSpec


def envelope_distance(
  case: CaseSpec,
  point: OperatingPointSpec,
  metrics: dict[str, float],
) -> dict[str, float]:
  limits = case.limits
  return {
    "mach": limits.max_mach - metrics["mach"],
    "cfl": limits.max_cfl - metrics["cfl"],
    "pressure_pa": limits.max_pressure_drop_pa - metrics["pressure_drop_pa"],
    "temperature_k": limits.max_bulk_temperature_k - metrics["outlet_temperature_k"],
    "head_pa": point.inlet_total_pressure_pa - point.outlet_static_pressure_pa - metrics["pressure_drop_pa"],
  }


def envelope_score(distances: dict[str, float]) -> float:
  normalized = [
    distances["mach"],
    distances["cfl"],
    distances["pressure_pa"] / max(abs(distances["pressure_pa"]), 1.0),
    distances["temperature_k"] / max(abs(distances["temperature_k"]), 1.0),
  ]
  return sum(normalized) / len(normalized)


def classify_envelope(distances: dict[str, float]) -> str:
  if any(value < 0.0 for value in distances.values()):
    return "outside"
  if any(value < 0.05 for key, value in distances.items() if key in {"mach", "cfl"}):
    return "near_limit"
  return "inside"
