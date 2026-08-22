from __future__ import annotations

import hashlib

from .models import CaseSpec


def point_lineage_digest(case_id: str, point_id: str, mass_flow: float, heat_load: float) -> str:
  payload = f"{case_id}:{point_id}:{mass_flow:.8f}:{heat_load:.4f}"
  return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def case_lineage_digest(case: CaseSpec) -> str:
  digest = hashlib.sha256()
  digest.update(case.case_id.encode("utf-8"))
  digest.update(case.source_digest.encode("utf-8"))
  for point in sorted(case.operating_points, key=lambda item: item.point_id):
    digest.update(point_lineage_digest(case.case_id, point.point_id, point.mass_flow_kg_s, point.heat_load_w).encode())
  return digest.hexdigest()[:20]


def operating_point_keys(case_results: list[dict[str, object]]) -> list[tuple[str, str]]:
  keys: list[tuple[str, str]] = []
  for case in case_results:
    for point in case["operating_points"]:
      keys.append((str(case["case_id"]), str(point["point_id"])))
  return sorted(keys)
