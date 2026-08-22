from __future__ import annotations

from pathlib import Path

from .loaders import load_cases, load_config
from .report import write_reports
from .solver import analyze_case


def _status_order(severity_order: list[str]) -> dict[str, int]:
    return {status: index for index, status in enumerate(severity_order)}


def _fleet_rollup(case_results: list[dict[str, object]], severity_order: list[str]) -> dict[str, object]:
    order = _status_order(severity_order)
    points = [point for case in case_results for point in case["operating_points"]]
    status_counts = {status: 0 for status in severity_order}
    for point in points:
        status_counts[point["status"]] += 1
    return {
        "case_count": len(case_results),
        "operating_point_count": len(points),
        "status_counts": status_counts,
        "worst_mach_margin": min(point["margins"]["mach_margin"] for point in points),
        "worst_cfl_margin": min(point["margins"]["cfl_margin"] for point in points),
        "worst_pressure_margin_pa": min(point["margins"]["pressure_margin_pa"] for point in points),
        "worst_temperature_margin_k": min(point["margins"]["temperature_margin_k"] for point in points),
        "worst_mesh_score": min(case["mesh"]["score"] for case in case_results),
    }


def run(root: Path) -> dict[str, object]:
    config = load_config(root)
    cases = load_cases(root)
    case_results = sorted(
        [analyze_case(case, config.severity_order) for case in cases],
        key=lambda item: item["case_id"],
    )
    fleet_rollup = _fleet_rollup(case_results, config.severity_order)
    artifacts = write_reports(config, case_results, fleet_rollup, root)
    return {
        "artifacts": artifacts,
        "fleet_rollup": fleet_rollup,
        "case_count": len(case_results),
    }
