from __future__ import annotations

from .models import LimitsSpec


def severity_rank(severity_order: list[str]) -> dict[str, int]:
  return {status: index for index, status in enumerate(severity_order)}


def worst_status(statuses: list[str], severity_order: list[str]) -> str:
  order = severity_rank(severity_order)
  return min(statuses, key=lambda item: order[item])


def finding_precedence(code: str, severity: str) -> tuple[int, str]:
  rank = 0 if severity == "FAIL" else 1
  return (rank, code)


def sort_findings(findings: list[dict[str, object]]) -> list[dict[str, object]]:
  return sorted(findings, key=lambda item: finding_precedence(str(item["code"]), str(item["severity"])))


def status_from_findings(findings: list[dict[str, object]]) -> str:
  if any(item["severity"] == "FAIL" for item in findings):
    return "FAIL"
  if findings:
    return "WARN"
  return "PASS"


def margin_snapshot(limits: LimitsSpec, metrics: dict[str, float], mesh_score: float, convergence: dict[str, object]) -> dict[str, float]:
  return {
    "mach_margin": limits.max_mach - metrics["mach"],
    "cfl_margin": limits.max_cfl - metrics["cfl"],
    "pressure_margin_pa": limits.max_pressure_drop_pa - metrics["pressure_drop_pa"],
    "temperature_margin_k": limits.max_bulk_temperature_k - metrics["outlet_temperature_k"],
    "mesh_margin": mesh_score - limits.min_mesh_score,
    "mass_imbalance_margin": limits.max_mass_imbalance_percent - float(convergence["mass_imbalance_percent"]),
    "energy_imbalance_margin": limits.max_energy_imbalance_percent - float(convergence["energy_imbalance_percent"]),
    "residual_margin": limits.max_final_residual - float(convergence["final_residual"]),
  }
