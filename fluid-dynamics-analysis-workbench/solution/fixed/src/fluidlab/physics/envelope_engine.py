from __future__ import annotations

from ..models import CaseSpec, LimitsSpec, OperatingPointSpec
from ..envelope_scoring import classify_envelope, envelope_distance, envelope_score
from .limit_surfaces import envelope_stress
from .stability_analysis import stability_margin


def effective_margins(
    case: CaseSpec,
    point: OperatingPointSpec,
    limits: LimitsSpec,
    metrics: dict[str, float],
    mesh_score: float,
    base_margins: dict[str, float],
    convergence: dict[str, object],
) -> dict[str, float]:
    distances = envelope_distance(
        case,
        point,
        {
            "mach": metrics["mach"],
            "cfl": metrics["cfl"],
            "pressure_drop_pa": metrics["pressure_drop_pa"],
            "outlet_temperature_k": metrics["outlet_temperature_k"],
        },
    )
    stress = envelope_stress(
        case,
        metrics["mach"],
        metrics["cfl"],
        base_margins["pressure_margin_pa"],
        base_margins["temperature_margin_k"],
    )
    stability = stability_margin(case, metrics["mach"], metrics["cfl"])
    score = envelope_score(distances)
    classification = classify_envelope(distances)
    pressure_coupling = min(base_margins["pressure_margin_pa"], distances["head_pa"])
    stability_coupling = min(base_margins["mach_margin"], base_margins["cfl_margin"], stability)
    adjusted = dict(base_margins)
    adjusted["pressure_margin_pa"] = pressure_coupling - stress * limits.max_pressure_drop_pa * 0.001
    adjusted["mach_margin"] = min(adjusted["mach_margin"], stability_coupling)
    adjusted["cfl_margin"] = min(adjusted["cfl_margin"], stability_coupling)
    adjusted["envelope_score"] = score
    adjusted["envelope_class"] = 1.0 if classification == "inside" else 0.5 if classification == "near_limit" else 0.0
    adjusted["convergence_pressure"] = float(convergence.get("convergence_pressure", 0.0))
    return adjusted
