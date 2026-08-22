from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class FluidSpec:
    model: str
    name: str
    density_kg_m3: float
    dynamic_viscosity_pa_s: float
    cp_j_kgk: float
    thermal_conductivity_w_mk: float
    reference_temperature_k: float
    thermal_expansion_per_k: float
    gamma: float
    gas_constant_j_kgk: float


@dataclass(frozen=True)
class GeometrySpec:
    hydraulic_diameter_m: float
    flow_area_m2: float
    wetted_perimeter_m: float
    length_m: float
    roughness_m: float
    minor_loss_coefficient: float
    heat_exchange_area_m2: float
    characteristic_cell_length_m: float


@dataclass(frozen=True)
class MeshSpec:
    cell_count: int
    max_aspect_ratio: float
    mean_skewness: float
    max_skewness: float
    min_orthogonality: float
    negative_volume_cells: int


@dataclass(frozen=True)
class SolverMonitorSpec:
    iterations: int
    target_iterations: int
    time_step_s: float
    continuity_residual: list[float]
    momentum_residual: list[float]
    energy_residual: list[float]
    mass_imbalance_percent: float
    energy_imbalance_percent: float


@dataclass(frozen=True)
class LimitsSpec:
    max_mach: float
    max_cfl: float
    min_mesh_score: float
    max_pressure_drop_pa: float
    max_bulk_temperature_k: float
    max_mass_imbalance_percent: float
    max_energy_imbalance_percent: float
    max_final_residual: float


@dataclass(frozen=True)
class OperatingPointSpec:
    point_id: str
    mass_flow_kg_s: float
    inlet_temperature_k: float
    wall_temperature_k: float
    inlet_total_pressure_pa: float
    outlet_static_pressure_pa: float
    heat_load_w: float


@dataclass(frozen=True)
class CaseSpec:
    case_id: str
    family: str
    fluid: FluidSpec
    geometry: GeometrySpec
    mesh: MeshSpec
    solver_monitor: SolverMonitorSpec
    limits: LimitsSpec
    operating_points: list[OperatingPointSpec]
    source_path: Path
    source_digest: str


@dataclass(frozen=True)
class Config:
    system_name: str
    schema_version: str
    output_dir: Path
    summary_name: str
    csv_name: str
    checkpoint_name: str
    severity_order: list[str]
    round_digits: int
    csv_fields: list[str]
