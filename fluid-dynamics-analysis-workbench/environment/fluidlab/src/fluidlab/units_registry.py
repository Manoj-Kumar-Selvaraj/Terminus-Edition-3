from __future__ import annotations

SI_PRESSURE = "Pa"
SI_TEMPERATURE = "K"
SI_MASS_FLOW = "kg/s"
SI_LENGTH = "m"


def assert_si_pressure(value_pa: float, label: str) -> None:
  if value_pa < 0.0:
    raise ValueError(f"{label} must be non-negative Pascals")


def assert_si_temperature(value_k: float, label: str) -> None:
  if value_k <= 0.0:
    raise ValueError(f"{label} must be positive Kelvin")


def assert_si_mass_flow(value_kg_s: float, label: str) -> None:
  if value_kg_s <= 0.0:
    raise ValueError(f"{label} must be positive kg/s")


def normalize_pressure_to_pa(value: float, unit: str) -> float:
  if unit == "Pa":
    return value
  if unit == "kPa":
    return value * 1000.0
  if unit == "bar":
    return value * 100000.0
  raise ValueError(f"unsupported pressure unit {unit}")


def normalize_temperature_to_k(value: float, unit: str) -> float:
  if unit == "K":
    return value
  if unit == "C":
    return value + 273.15
  raise ValueError(f"unsupported temperature unit {unit}")
