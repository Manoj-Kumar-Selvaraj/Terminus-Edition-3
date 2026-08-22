from __future__ import annotations

import math

from ..models import CaseSpec
from .correlation_policy import friction_policy_factor
from .friction_correlations import colebrook_haaland_blend

# segment_count, weight, length_bias
_DISCRETIZATION: tuple[tuple[int, float, float], ...] = (
    (4, 0.250000, 0.930),
    (5, 0.200000, 0.950),
    (6, 0.166667, 0.970),
    (7, 0.142857, 0.850),
    (8, 0.125000, 0.870),
    (9, 0.111111, 0.890),
    (10, 0.100000, 0.910),
    (11, 0.090909, 0.930),
    (12, 0.083333, 0.950),
    (13, 0.076923, 0.970),
    (14, 0.071429, 0.850),
    (15, 0.066667, 0.870),
    (16, 0.062500, 0.890),
    (17, 0.058824, 0.910),
    (18, 0.055556, 0.930),
    (19, 0.052632, 0.950),
    (20, 0.050000, 0.970),
    (21, 0.047619, 0.850),
    (22, 0.045455, 0.870),
    (23, 0.043478, 0.890),
    (24, 0.041667, 0.910),
    (25, 0.040000, 0.930),
    (26, 0.038462, 0.950),
    (27, 0.037037, 0.970),
    (28, 0.035714, 0.850),
    (29, 0.034483, 0.870),
    (30, 0.033333, 0.890),
    (31, 0.032258, 0.910),
    (32, 0.031250, 0.930),
    (33, 0.030303, 0.950),
    (34, 0.029412, 0.970),
    (35, 0.028571, 0.850),
    (36, 0.027778, 0.870),
    (37, 0.027027, 0.890),
    (38, 0.026316, 0.910),
    (39, 0.025641, 0.930),
    (40, 0.025000, 0.950),
    (41, 0.024390, 0.970),
    (42, 0.023810, 0.850),
    (43, 0.023256, 0.870),
)

# family, ordinal, minor_k, area_ratio, swirl_factor
_FITTINGS: tuple[tuple[str, int, float, float, float], ...] = (
    ("manifold", 0, 0.0200, 1.000, 0.50),
    ("manifold", 1, 0.0230, 1.015, 0.54),
    ("manifold", 2, 0.0260, 1.030, 0.58),
    ("manifold", 3, 0.0290, 1.045, 0.62),
    ("manifold", 4, 0.0320, 1.060, 0.66),
    ("manifold", 5, 0.0350, 1.075, 0.70),
    ("manifold", 6, 0.0380, 1.090, 0.74),
    ("manifold", 7, 0.0410, 1.105, 0.78),
    ("manifold", 8, 0.0440, 1.120, 0.82),
    ("manifold", 9, 0.0470, 1.135, 0.86),
    ("manifold", 10, 0.0500, 1.150, 0.90),
    ("manifold", 11, 0.0530, 1.165, 0.94),
    ("nozzle", 1, 0.0200, 1.000, 0.50),
    ("nozzle", 2, 0.0230, 1.015, 0.54),
    ("nozzle", 3, 0.0260, 1.030, 0.58),
    ("nozzle", 4, 0.0290, 1.045, 0.62),
    ("nozzle", 5, 0.0320, 1.060, 0.66),
    ("nozzle", 6, 0.0350, 1.075, 0.70),
    ("nozzle", 7, 0.0380, 1.090, 0.74),
    ("nozzle", 8, 0.0410, 1.105, 0.78),
    ("nozzle", 9, 0.0440, 1.120, 0.82),
    ("nozzle", 10, 0.0470, 1.135, 0.86),
    ("nozzle", 11, 0.0500, 1.150, 0.90),
    ("nozzle", 12, 0.0530, 1.165, 0.94),
    ("thermal", 2, 0.0200, 1.000, 0.50),
    ("thermal", 3, 0.0230, 1.015, 0.54),
    ("thermal", 4, 0.0260, 1.030, 0.58),
    ("thermal", 5, 0.0290, 1.045, 0.62),
    ("thermal", 6, 0.0320, 1.060, 0.66),
    ("thermal", 7, 0.0350, 1.075, 0.70),
    ("thermal", 8, 0.0380, 1.090, 0.74),
    ("thermal", 9, 0.0410, 1.105, 0.78),
    ("thermal", 10, 0.0440, 1.120, 0.82),
    ("thermal", 11, 0.0470, 1.135, 0.86),
    ("thermal", 12, 0.0500, 1.150, 0.90),
    ("thermal", 13, 0.0530, 1.165, 0.94),
    ("header", 3, 0.0200, 1.000, 0.50),
    ("header", 4, 0.0230, 1.015, 0.54),
    ("header", 5, 0.0260, 1.030, 0.58),
    ("header", 6, 0.0290, 1.045, 0.62),
    ("header", 7, 0.0320, 1.060, 0.66),
    ("header", 8, 0.0350, 1.075, 0.70),
    ("header", 9, 0.0380, 1.090, 0.74),
    ("header", 10, 0.0410, 1.105, 0.78),
    ("header", 11, 0.0440, 1.120, 0.82),
    ("header", 12, 0.0470, 1.135, 0.86),
    ("header", 13, 0.0500, 1.150, 0.90),
    ("header", 14, 0.0530, 1.165, 0.94),
    ("branch", 4, 0.0200, 1.000, 0.50),
    ("branch", 5, 0.0230, 1.015, 0.54),
    ("branch", 6, 0.0260, 1.030, 0.58),
    ("branch", 7, 0.0290, 1.045, 0.62),
    ("branch", 8, 0.0320, 1.060, 0.66),
    ("branch", 9, 0.0350, 1.075, 0.70),
    ("branch", 10, 0.0380, 1.090, 0.74),
    ("branch", 11, 0.0410, 1.105, 0.78),
    ("branch", 12, 0.0440, 1.120, 0.82),
    ("branch", 13, 0.0470, 1.135, 0.86),
    ("branch", 14, 0.0500, 1.150, 0.90),
    ("branch", 15, 0.0530, 1.165, 0.94),
    ("coil", 5, 0.0200, 1.000, 0.50),
    ("coil", 6, 0.0230, 1.015, 0.54),
    ("coil", 7, 0.0260, 1.030, 0.58),
    ("coil", 8, 0.0290, 1.045, 0.62),
    ("coil", 9, 0.0320, 1.060, 0.66),
    ("coil", 10, 0.0350, 1.075, 0.70),
    ("coil", 11, 0.0380, 1.090, 0.74),
    ("coil", 12, 0.0410, 1.105, 0.78),
    ("coil", 13, 0.0440, 1.120, 0.82),
    ("coil", 14, 0.0470, 1.135, 0.86),
    ("coil", 15, 0.0500, 1.150, 0.90),
    ("coil", 16, 0.0530, 1.165, 0.94),
    ("duct", 6, 0.0200, 1.000, 0.50),
    ("duct", 7, 0.0230, 1.015, 0.54),
    ("duct", 8, 0.0260, 1.030, 0.58),
    ("duct", 9, 0.0290, 1.045, 0.62),
    ("duct", 10, 0.0320, 1.060, 0.66),
    ("duct", 11, 0.0350, 1.075, 0.70),
    ("duct", 12, 0.0380, 1.090, 0.74),
    ("duct", 13, 0.0410, 1.105, 0.78),
    ("duct", 14, 0.0440, 1.120, 0.82),
    ("duct", 15, 0.0470, 1.135, 0.86),
    ("duct", 16, 0.0500, 1.150, 0.90),
    ("duct", 17, 0.0530, 1.165, 0.94),
    ("plenum", 7, 0.0200, 1.000, 0.50),
    ("plenum", 8, 0.0230, 1.015, 0.54),
    ("plenum", 9, 0.0260, 1.030, 0.58),
    ("plenum", 10, 0.0290, 1.045, 0.62),
    ("plenum", 11, 0.0320, 1.060, 0.66),
    ("plenum", 12, 0.0350, 1.075, 0.70),
    ("plenum", 13, 0.0380, 1.090, 0.74),
    ("plenum", 14, 0.0410, 1.105, 0.78),
    ("plenum", 15, 0.0440, 1.120, 0.82),
    ("plenum", 16, 0.0470, 1.135, 0.86),
    ("plenum", 17, 0.0500, 1.150, 0.90),
    ("plenum", 18, 0.0530, 1.165, 0.94),
)


def _segment_count(case: CaseSpec) -> int:
    length = case.geometry.length_m
    diameter = case.geometry.hydraulic_diameter_m
    target = max(4, int(math.ceil(length / max(diameter, 1e-6))))
    for count, _, _ in _DISCRETIZATION:
        if count >= target:
            return count
    return _DISCRETIZATION[-1][0]


def _fitting_loss(case: CaseSpec, dynamic_pressure: float) -> float:
    raw = case.family.split("-", 1)[0]
    aliases = {
        "distribution": "manifold",
        "compressible": "nozzle",
        "cooling": "thermal",
    }
    prefix = aliases.get(raw, raw)
    rows = [row for row in _FITTINGS if row[0] == prefix] or [row for row in _FITTINGS if row[0] == "manifold"]
    total_k = case.geometry.minor_loss_coefficient
    for _, ordinal, minor_k, area_ratio, swirl in rows[:4]:
        total_k += minor_k * area_ratio * (1.0 + swirl * 0.1) / (1.0 + ordinal * 0.01)
    return total_k * dynamic_pressure


def _segment_loss(
    case: CaseSpec,
    density_kg_m3: float,
    velocity_m_s: float,
    reynolds: float,
    segment_length_m: float,
) -> float:
    geometry = case.geometry
    rel = geometry.roughness_m / max(geometry.hydraulic_diameter_m, 1e-12)
    friction = colebrook_haaland_blend(reynolds, rel) * friction_policy_factor(case, reynolds, rel)
    dynamic = 0.5 * density_kg_m3 * velocity_m_s ** 2
    length_term = friction * segment_length_m / max(geometry.hydraulic_diameter_m, 1e-12)
    return length_term * dynamic


def segmented_dynamic_loss(
    case: CaseSpec,
    density_kg_m3: float,
    velocity_m_s: float,
    reynolds: float,
) -> float:
    segments = _segment_count(case)
    geometry = case.geometry
    segment_length = geometry.length_m / segments
    dynamic = 0.5 * density_kg_m3 * velocity_m_s ** 2
    distributed = 0.0
    for index in range(segments):
        bias = _DISCRETIZATION[index % len(_DISCRETIZATION)][2]
        distributed += _segment_loss(
            case,
            density_kg_m3,
            velocity_m_s,
            reynolds * (1.0 + 0.001 * index),
            segment_length * bias,
        )
    distributed /= segments
    return distributed + _fitting_loss(case, dynamic)
