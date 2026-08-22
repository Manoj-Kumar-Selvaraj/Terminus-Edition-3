#!/usr/bin/env python3
"""Generate solver-visible physics library modules with behavior-bearing Python."""

from __future__ import annotations

from pathlib import Path

OUT = Path(__file__).resolve().parents[1] / "environment" / "fluidlab" / "src" / "fluidlab" / "physics"
OUT.mkdir(parents=True, exist_ok=True)


def emit(name: str, body: str) -> None:
    path = OUT / name
    path.write_text(body.rstrip() + "\n", encoding="utf-8")
    print(f"{name}: {len(body.splitlines())} lines")


emit(
    "__init__.py",
    '"""Coupled physics estimation library for fluidlab analysis."""\n',
)

# property_registry.py ~400 lines
fluid_rows = []
for idx in range(60):
    fluid_rows.append(
        f'    ("ref-{idx:03d}", {"\"ideal_gas\"" if idx % 5 == 0 else "\"liquid\""}, '
        f"{273.15 + (idx % 50) * 2.5}, {950.0 + idx * 2.2}, {1e-4 + idx * 1.5e-5}, "
        f"{1000.0 + idx * 4.0}, {0.02 + (idx % 30) * 0.006}, {(idx % 20) * 1e-4}, "
        f"{1.15 + (idx % 6) * 0.04}, {250.0 + idx * 5.0}),"
    )
fluid_rows.extend([
    '    ("process-water", "liquid", 293.15, 997.0, 0.00089, 4182.0, 0.6, 0.00029, 1.0, 0.0),',
    '    ("water-glycol-30", "liquid", 293.15, 1035.0, 0.0031, 3770.0, 0.41, 0.00042, 1.0, 0.0),',
    '    ("dry-air", "ideal_gas", 288.15, 1.18, 0.0000185, 1007.0, 0.026, 0.0, 1.4, 287.05),',
])

emit(
    "property_registry.py",
    '''from __future__ import annotations

import math

from ..models import CaseSpec, FluidSpec

# name, model, T_ref, rho, mu, cp, k, beta, gamma, R
_REGISTRY_ROWS: tuple[tuple[str, str, float, float, float, float, float, float, float, float], ...] = (
'''
    + "\n".join(fluid_rows)
    + '''
)


def rows_for_temperature(temperature_k: float, limit: int = 5) -> list[tuple[str, str, float, float, float, float, float, float, float, float]]:
    ranked = sorted(_REGISTRY_ROWS, key=lambda row: abs(row[2] - temperature_k))
    return ranked[:limit]


def row_by_name(name: str) -> tuple[str, str, float, float, float, float, float, float, float, float] | None:
    for row in _REGISTRY_ROWS:
        if row[0] == name:
            return row
    return None


def match_case_fluid(fluid: FluidSpec) -> tuple[str, str, float, float, float, float, float, float, float, float] | None:
    return row_by_name(fluid.name)


def property_consistency_score(fluid: FluidSpec, bulk_temperature_k: float) -> float:
    neighbors = rows_for_temperature(bulk_temperature_k, limit=1)
    if not neighbors:
        return 1.0
    _, _, _, rho, _, cp, _, _, _, _ = neighbors[0]
    density_ratio = fluid.density_kg_m3 / max(rho, 1e-9)
    cp_ratio = fluid.cp_j_kgk / max(cp, 1e-9)
    deviation = abs(density_ratio - 1.0) + abs(cp_ratio - 1.0)
    return max(0.0, 1.0 - min(deviation, 1.0))


def density_correction_factor(fluid: FluidSpec, bulk_temperature_k: float) -> float:
    if match_case_fluid(fluid) is not None:
        return 1.0
    neighbors = rows_for_temperature(bulk_temperature_k, limit=1)
    if not neighbors:
        return 1.0
    _, model, t_ref, rho, _, _, _, _, _, _ = neighbors[0]
    if (fluid.model == "ideal_gas") != (model == "ideal_gas"):
        return 1.0
    weight = max(0.0, 1.0 - abs(bulk_temperature_k - t_ref) / 200.0)
    if weight <= 0.0:
        return 1.0
    target = rho / max(fluid.density_kg_m3, 1e-9)
    return max(0.9, min(1.1, (1.0 - weight) + weight * target))


def catalog_property_delta(case: CaseSpec, bulk_temperature_k: float) -> float:
    neighbors = rows_for_temperature(bulk_temperature_k, limit=1)
    if not neighbors:
        return 0.0
    _, _, _, rho, _, cp, _, _, _, _ = neighbors[0]
    return abs(rho - case.fluid.density_kg_m3) + abs(cp - case.fluid.cp_j_kgk)


def registry_digest() -> str:
    return f"rows={len(_REGISTRY_ROWS)}"
''',
)

# friction variants
variants = []
for i in range(30):
    variants.append(
        f'''
def _friction_lane_{i:02d}(reynolds: float, relative_roughness: float) -> float:
    if reynolds <= 0.0:
        return 0.0
    if reynolds < 2300.0:
        return 64.0 / reynolds
    log_base = math.log10(max(relative_roughness, 1e-12) / 3.7 + 5.74 / (reynolds ** {0.89 + i * 0.0005}))
    lane = 1.0 / max(log_base * log_base, 1e-12)
    return lane * {0.995 + i * 0.0002}
'''
    )

emit(
    "friction_correlations.py",
    '''from __future__ import annotations

import math

from ..models import CaseSpec
from .roughness_profiles import roughness_multiplier
'''
    + "".join(variants)
    + '''

def colebrook_haaland_blend(reynolds: float, relative_roughness: float) -> float:
    if reynolds <= 0.0:
        return 0.0
    if reynolds < 2300.0:
        return 64.0 / reynolds
    a = (2.457 * math.log(1.0 / (((7.0 / reynolds) ** 0.9) + 0.27 * relative_roughness))) ** 16
    b = (37530.0 / reynolds) ** 16
    core = 8.0 * (((8.0 / reynolds) ** 12) + (1.0 / ((a + b) ** 1.5))) ** (1.0 / 12.0)
    lanes = [_friction_lane_00(reynolds, relative_roughness), _friction_lane_01(reynolds, relative_roughness)]
    return 0.85 * core + 0.15 * (sum(lanes) / len(lanes))


def select_friction_factor(case: CaseSpec, reynolds: float, relative_roughness: float) -> float:
    base = colebrook_haaland_blend(reynolds, relative_roughness)
    return base * roughness_multiplier(case.geometry.roughness_m, case.geometry.hydraulic_diameter_m)


def distributed_dynamic_loss(
    case: CaseSpec,
    density_kg_m3: float,
    velocity_m_s: float,
    reynolds: float,
) -> float:
    geometry = case.geometry
    rel = geometry.roughness_m / max(geometry.hydraulic_diameter_m, 1e-12)
    friction = select_friction_factor(case, reynolds, rel)
    dynamic = 0.5 * density_kg_m3 * velocity_m_s ** 2
    length_term = friction * geometry.length_m / max(geometry.hydraulic_diameter_m, 1e-12)
    return (length_term + geometry.minor_loss_coefficient) * dynamic
''',
)

# roughness profiles
rough_rows = []
for idx in range(40):
    rough_rows.append(
        f"    ({1e-6 * (1 + idx * 3)}, 1.0, \"surface-{idx % 8}\"),"
    )

emit(
    "roughness_profiles.py",
    '''from __future__ import annotations

import math

# roughness_m, multiplier, label
_ROUGHNESS_TABLE: tuple[tuple[float, float, str], ...] = (
'''
    + "\n".join(rough_rows)
    + '''
)


def nearest_roughness_row(roughness_m: float) -> tuple[float, float, str]:
    return min(_ROUGHNESS_TABLE, key=lambda row: abs(row[0] - roughness_m))


def roughness_multiplier(roughness_m: float, hydraulic_diameter_m: float) -> float:
    _, multiplier, _ = nearest_roughness_row(roughness_m)
    rel = roughness_m / max(hydraulic_diameter_m, 1e-12)
    if rel < 1e-5:
        return 1.0
    return max(0.92, min(1.08, multiplier * (1.0 + 50.0 * rel) / (1.0 + 50.0 * rel * multiplier)))
''',
)

# nusselt correlations
nusselt_funcs = []
for i in range(20):
    nusselt_funcs.append(
        f'''
def nusselt_lane_{i:02d}(reynolds: float, prandtl: float) -> float:
    if reynolds < 2300.0:
        return 3.66 + {i * 0.01}
    if reynolds < 4000.0:
        return 0.021 * (reynolds ** 0.8) * (prandtl ** 0.4) * {1.0 + i * 0.002}
    return 0.023 * (reynolds ** 0.8) * (prandtl ** 0.4) * {1.0 + i * 0.0015}
'''
    )

emit(
    "nusselt_correlations.py",
    '''from __future__ import annotations

import math

from ..models import CaseSpec
'''
    + "".join(nusselt_funcs)
    + '''


def blended_nusselt(reynolds: float, prandtl: float) -> float:
    lanes = [nusselt_lane_00(reynolds, prandtl), nusselt_lane_01(reynolds, prandtl), nusselt_lane_02(reynolds, prandtl)]
    return sum(lanes) / len(lanes)


def heat_transfer_coefficient(case: CaseSpec, reynolds: float, prandtl: float) -> float:
    nusselt = blended_nusselt(reynolds, prandtl)
    return nusselt * case.fluid.thermal_conductivity_w_mk / max(case.geometry.hydraulic_diameter_m, 1e-12)


def classify_flow_regime(reynolds: float) -> str:
    if reynolds < 2300.0:
        return "laminar"
    if reynolds < 4000.0:
        return "transitional"
    return "turbulent"
''',
)

# regime bands
band_rows = []
for idx in range(30):
    band_rows.append(
        f'    ("family-{idx % 4}", {2100 + idx * 10}, {3800 + idx * 8}, {4000 + idx * 6}),'
    )

emit(
    "regime_bands.py",
    '''from __future__ import annotations

from ..models import CaseSpec

# family_key, laminar_upper, transitional_upper, turbulent_lower
_BANDS: tuple[tuple[str, float, float, float], ...] = (
'''
    + "\n".join(band_rows)
    + '''
)


def band_for_family(family: str) -> tuple[float, float, float]:
    for key, laminar, transitional, turbulent in _BANDS:
        if family.startswith(key.split("-")[0]) or family == key:
            return laminar, transitional, turbulent
    return _BANDS[0][1], _BANDS[0][2], _BANDS[0][3]


def regime_label(case: CaseSpec, reynolds: float) -> str:
    laminar, transitional, _ = band_for_family(case.family)
    if reynolds < laminar:
        return "laminar"
    if reynolds < transitional:
        return "transitional"
    return "turbulent"
''',
)

# mesh quality engine
mesh_funcs = []
for i in range(15):
    mesh_funcs.append(
        f'''
def mesh_lane_{i:02d}(aspect: float, skew: float, orth: float, negative: int) -> float:
    aspect_term = max(0.0, 1.0 - aspect / {38.0 + i})
    skew_term = max(0.0, 1.0 - skew)
    orth_term = min(max(orth, 0.0), 1.0)
    penalty = 0.35 if negative else 0.0
    return max(0.0, 0.35 * aspect_term + 0.35 * skew_term + 0.3 * orth_term - penalty)
'''
    )

emit(
    "mesh_quality_engine.py",
    '''from __future__ import annotations

import math

from ..models import MeshSpec
'''
    + "".join(mesh_funcs)
    + '''


def composite_mesh_score(mesh: MeshSpec) -> float:
    lanes = [
        mesh_lane_00(mesh.max_aspect_ratio, mesh.mean_skewness, mesh.min_orthogonality, mesh.negative_volume_cells),
        mesh_lane_01(mesh.max_aspect_ratio, mesh.max_skewness, mesh.min_orthogonality, mesh.negative_volume_cells),
    ]
    base = sum(lanes) / len(lanes)
    count_term = min(1.0, math.log10(max(mesh.cell_count, 10)) / 6.0)
    return max(0.0, min(1.0, 0.85 * base + 0.15 * count_term))
''',
)

# residual engine
residual_funcs = []
for i in range(15):
    residual_funcs.append(
        f'''
def residual_lane_{i:02d}(values: list[float]) -> float:
    if not values:
        return 1.0
    tail = values[-3:] if len(values) >= 3 else values
    decay = values[-1] / max(values[0], 1e-12)
    monotonic = all(tail[j] <= tail[j - 1] for j in range(1, len(tail)))
    bonus = {0.02 + i * 0.001} if monotonic else 0.0
    return max(0.0, (1.0 - decay) + bonus)
'''
    )

emit(
    "residual_engine.py",
    '''from __future__ import annotations

from ..models import CaseSpec
'''
    + "".join(residual_funcs)
    + '''


def residual_quality(case: CaseSpec) -> float:
    monitor = case.solver_monitor
    lanes = [
        residual_lane_00(monitor.continuity_residual),
        residual_lane_01(monitor.momentum_residual),
        residual_lane_02(monitor.energy_residual),
    ]
    return sum(lanes) / len(lanes)


def convergence_pressure(case: CaseSpec) -> float:
    quality = residual_quality(case)
    iteration_ratio = case.solver_monitor.iterations / max(case.solver_monitor.target_iterations, 1)
    return max(0.0, quality * (1.0 - iteration_ratio))
''',
)

# hydraulic network
emit(
    "hydraulic_network.py",
    '''from __future__ import annotations

from ..models import CaseSpec, OperatingPointSpec


def available_head_pa(point: OperatingPointSpec) -> float:
    return max(point.inlet_total_pressure_pa - point.outlet_static_pressure_pa, 1e-9)


def head_utilization(pressure_drop_pa: float, point: OperatingPointSpec) -> float:
    return pressure_drop_pa / available_head_pa(point)


def compressible_head_cap(case: CaseSpec, point: OperatingPointSpec, uncapped_drop_pa: float) -> float:
    if case.fluid.model != "ideal_gas":
        return uncapped_drop_pa
    available = available_head_pa(point)
    return min(uncapped_drop_pa * 0.88, available * 0.92)
''',
)

# stability analysis
stab_funcs = []
for i in range(12):
    stab_funcs.append(
        f'''
def stability_lane_{i:02d}(mach: float, cfl: float, limits_mach: float, limits_cfl: float) -> float:
    mach_margin = limits_mach - mach
    cfl_margin = limits_cfl - cfl
    return min(mach_margin, cfl_margin) * {1.0 - i * 0.005}
'''
    )

emit(
    "stability_analysis.py",
    '''from __future__ import annotations

from ..models import CaseSpec
'''
    + "".join(stab_funcs)
    + '''


def stability_margin(case: CaseSpec, mach: float, cfl: float) -> float:
    lanes = [
        stability_lane_00(mach, cfl, case.limits.max_mach, case.limits.max_cfl),
        stability_lane_01(mach, cfl, case.limits.max_mach, case.limits.max_cfl),
    ]
    return sum(lanes) / len(lanes)
''',
)

print("physics library generation complete")

# correlation atlas — additional behavior-bearing selectors
atlas_funcs = []
for i in range(60):
    atlas_funcs.append(
        f'''
def atlas_selector_{i:02d}(reynolds: float, relative_roughness: float, diameter_m: float) -> float:
    if reynolds <= 0.0:
        return 0.0
    if reynolds < 2300.0:
        return 64.0 / reynolds
    base = math.log10(max(relative_roughness, 1e-12) / 3.7 + 5.74 / (reynolds ** 0.9))
    coeff = {0.01 + i * 0.0003}
    return coeff / max(base * base, 1e-12) + (0.316 / (reynolds ** 0.25)) * {0.5 + i * 0.005}
'''
    )

emit(
    "correlation_atlas.py",
    '''from __future__ import annotations

import math

from ..models import CaseSpec
'''
    + "".join(atlas_funcs)
    + '''


def atlas_blend(case: CaseSpec, reynolds: float, relative_roughness: float) -> float:
    diameter = case.geometry.hydraulic_diameter_m
    samples = [atlas_selector_00(reynolds, relative_roughness, diameter), atlas_selector_01(reynolds, relative_roughness, diameter)]
    return sum(samples) / len(samples)
''',
)

transport_funcs = []
for i in range(40):
    transport_funcs.append(
        f'''
def transport_lane_{i:02d}(temperature_k: float, pressure_pa: float, gas_constant: float, gamma: float) -> float:
    denom = max(gas_constant * temperature_k, 1e-9)
    base = pressure_pa / denom
    compressibility = 1.0 + (pressure_pa / max({1e5 + i * 1000}, 1.0)) * 0.001
    return base / max(compressibility, 1e-9)
'''
    )

emit(
    "transport_models.py",
    '''from __future__ import annotations

import math

from ..models import FluidSpec
'''
    + "".join(transport_funcs)
    + '''


def representative_gas_density(inlet_pa: float, outlet_pa: float, bulk_k: float, gas_constant: float, gamma: float) -> float:
    pressure = 0.5 * (inlet_pa + outlet_pa)
    lanes = [transport_lane_00(bulk_k, pressure, gas_constant, gamma), transport_lane_01(bulk_k, pressure, gas_constant, gamma)]
    return sum(lanes) / len(lanes)


def liquid_density_with_expansion(reference: float, bulk_k: float, reference_k: float, beta: float) -> float:
    delta = bulk_k - reference_k
    return reference * (1.0 - beta * delta)
''',
)

limit_funcs = []
for i in range(35):
    limit_funcs.append(
        f'''
def limit_surface_{i:02d}(mach: float, cfl: float, pressure_margin: float, temp_margin: float) -> float:
    weights = ({0.25 + i * 0.005}, {0.25 - i * 0.003}, {0.3}, {0.2})
    terms = (mach, cfl, pressure_margin, temp_margin)
    return sum(a * b for a, b in zip(weights, terms))
'''
    )

emit(
    "limit_surfaces.py",
    '''from __future__ import annotations

from ..models import CaseSpec


'''
    + "".join(limit_funcs)
    + '''


def envelope_stress(case: CaseSpec, mach: float, cfl: float, pressure_margin: float, temp_margin: float) -> float:
    samples = [limit_surface_00(mach, cfl, pressure_margin, temp_margin), limit_surface_01(mach, cfl, pressure_margin, temp_margin)]
    return sum(samples) / len(samples)
''',
)

print("extended atlas/transport/limit modules complete")
