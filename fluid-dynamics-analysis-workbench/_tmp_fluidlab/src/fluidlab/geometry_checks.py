from __future__ import annotations

import math

from .models import GeometrySpec


def hydraulic_diameter_from_geometry(geometry: GeometrySpec) -> float:
  """Derive hydraulic diameter from wetted perimeter and flow area when needed."""
  if geometry.wetted_perimeter_m <= 0.0 or geometry.flow_area_m2 <= 0.0:
    return geometry.hydraulic_diameter_m
  return 4.0 * geometry.flow_area_m2 / geometry.wetted_perimeter_m


def geometry_consistency_score(geometry: GeometrySpec) -> float:
  derived = hydraulic_diameter_from_geometry(geometry)
  configured = geometry.hydraulic_diameter_m
  ratio = derived / max(configured, 1e-12)
  deviation = abs(ratio - 1.0)
  return max(0.0, 1.0 - deviation)


def validate_geometry(geometry: GeometrySpec) -> list[str]:
  issues: list[str] = []
  if geometry.flow_area_m2 <= 0.0:
    issues.append("flow_area_m2 must be positive")
  if geometry.hydraulic_diameter_m <= 0.0:
    issues.append("hydraulic_diameter_m must be positive")
  if geometry.length_m <= 0.0:
    issues.append("length_m must be positive")
  if geometry.characteristic_cell_length_m <= 0.0:
    issues.append("characteristic_cell_length_m must be positive")
  derived = hydraulic_diameter_from_geometry(geometry)
  if abs(derived - geometry.hydraulic_diameter_m) / geometry.hydraulic_diameter_m > 0.08:
    issues.append("hydraulic diameter disagrees with wetted perimeter and flow area")
  if geometry.heat_exchange_area_m2 < geometry.flow_area_m2:
    issues.append("heat_exchange_area_m2 should exceed flow cross-section")
  return issues


def characteristic_lengths(geometry: GeometrySpec) -> dict[str, float]:
  hydraulic = geometry.hydraulic_diameter_m
  hydraulic_equiv = hydraulic_diameter_from_geometry(geometry)
  return {
    "hydraulic_diameter_m": hydraulic,
    "equivalent_hydraulic_diameter_m": hydraulic_equiv,
    "length_to_diameter": geometry.length_m / max(hydraulic, 1e-12),
    "area_to_perimeter": geometry.flow_area_m2 / max(geometry.wetted_perimeter_m, 1e-12),
    "cell_to_hydraulic_ratio": geometry.characteristic_cell_length_m / max(hydraulic, 1e-12),
  }


def mesh_length_scale(geometry: GeometrySpec, cell_count: int) -> float:
  volume_proxy = geometry.flow_area_m2 * geometry.length_m
  cell_volume = volume_proxy / max(cell_count, 1)
  return math.sqrt(max(cell_volume, 1e-18))
