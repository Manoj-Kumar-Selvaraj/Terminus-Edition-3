from __future__ import annotations

from .convergence import convergence_summary
from .fluid import compute_state
from .mesh import mesh_summary
from .models import CaseSpec, OperatingPointSpec
from .regime import regime_metrics


def _finding(code: str, severity: str, metric: str, actual: float, limit: float) -> dict[str, object]:
    return {
        "code": code,
        "severity": severity,
        "metric": metric,
        "actual": actual,
        "limit": limit,
    }


def analyze_case(case: CaseSpec, severity_order: list[str]) -> dict[str, object]:
    mesh = mesh_summary(case.mesh)
    convergence = convergence_summary(case)
    point_results: list[dict[str, object]] = []
    for point in sorted(case.operating_points, key=lambda item: item.point_id):
        point_results.append(analyze_point(case, point, mesh["score"], convergence))
    point_results.sort(key=lambda item: item["point_id"])
    case_status = point_results[0]["status"]
    aggregates = {
        "operating_point_count": len(point_results),
        "max_pressure_drop_pa": max(item["metrics"]["pressure_drop_pa"] for item in point_results),
        "max_bulk_temperature_k": max(item["metrics"]["outlet_temperature_k"] for item in point_results),
        "max_mach": max(item["metrics"]["mach"] for item in point_results),
        "max_cfl": max(item["metrics"]["cfl"] for item in point_results),
        "mesh_score": mesh["score"],
        "converged": convergence["converged"],
    }
    return {
        "case_id": case.case_id,
        "family": case.family,
        "source_digest": case.source_digest,
        "status": case_status,
        "mesh": mesh,
        "aggregates": aggregates,
        "operating_points": point_results,
    }


def analyze_point(
    case: CaseSpec,
    point: OperatingPointSpec,
    mesh_score: float,
    convergence: dict[str, object],
) -> dict[str, object]:
    state = compute_state(case, point)
    regime = regime_metrics(case, state)
    limits = case.limits
    metrics = {
        "density_kg_m3": state["density_kg_m3"],
        "velocity_m_s": state["velocity_m_s"],
        "reynolds": regime["reynolds"],
        "mach": regime["mach"],
        "cfl": regime["cfl"],
        "pressure_drop_pa": regime["pressure_drop_pa"],
        "outlet_temperature_k": state["outlet_temperature_k"],
        "heat_transfer_coefficient_w_m2k": regime["heat_transfer_coefficient_w_m2k"],
    }
    margins = {
        "mach_margin": limits.max_mach - metrics["mach"],
        "cfl_margin": limits.max_cfl - metrics["cfl"],
        "pressure_margin_pa": limits.max_pressure_drop_pa - metrics["pressure_drop_pa"],
        "temperature_margin_k": limits.max_bulk_temperature_k - metrics["outlet_temperature_k"],
        "mesh_margin": mesh_score - limits.min_mesh_score,
        "mass_imbalance_margin": limits.max_mass_imbalance_percent - convergence["mass_imbalance_percent"],
        "energy_imbalance_margin": limits.max_energy_imbalance_percent - convergence["energy_imbalance_percent"],
        "residual_margin": limits.max_final_residual - convergence["final_residual"],
    }
    findings: list[dict[str, object]] = []
    if margins["mach_margin"] < 0.0:
        findings.append(_finding("MACH_LIMIT", "FAIL", "mach", metrics["mach"], limits.max_mach))
    if margins["cfl_margin"] < 0.0:
        findings.append(_finding("CFL_LIMIT", "FAIL", "cfl", metrics["cfl"], limits.max_cfl))
    if margins["pressure_margin_pa"] < 0.0:
        findings.append(
            _finding("PRESSURE_DROP_LIMIT", "FAIL", "pressure_drop_pa", metrics["pressure_drop_pa"], limits.max_pressure_drop_pa)
        )
    if margins["temperature_margin_k"] < 0.0:
        findings.append(
            _finding(
                "BULK_TEMPERATURE_LIMIT",
                "FAIL",
                "outlet_temperature_k",
                metrics["outlet_temperature_k"],
                limits.max_bulk_temperature_k,
            )
        )
    if margins["mesh_margin"] < 0.0:
        findings.append(_finding("MESH_SCORE_LIMIT", "WARN", "mesh_score", mesh_score, limits.min_mesh_score))
    if not convergence["converged"]:
        findings.append(
            _finding("CONVERGENCE_LIMIT", "WARN", "final_residual", convergence["final_residual"], limits.max_final_residual)
        )
    findings.sort(key=lambda item: (0 if item["severity"] == "FAIL" else 1, str(item["code"])))
    status = "PASS"
    if any(item["severity"] == "FAIL" for item in findings):
        status = "FAIL"
    elif findings:
        status = "WARN"
    return {
        "case_id": case.case_id,
        "point_id": point.point_id,
        "status": status,
        "flow_regime": regime["flow_regime"],
        "metrics": metrics,
        "margins": margins,
        "convergence": convergence,
        "findings": findings,
    }
