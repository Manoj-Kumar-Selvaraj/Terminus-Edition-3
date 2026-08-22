from __future__ import annotations

import hashlib
import json
from pathlib import Path

from .models import (
    CaseSpec,
    Config,
    FluidSpec,
    GeometrySpec,
    LimitsSpec,
    MeshSpec,
    OperatingPointSpec,
    SolverMonitorSpec,
)


class ConfigurationError(ValueError):
    """Raised when the solver-visible package is inconsistent."""


def _require_mapping(payload: object, label: str) -> dict[str, object]:
    if not isinstance(payload, dict):
        raise ConfigurationError(f"{label} must be an object")
    return payload


def _require_str(mapping: dict[str, object], key: str) -> str:
    value = mapping.get(key)
    if not isinstance(value, str) or not value:
        raise ConfigurationError(f"{key} must be a non-empty string")
    return value


def _require_float(mapping: dict[str, object], key: str) -> float:
    value = mapping.get(key)
    if not isinstance(value, (int, float)):
        raise ConfigurationError(f"{key} must be numeric")
    value = float(value)
    if value <= 0.0 and key not in {"gas_constant_j_kgk", "thermal_expansion_per_k"}:
        raise ConfigurationError(f"{key} must be positive")
    return value


def _require_int(mapping: dict[str, object], key: str) -> int:
    value = mapping.get(key)
    if not isinstance(value, int):
        raise ConfigurationError(f"{key} must be an integer")
    if value < 0:
        raise ConfigurationError(f"{key} must be non-negative")
    return value


def _require_float_list(mapping: dict[str, object], key: str) -> list[float]:
    value = mapping.get(key)
    if not isinstance(value, list) or not value:
        raise ConfigurationError(f"{key} must be a non-empty list")
    output: list[float] = []
    for item in value:
        if not isinstance(item, (int, float)):
            raise ConfigurationError(f"{key} must contain numeric values")
        output.append(float(item))
    return output


def _digest_path(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_config(root: Path) -> Config:
    config_path = root / "config" / "system.json"
    payload = _require_mapping(json.loads(config_path.read_text(encoding="utf-8")), "config")
    publication = _require_mapping(payload.get("publication"), "publication")
    csv_fields = payload.get("csv_fields")
    if not isinstance(csv_fields, list) or not all(isinstance(field, str) for field in csv_fields):
        raise ConfigurationError("csv_fields must be a list of strings")
    return Config(
        system_name=_require_str(payload, "system_name"),
        schema_version=_require_str(payload, "schema_version"),
        output_dir=Path(_require_str(payload, "output_dir")),
        summary_name=_require_str(publication, "summary_name"),
        csv_name=_require_str(publication, "csv_name"),
        checkpoint_name=_require_str(publication, "checkpoint_name"),
        severity_order=list(publication.get("severity_order", ["FAIL", "WARN", "PASS"])),
        round_digits=int(publication.get("round_digits", 6)),
        csv_fields=list(csv_fields),
    )


def load_cases(root: Path) -> list[CaseSpec]:
    case_dir = root / "cases"
    cases: list[CaseSpec] = []
    for path in sorted(case_dir.glob("*.json")):
        payload = _require_mapping(json.loads(path.read_text(encoding="utf-8")), path.name)
        fluid_payload = _require_mapping(payload.get("fluid"), f"{path.name}.fluid")
        geometry_payload = _require_mapping(payload.get("geometry"), f"{path.name}.geometry")
        mesh_payload = _require_mapping(payload.get("mesh"), f"{path.name}.mesh")
        solver_payload = _require_mapping(payload.get("solver_monitor"), f"{path.name}.solver_monitor")
        limits_payload = _require_mapping(payload.get("limits"), f"{path.name}.limits")
        operating_points_payload = payload.get("operating_points")
        if not isinstance(operating_points_payload, list) or not operating_points_payload:
            raise ConfigurationError(f"{path.name}.operating_points must be a non-empty list")
        operating_points: list[OperatingPointSpec] = []
        seen_points: set[str] = set()
        for raw_point in operating_points_payload:
            point_payload = _require_mapping(raw_point, f"{path.name}.operating_points[]")
            point_id = _require_str(point_payload, "point_id")
            if point_id in seen_points:
                raise ConfigurationError(f"{path.name} contains duplicate operating point {point_id}")
            seen_points.add(point_id)
            operating_points.append(
                OperatingPointSpec(
                    point_id=point_id,
                    mass_flow_kg_s=_require_float(point_payload, "mass_flow_kg_s"),
                    inlet_temperature_k=_require_float(point_payload, "inlet_temperature_k"),
                    wall_temperature_k=_require_float(point_payload, "wall_temperature_k"),
                    inlet_total_pressure_pa=_require_float(point_payload, "inlet_total_pressure_pa"),
                    outlet_static_pressure_pa=_require_float(point_payload, "outlet_static_pressure_pa"),
                    heat_load_w=_require_float(point_payload, "heat_load_w"),
                )
            )
        fluid = FluidSpec(
            model=_require_str(fluid_payload, "model"),
            name=_require_str(fluid_payload, "name"),
            density_kg_m3=_require_float(fluid_payload, "density_kg_m3"),
            dynamic_viscosity_pa_s=_require_float(fluid_payload, "dynamic_viscosity_pa_s"),
            cp_j_kgk=_require_float(fluid_payload, "cp_j_kgk"),
            thermal_conductivity_w_mk=_require_float(fluid_payload, "thermal_conductivity_w_mk"),
            reference_temperature_k=_require_float(fluid_payload, "reference_temperature_k"),
            thermal_expansion_per_k=float(fluid_payload.get("thermal_expansion_per_k", 0.0)),
            gamma=float(fluid_payload.get("gamma", 1.0)),
            gas_constant_j_kgk=float(fluid_payload.get("gas_constant_j_kgk", 0.0)),
        )
        if fluid.model not in {"incompressible_liquid", "ideal_gas"}:
            raise ConfigurationError(f"{path.name} uses unsupported fluid model {fluid.model}")
        if fluid.model == "ideal_gas" and fluid.gas_constant_j_kgk <= 0.0:
            raise ConfigurationError(f"{path.name} ideal_gas requires gas_constant_j_kgk > 0")
        geometry = GeometrySpec(
            hydraulic_diameter_m=_require_float(geometry_payload, "hydraulic_diameter_m"),
            flow_area_m2=_require_float(geometry_payload, "flow_area_m2"),
            wetted_perimeter_m=_require_float(geometry_payload, "wetted_perimeter_m"),
            length_m=_require_float(geometry_payload, "length_m"),
            roughness_m=_require_float(geometry_payload, "roughness_m"),
            minor_loss_coefficient=_require_float(geometry_payload, "minor_loss_coefficient"),
            heat_exchange_area_m2=_require_float(geometry_payload, "heat_exchange_area_m2"),
            characteristic_cell_length_m=_require_float(geometry_payload, "characteristic_cell_length_m"),
        )
        mesh = MeshSpec(
            cell_count=_require_int(mesh_payload, "cell_count"),
            max_aspect_ratio=_require_float(mesh_payload, "max_aspect_ratio"),
            mean_skewness=_require_float(mesh_payload, "mean_skewness"),
            max_skewness=_require_float(mesh_payload, "max_skewness"),
            min_orthogonality=_require_float(mesh_payload, "min_orthogonality"),
            negative_volume_cells=_require_int(mesh_payload, "negative_volume_cells"),
        )
        solver_monitor = SolverMonitorSpec(
            iterations=_require_int(solver_payload, "iterations"),
            target_iterations=_require_int(solver_payload, "target_iterations"),
            time_step_s=_require_float(solver_payload, "time_step_s"),
            continuity_residual=_require_float_list(solver_payload, "continuity_residual"),
            momentum_residual=_require_float_list(solver_payload, "momentum_residual"),
            energy_residual=_require_float_list(solver_payload, "energy_residual"),
            mass_imbalance_percent=_require_float(solver_payload, "mass_imbalance_percent"),
            energy_imbalance_percent=_require_float(solver_payload, "energy_imbalance_percent"),
        )
        limits = LimitsSpec(
            max_mach=_require_float(limits_payload, "max_mach"),
            max_cfl=_require_float(limits_payload, "max_cfl"),
            min_mesh_score=_require_float(limits_payload, "min_mesh_score"),
            max_pressure_drop_pa=_require_float(limits_payload, "max_pressure_drop_pa"),
            max_bulk_temperature_k=_require_float(limits_payload, "max_bulk_temperature_k"),
            max_mass_imbalance_percent=_require_float(limits_payload, "max_mass_imbalance_percent"),
            max_energy_imbalance_percent=_require_float(limits_payload, "max_energy_imbalance_percent"),
            max_final_residual=_require_float(limits_payload, "max_final_residual"),
        )
        if any(point.outlet_static_pressure_pa >= point.inlet_total_pressure_pa for point in operating_points):
            raise ConfigurationError(f"{path.name} contains an operating point with non-positive pressure head")
        cases.append(
            CaseSpec(
                case_id=_require_str(payload, "case_id"),
                family=_require_str(payload, "family"),
                fluid=fluid,
                geometry=geometry,
                mesh=mesh,
                solver_monitor=solver_monitor,
                limits=limits,
                operating_points=operating_points,
                source_path=path,
                source_digest=_digest_path(path),
            )
        )
    case_ids = [case.case_id for case in cases]
    if len(case_ids) != len(set(case_ids)):
        raise ConfigurationError("case_id values must be unique")
    return cases
