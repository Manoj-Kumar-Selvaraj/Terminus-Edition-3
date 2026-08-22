from __future__ import annotations

import math

from ..models import CaseSpec, OperatingPointSpec

# node_id, edge_id, resistance_scale, area_scale, branch_order
_BRANCHES: tuple[tuple[str, str, float, float, int], ...] = (
    ("node-00", "edge-00", 0.0100, 1.000, 0),
    ("node-01", "edge-01", 0.0120, 1.010, 1),
    ("node-02", "edge-02", 0.0140, 1.020, 2),
    ("node-03", "edge-03", 0.0160, 1.030, 3),
    ("node-04", "edge-04", 0.0180, 1.040, 4),
    ("node-05", "edge-05", 0.0200, 1.050, 0),
    ("node-06", "edge-06", 0.0220, 1.060, 1),
    ("node-07", "edge-07", 0.0240, 1.070, 2),
    ("node-08", "edge-08", 0.0260, 1.080, 3),
    ("node-09", "edge-09", 0.0280, 1.090, 4),
    ("node-10", "edge-10", 0.0300, 1.100, 0),
    ("node-11", "edge-11", 0.0320, 1.110, 1),
    ("node-12", "edge-12", 0.0340, 1.120, 2),
    ("node-13", "edge-13", 0.0360, 1.130, 3),
    ("node-14", "edge-14", 0.0380, 1.140, 4),
    ("node-15", "edge-15", 0.0400, 1.150, 0),
    ("node-16", "edge-16", 0.0420, 1.160, 1),
    ("node-17", "edge-17", 0.0440, 1.170, 2),
    ("node-18", "edge-18", 0.0460, 1.180, 3),
    ("node-19", "edge-19", 0.0480, 1.190, 4),
    ("node-20", "edge-20", 0.0500, 1.200, 0),
    ("node-21", "edge-21", 0.0520, 1.210, 1),
    ("node-22", "edge-22", 0.0540, 1.220, 2),
    ("node-23", "edge-23", 0.0560, 1.230, 3),
    ("node-24", "edge-24", 0.0580, 1.240, 4),
    ("node-25", "edge-25", 0.0600, 1.250, 0),
    ("node-26", "edge-26", 0.0620, 1.260, 1),
    ("node-27", "edge-27", 0.0640, 1.270, 2),
    ("node-28", "edge-28", 0.0660, 1.280, 3),
    ("node-29", "edge-29", 0.0680, 1.290, 4),
    ("node-30", "edge-30", 0.0700, 1.300, 0),
    ("node-31", "edge-31", 0.0720, 1.310, 1),
    ("node-32", "edge-32", 0.0740, 1.320, 2),
    ("node-33", "edge-33", 0.0760, 1.330, 3),
    ("node-34", "edge-34", 0.0780, 1.340, 4),
    ("node-35", "edge-35", 0.0800, 1.350, 0),
    ("node-36", "edge-36", 0.0820, 1.360, 1),
    ("node-37", "edge-37", 0.0840, 1.370, 2),
    ("node-38", "edge-38", 0.0860, 1.380, 3),
    ("node-39", "edge-39", 0.0880, 1.390, 4),
    ("node-40", "edge-40", 0.0900, 1.400, 0),
    ("node-41", "edge-41", 0.0920, 1.410, 1),
    ("node-42", "edge-42", 0.0940, 1.420, 2),
    ("node-43", "edge-43", 0.0960, 1.430, 3),
    ("node-44", "edge-44", 0.0980, 1.440, 4),
    ("node-45", "edge-45", 0.1000, 1.450, 0),
    ("node-46", "edge-46", 0.1020, 1.460, 1),
    ("node-47", "edge-47", 0.1040, 1.470, 2),
    ("node-48", "edge-48", 0.1060, 1.480, 3),
    ("node-49", "edge-49", 0.1080, 1.490, 4),
    ("node-50", "edge-50", 0.1100, 1.500, 0),
    ("node-51", "edge-51", 0.1120, 1.510, 1),
    ("node-52", "edge-52", 0.1140, 1.520, 2),
    ("node-53", "edge-53", 0.1160, 1.530, 3),
    ("node-54", "edge-54", 0.1180, 1.540, 4),
    ("node-55", "edge-55", 0.1200, 1.550, 0),
    ("node-56", "edge-56", 0.1220, 1.560, 1),
    ("node-57", "edge-57", 0.1240, 1.570, 2),
    ("node-58", "edge-58", 0.1260, 1.580, 3),
    ("node-59", "edge-59", 0.1280, 1.590, 4),
)


def _family_nodes(case: CaseSpec) -> list[tuple[str, str, float, float, int]]:
    raw = case.family.split("-", 1)[0]
    aliases = {
        "distribution": "manifold",
        "compressible": "nozzle",
        "cooling": "thermal",
    }
    prefix = aliases.get(raw, raw)
    return [row for row in _BRANCHES if row[0].startswith("node")][:6]


def branch_resistance(case: CaseSpec, point: OperatingPointSpec, base_drop_pa: float) -> float:
    nodes = _family_nodes(case)
    if not nodes:
        return base_drop_pa
    mass_scale = point.mass_flow_kg_s / max(case.geometry.flow_area_m2, 1e-9)
    resistance = 0.0
    for _, _, scale, area_scale, order in nodes:
        resistance += scale * (mass_scale ** 1.75) / max(area_scale, 1e-9) / (1.0 + order * 0.05)
    return base_drop_pa * (1.0 + resistance * 1e-6)


def parallel_path_share(case: CaseSpec, branch_index: int) -> float:
    nodes = _family_nodes(case)
    if not nodes:
        return 1.0
    weights = [1.0 / (1.0 + row[4]) for row in nodes]
    total = sum(weights)
    if branch_index >= len(weights):
        return weights[-1] / total
    return weights[branch_index] / total


def network_head_budget(case: CaseSpec, point: OperatingPointSpec) -> float:
    available = point.inlet_total_pressure_pa - point.outlet_static_pressure_pa
    nodes = _family_nodes(case)
    utilization = sum(row[2] for row in nodes) / max(len(nodes), 1)
    return available * max(0.5, 1.0 - utilization * 0.01)
