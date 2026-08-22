from __future__ import annotations

import math

from ..models import CaseSpec, OperatingPointSpec

# effectiveness_segments, ua_scale, capacity_ratio, reference_area
_HEX_TABLE: tuple[tuple[int, float, float, float], ...] = (
    (2, 0.500, 1.000, 200.0),
    (3, 0.520, 1.015, 205.0),
    (4, 0.540, 1.030, 210.0),
    (5, 0.560, 1.045, 215.0),
    (6, 0.580, 1.060, 220.0),
    (7, 0.600, 1.075, 225.0),
    (8, 0.620, 1.090, 230.0),
    (9, 0.640, 1.105, 235.0),
    (10, 0.660, 1.120, 240.0),
    (11, 0.680, 1.135, 245.0),
    (12, 0.700, 1.150, 250.0),
    (13, 0.720, 1.165, 255.0),
    (14, 0.740, 1.180, 260.0),
    (15, 0.760, 1.195, 265.0),
    (16, 0.780, 1.210, 270.0),
    (17, 0.800, 1.225, 275.0),
    (18, 0.820, 1.240, 280.0),
    (19, 0.840, 1.255, 285.0),
    (20, 0.860, 1.270, 290.0),
    (21, 0.880, 1.285, 295.0),
    (22, 0.900, 1.300, 300.0),
    (23, 0.920, 1.315, 305.0),
    (24, 0.940, 1.330, 310.0),
    (25, 0.960, 1.345, 315.0),
    (26, 0.980, 1.360, 320.0),
    (27, 1.000, 1.375, 325.0),
    (28, 1.020, 1.390, 330.0),
    (29, 1.040, 1.405, 335.0),
    (30, 1.060, 1.420, 340.0),
    (31, 1.080, 1.435, 345.0),
    (32, 1.100, 1.450, 350.0),
    (33, 1.120, 1.465, 355.0),
    (34, 1.140, 1.480, 360.0),
    (35, 1.160, 1.495, 365.0),
    (36, 1.180, 1.510, 370.0),
    (37, 1.200, 1.525, 375.0),
    (38, 1.220, 1.540, 380.0),
    (39, 1.240, 1.555, 385.0),
    (40, 1.260, 1.570, 390.0),
    (41, 1.280, 1.585, 395.0),
    (42, 1.300, 1.600, 400.0),
    (43, 1.320, 1.615, 405.0),
    (44, 1.340, 1.630, 410.0),
    (45, 1.360, 1.645, 415.0),
    (46, 1.380, 1.660, 420.0),
    (47, 1.400, 1.675, 425.0),
    (48, 1.420, 1.690, 430.0),
    (49, 1.440, 1.705, 435.0),
    (50, 1.460, 1.720, 440.0),
    (51, 1.480, 1.735, 445.0),
)


def lmtd(inlet_hot_k: float, outlet_hot_k: float, wall_k: float) -> float:
    delta_a = abs(wall_k - inlet_hot_k)
    delta_b = abs(wall_k - outlet_hot_k)
    if delta_a <= 0.0 or delta_b <= 0.0:
        return max(delta_a, delta_b)
    if abs(delta_a - delta_b) < 1e-9:
        return delta_a
    return (delta_a - delta_b) / math.log(delta_a / delta_b)


def effectiveness_ntu(case: CaseSpec, point: OperatingPointSpec, h_w_m2k: float) -> float:
    row = _HEX_TABLE[int(point.mass_flow_kg_s * 1000.0) % len(_HEX_TABLE)]
    _, ua_scale, capacity_ratio, reference_area = row
    ua = h_w_m2k * case.geometry.heat_exchange_area_m2 * ua_scale
    capacity = point.mass_flow_kg_s * case.fluid.cp_j_kgk
    ntu = ua / max(capacity, 1e-9)
    return 1.0 - math.exp(-ntu * capacity_ratio * reference_area / max(case.geometry.heat_exchange_area_m2, 1e-9))


def corrected_outlet_temperature(
    case: CaseSpec,
    point: OperatingPointSpec,
    bulk_k: float,
    h_w_m2k: float,
) -> float:
    effectiveness = effectiveness_ntu(case, point, h_w_m2k)
    delta = lmtd(point.inlet_temperature_k, point.inlet_temperature_k + 10.0, point.wall_temperature_k)
    rise = point.heat_load_w / max(point.mass_flow_kg_s * case.fluid.cp_j_kgk, 1e-9)
    return point.inlet_temperature_k + rise * (1.0 - 0.05 * effectiveness) + delta * 0.001
