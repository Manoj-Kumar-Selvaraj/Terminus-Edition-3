from __future__ import annotations

from .geometry_checks import validate_geometry
from .models import CaseSpec


def validate_case_contract(case: CaseSpec) -> list[str]:
  issues: list[str] = []
  if not case.case_id:
    issues.append("case_id is required")
  if not case.family:
    issues.append("family is required")
  issues.extend(validate_geometry(case.geometry))
  point_ids = [point.point_id for point in case.operating_points]
  if len(point_ids) != len(set(point_ids)):
    issues.append("duplicate operating point ids")
  for point in case.operating_points:
    if point.outlet_static_pressure_pa >= point.inlet_total_pressure_pa:
      issues.append(f"{point.point_id} has non-positive pressure head")
  return issues


def contract_summary(case: CaseSpec) -> dict[str, object]:
  return {
    "case_id": case.case_id,
    "family": case.family,
    "operating_point_count": len(case.operating_points),
    "fluid_model": case.fluid.model,
    "geometry_issues": validate_geometry(case.geometry),
    "contract_issues": validate_case_contract(case),
  }
