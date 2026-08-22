#!/usr/bin/env python3
"""One-shot generator for solver-visible physics library modules (authoring aid)."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "environment" / "fluidlab" / "src" / "fluidlab" / "physics"
ROOT.mkdir(parents=True, exist_ok=True)


def write(name: str, content: str) -> None:
    path = ROOT / name
    path.write_text(content, encoding="utf-8")
    print(f"wrote {path.name}: {len(content.splitlines())} lines")


FLUID_ENTRIES = []
names = [
    "process-water", "water-glycol-30", "dry-air", "steam", "nitrogen", "helium",
    "ethylene-glycol", "sae-30-oil", "ammonia", "co2", "brine", "hydrogen",
]
for idx in range(80):
    base = names[idx % len(names)]
    FLUID_ENTRIES.append(
        f'    {{"name": "{base}-ref-{idx:03d}", "model": '
        f'{"\"ideal_gas\"" if idx % 5 == 0 else "\"incompressible_liquid\""}, '
        f'"reference_temperature_k": {273.15 + (idx % 60) * 2.5}, '
        f'"density_kg_m3": {900.0 + idx * 1.1}, '
        f'"dynamic_viscosity_pa_s": {1e-4 + idx * 2e-5}, '
        f'"cp_j_kgk": {900.0 + idx * 3.5}, '
        f'"thermal_conductivity_w_mk": {0.02 + (idx % 40) * 0.007}, '
        f'"thermal_expansion_per_k": {(idx % 25) * 1e-4}, '
        f'"gamma": {1.1 + (idx % 8) * 0.05}, '
        f'"gas_constant_j_kgk": {200.0 + (idx % 20) * 10.0}}},'
    )

write(
    "property_registry.py",
    '''from __future__ import annotations

import math
from dataclasses import dataclass

from ..models import CaseSpec, FluidSpec


@dataclass(frozen=True)
class FluidReference:
    name: str
    model: str
    reference_temperature_k: float
    density_kg_m3: float
    dynamic_viscosity_pa_s: float
    cp_j_kgk: float
    thermal_conductivity_w_mk: float
    thermal_expansion_per_k: float
    gamma: float
    gas_constant_j_kgk: float


FLUID_REFERENCES: tuple[FluidReference, ...] = (
'''
    + "\n".join(
        line.replace('{"name":', "FluidReference(")
        .replace('"model":', "")
        .replace('"reference_temperature_k":', "")
        .replace('"density_kg_m3":', "")
        .replace('"dynamic_viscosity_pa_s":', "")
        .replace('"cp_j_kgk":', "")
        .replace('"thermal_conductivity_w_mk":', "")
        .replace('"thermal_expansion_per_k":', "")
        .replace('"gamma":', "")
        .replace('"gas_constant_j_kgk":', "")
        .replace('},', "),")
        for line in FLUID_ENTRIES[:40]
    )
    + '''
)


def _as_reference(raw: dict[str, object]) -> FluidReference:
    return FluidReference(
        name=str(raw["name"]),
        model=str(raw["model"]),
        reference_temperature_k=float(raw["reference_temperature_k"]),
        density_kg_m3=float(raw["density_kg_m3"]),
        dynamic_viscosity_pa_s=float(raw["dynamic_viscosity_pa_s"]),
        cp_j_kgk=float(raw["cp_j_kgk"]),
        thermal_conductivity_w_mk=float(raw["thermal_conductivity_w_mk"]),
        thermal_expansion_per_k=float(raw["thermal_expansion_per_k"]),
        gamma=float(raw["gamma"]),
        gas_constant_j_kgk=float(raw["gas_constant_j_kgk"]),
    )


def all_references() -> tuple[FluidReference, ...]:
    return FLUID_REFERENCES


def nearest_by_temperature(temperature_k: float, limit: int = 5) -> list[FluidReference]:
    ranked = sorted(all_references(), key=lambda item: abs(item.reference_temperature_k - temperature_k))
    return ranked[:limit]


def match_by_name(fluid_name: str) -> FluidReference | None:
    for entry in all_references():
        if entry.name == fluid_name:
            return entry
    return None


def property_consistency_score(fluid: FluidSpec, bulk_temperature_k: float) -> float:
    """Return 0..1 consistency against nearest registry neighbor."""
    neighbors = nearest_by_temperature(bulk_temperature_k, limit=3)
    if not neighbors:
        return 1.0
    best = neighbors[0]
    density_ratio = fluid.density_kg_m3 / max(best.density_kg_m3, 1e-9)
    cp_ratio = fluid.cp_j_kgk / max(best.cp_j_kgk, 1e-9)
    deviation = abs(density_ratio - 1.0) + abs(cp_ratio - 1.0)
    return max(0.0, 1.0 - deviation)


def density_correction_factor(fluid: FluidSpec, bulk_temperature_k: float) -> float:
    """Blend case fluid toward registry neighbor; identity when case name matches a row."""
    matched = match_by_name(fluid.name)
    if matched is not None:
        return 1.0
    neighbors = nearest_by_temperature(bulk_temperature_k, limit=1)
    if not neighbors:
        return 1.0
    neighbor = neighbors[0]
    if fluid.model != neighbor.model:
        return 1.0
    weight = max(0.0, 1.0 - abs(bulk_temperature_k - neighbor.reference_temperature_k) / 250.0)
    if weight <= 0.0:
        return 1.0
    target_density = neighbor.density_kg_m3
    if target_density <= 0.0:
        return 1.0
    blend = (1.0 - weight) + weight * (target_density / max(fluid.density_kg_m3, 1e-9))
    return max(0.85, min(1.15, blend))


def catalog_property_delta(case: CaseSpec, bulk_temperature_k: float) -> float:
    neighbors = nearest_by_temperature(bulk_temperature_k, limit=1)
    if not neighbors:
        return 0.0
    entry = neighbors[0]
    return abs(entry.density_kg_m3 - case.fluid.density_kg_m3) + abs(entry.cp_j_kgk - case.fluid.cp_j_kgk)


def registry_digest() -> str:
    return f"fluids={len(all_references())}"
''',
)

# Generate friction_correlations with many functions
friction_funcs = []
for i in range(24):
    friction_funcs.append(
        f'''
def friction_variant_{i:02d}(reynolds: float, relative_roughness: float) -> float:
    if reynolds <= 0.0:
        return 0.0
    if reynolds < 2300.0:
        return 64.0 / reynolds
    log_term = math.log10(max(relative_roughness, 1e-12) / 3.7 + 5.74 / (reynolds ** {0.88 + i * 0.001}))
    return 1.0 / max(log_term ** 2, 1e-12) * {0.98 + i * 0.001}
'''
    )

write(
    "friction_correlations.py",
    '''from __future__ import annotations

import math

from ..models import CaseSpec
from .roughness_profiles import roughness_multiplier
'''
    + "".join(friction_funcs)
    + '''

def colebrook_haaland_blend(reynolds: float, relative_roughness: float) -> float:
    if reynolds <= 0.0:
        return 0.0
    if reynolds < 2300.0:
        return 64.0 / reynolds
    a = (2.457 * math.log(1.0 / (((7.0 / reynolds) ** 0.9) + 0.27 * relative_roughness))) ** 16
    b = (37530.0 / reynolds) ** 16
    haaland = friction_variant_00(reynolds, relative_roughness)
    churchill = 8.0 * (((8.0 / reynolds) ** 12) + (1.0 / ((a + b) ** 1.5))) ** (1.0 / 12.0)
    return 0.62 * churchill + 0.38 * haaland


def select_friction_factor(case: CaseSpec, reynolds: float, relative_roughness: float) -> float:
    base = colebrook_haaland_blend(reynolds, relative_roughness)
    multiplier = roughness_multiplier(case.geometry.roughness_m, case.geometry.hydraulic_diameter_m)
    if case.fluid.model == "ideal_gas":
        return base * multiplier
    return base * (0.5 + 0.5 * multiplier)


def distributed_dynamic_loss(
    case: CaseSpec,
    density_kg_m3: float,
    velocity_m_s: float,
    reynolds: float,
) -> float:
    geometry = case.geometry
    relative_roughness = geometry.roughness_m / max(geometry.hydraulic_diameter_m, 1e-12)
    friction = select_friction_factor(case, reynolds, relative_roughness)
    dynamic_pressure = 0.5 * density_kg_m3 * velocity_m_s ** 2
    length_term = friction * geometry.length_m / max(geometry.hydraulic_diameter_m, 1e-12)
    return (length_term + geometry.minor_loss_coefficient) * dynamic_pressure
''',
)

print("done")
