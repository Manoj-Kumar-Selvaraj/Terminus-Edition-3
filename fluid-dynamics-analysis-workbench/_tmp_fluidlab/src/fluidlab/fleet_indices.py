from __future__ import annotations


def fleet_risk_indices(case_results: list[dict[str, object]]) -> dict[str, float]:
  points = [point for case in case_results for point in case["operating_points"]]
  if not points:
    return {
      "hydraulic_stress_index": 0.0,
      "thermal_stress_index": 0.0,
      "stability_stress_index": 0.0,
      "mesh_stress_index": 0.0,
    }
  pressure_margins = [float(point["margins"]["pressure_margin_pa"]) for point in points]
  temperature_margins = [float(point["margins"]["temperature_margin_k"]) for point in points]
  mach_margins = [float(point["margins"]["mach_margin"]) for point in points]
  cfl_margins = [float(point["margins"]["cfl_margin"]) for point in points]
  mesh_scores = [float(case["mesh"]["score"]) for case in case_results]
  return {
    "hydraulic_stress_index": 1.0 - min(pressure_margins) / max(abs(min(pressure_margins)), 1.0),
    "thermal_stress_index": 1.0 - min(temperature_margins) / max(abs(min(temperature_margins)), 1.0),
    "stability_stress_index": min(mach_margins + cfl_margins) / max(max(mach_margins + cfl_margins), 1.0),
    "mesh_stress_index": 1.0 - min(mesh_scores),
  }


def enrich_fleet_rollup(
  case_results: list[dict[str, object]],
  severity_order: list[str],
  base_rollup: dict[str, object],
) -> dict[str, object]:
  indices = fleet_risk_indices(case_results)
  enriched = dict(base_rollup)
  enriched.update(indices)
  return enriched
