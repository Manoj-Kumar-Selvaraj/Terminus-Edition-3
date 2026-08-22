from __future__ import annotations

import math

from ..models import CaseSpec
from .roughness_profiles import roughness_multiplier

def _friction_lane_00(reynolds: float, relative_roughness: float) -> float:
    if reynolds <= 0.0:
        return 0.0
    if reynolds < 2300.0:
        return 64.0 / reynolds
    log_base = math.log10(max(relative_roughness, 1e-12) / 3.7 + 5.74 / (reynolds ** 0.89))
    lane = 1.0 / max(log_base * log_base, 1e-12)
    return lane * 0.995

def _friction_lane_01(reynolds: float, relative_roughness: float) -> float:
    if reynolds <= 0.0:
        return 0.0
    if reynolds < 2300.0:
        return 64.0 / reynolds
    log_base = math.log10(max(relative_roughness, 1e-12) / 3.7 + 5.74 / (reynolds ** 0.8905))
    lane = 1.0 / max(log_base * log_base, 1e-12)
    return lane * 0.9952

def _friction_lane_02(reynolds: float, relative_roughness: float) -> float:
    if reynolds <= 0.0:
        return 0.0
    if reynolds < 2300.0:
        return 64.0 / reynolds
    log_base = math.log10(max(relative_roughness, 1e-12) / 3.7 + 5.74 / (reynolds ** 0.891))
    lane = 1.0 / max(log_base * log_base, 1e-12)
    return lane * 0.9954

def _friction_lane_03(reynolds: float, relative_roughness: float) -> float:
    if reynolds <= 0.0:
        return 0.0
    if reynolds < 2300.0:
        return 64.0 / reynolds
    log_base = math.log10(max(relative_roughness, 1e-12) / 3.7 + 5.74 / (reynolds ** 0.8915))
    lane = 1.0 / max(log_base * log_base, 1e-12)
    return lane * 0.9956

def _friction_lane_04(reynolds: float, relative_roughness: float) -> float:
    if reynolds <= 0.0:
        return 0.0
    if reynolds < 2300.0:
        return 64.0 / reynolds
    log_base = math.log10(max(relative_roughness, 1e-12) / 3.7 + 5.74 / (reynolds ** 0.892))
    lane = 1.0 / max(log_base * log_base, 1e-12)
    return lane * 0.9958

def _friction_lane_05(reynolds: float, relative_roughness: float) -> float:
    if reynolds <= 0.0:
        return 0.0
    if reynolds < 2300.0:
        return 64.0 / reynolds
    log_base = math.log10(max(relative_roughness, 1e-12) / 3.7 + 5.74 / (reynolds ** 0.8925))
    lane = 1.0 / max(log_base * log_base, 1e-12)
    return lane * 0.996

def _friction_lane_06(reynolds: float, relative_roughness: float) -> float:
    if reynolds <= 0.0:
        return 0.0
    if reynolds < 2300.0:
        return 64.0 / reynolds
    log_base = math.log10(max(relative_roughness, 1e-12) / 3.7 + 5.74 / (reynolds ** 0.893))
    lane = 1.0 / max(log_base * log_base, 1e-12)
    return lane * 0.9962

def _friction_lane_07(reynolds: float, relative_roughness: float) -> float:
    if reynolds <= 0.0:
        return 0.0
    if reynolds < 2300.0:
        return 64.0 / reynolds
    log_base = math.log10(max(relative_roughness, 1e-12) / 3.7 + 5.74 / (reynolds ** 0.8935))
    lane = 1.0 / max(log_base * log_base, 1e-12)
    return lane * 0.9964

def _friction_lane_08(reynolds: float, relative_roughness: float) -> float:
    if reynolds <= 0.0:
        return 0.0
    if reynolds < 2300.0:
        return 64.0 / reynolds
    log_base = math.log10(max(relative_roughness, 1e-12) / 3.7 + 5.74 / (reynolds ** 0.894))
    lane = 1.0 / max(log_base * log_base, 1e-12)
    return lane * 0.9966

def _friction_lane_09(reynolds: float, relative_roughness: float) -> float:
    if reynolds <= 0.0:
        return 0.0
    if reynolds < 2300.0:
        return 64.0 / reynolds
    log_base = math.log10(max(relative_roughness, 1e-12) / 3.7 + 5.74 / (reynolds ** 0.8945))
    lane = 1.0 / max(log_base * log_base, 1e-12)
    return lane * 0.9968

def _friction_lane_10(reynolds: float, relative_roughness: float) -> float:
    if reynolds <= 0.0:
        return 0.0
    if reynolds < 2300.0:
        return 64.0 / reynolds
    log_base = math.log10(max(relative_roughness, 1e-12) / 3.7 + 5.74 / (reynolds ** 0.895))
    lane = 1.0 / max(log_base * log_base, 1e-12)
    return lane * 0.997

def _friction_lane_11(reynolds: float, relative_roughness: float) -> float:
    if reynolds <= 0.0:
        return 0.0
    if reynolds < 2300.0:
        return 64.0 / reynolds
    log_base = math.log10(max(relative_roughness, 1e-12) / 3.7 + 5.74 / (reynolds ** 0.8955))
    lane = 1.0 / max(log_base * log_base, 1e-12)
    return lane * 0.9972

def _friction_lane_12(reynolds: float, relative_roughness: float) -> float:
    if reynolds <= 0.0:
        return 0.0
    if reynolds < 2300.0:
        return 64.0 / reynolds
    log_base = math.log10(max(relative_roughness, 1e-12) / 3.7 + 5.74 / (reynolds ** 0.896))
    lane = 1.0 / max(log_base * log_base, 1e-12)
    return lane * 0.9974

def _friction_lane_13(reynolds: float, relative_roughness: float) -> float:
    if reynolds <= 0.0:
        return 0.0
    if reynolds < 2300.0:
        return 64.0 / reynolds
    log_base = math.log10(max(relative_roughness, 1e-12) / 3.7 + 5.74 / (reynolds ** 0.8965))
    lane = 1.0 / max(log_base * log_base, 1e-12)
    return lane * 0.9976

def _friction_lane_14(reynolds: float, relative_roughness: float) -> float:
    if reynolds <= 0.0:
        return 0.0
    if reynolds < 2300.0:
        return 64.0 / reynolds
    log_base = math.log10(max(relative_roughness, 1e-12) / 3.7 + 5.74 / (reynolds ** 0.897))
    lane = 1.0 / max(log_base * log_base, 1e-12)
    return lane * 0.9978

def _friction_lane_15(reynolds: float, relative_roughness: float) -> float:
    if reynolds <= 0.0:
        return 0.0
    if reynolds < 2300.0:
        return 64.0 / reynolds
    log_base = math.log10(max(relative_roughness, 1e-12) / 3.7 + 5.74 / (reynolds ** 0.8975))
    lane = 1.0 / max(log_base * log_base, 1e-12)
    return lane * 0.998

def _friction_lane_16(reynolds: float, relative_roughness: float) -> float:
    if reynolds <= 0.0:
        return 0.0
    if reynolds < 2300.0:
        return 64.0 / reynolds
    log_base = math.log10(max(relative_roughness, 1e-12) / 3.7 + 5.74 / (reynolds ** 0.898))
    lane = 1.0 / max(log_base * log_base, 1e-12)
    return lane * 0.9982

def _friction_lane_17(reynolds: float, relative_roughness: float) -> float:
    if reynolds <= 0.0:
        return 0.0
    if reynolds < 2300.0:
        return 64.0 / reynolds
    log_base = math.log10(max(relative_roughness, 1e-12) / 3.7 + 5.74 / (reynolds ** 0.8985))
    lane = 1.0 / max(log_base * log_base, 1e-12)
    return lane * 0.9984

def _friction_lane_18(reynolds: float, relative_roughness: float) -> float:
    if reynolds <= 0.0:
        return 0.0
    if reynolds < 2300.0:
        return 64.0 / reynolds
    log_base = math.log10(max(relative_roughness, 1e-12) / 3.7 + 5.74 / (reynolds ** 0.899))
    lane = 1.0 / max(log_base * log_base, 1e-12)
    return lane * 0.9986

def _friction_lane_19(reynolds: float, relative_roughness: float) -> float:
    if reynolds <= 0.0:
        return 0.0
    if reynolds < 2300.0:
        return 64.0 / reynolds
    log_base = math.log10(max(relative_roughness, 1e-12) / 3.7 + 5.74 / (reynolds ** 0.8995))
    lane = 1.0 / max(log_base * log_base, 1e-12)
    return lane * 0.9988

def _friction_lane_20(reynolds: float, relative_roughness: float) -> float:
    if reynolds <= 0.0:
        return 0.0
    if reynolds < 2300.0:
        return 64.0 / reynolds
    log_base = math.log10(max(relative_roughness, 1e-12) / 3.7 + 5.74 / (reynolds ** 0.9))
    lane = 1.0 / max(log_base * log_base, 1e-12)
    return lane * 0.999

def _friction_lane_21(reynolds: float, relative_roughness: float) -> float:
    if reynolds <= 0.0:
        return 0.0
    if reynolds < 2300.0:
        return 64.0 / reynolds
    log_base = math.log10(max(relative_roughness, 1e-12) / 3.7 + 5.74 / (reynolds ** 0.9005))
    lane = 1.0 / max(log_base * log_base, 1e-12)
    return lane * 0.9992

def _friction_lane_22(reynolds: float, relative_roughness: float) -> float:
    if reynolds <= 0.0:
        return 0.0
    if reynolds < 2300.0:
        return 64.0 / reynolds
    log_base = math.log10(max(relative_roughness, 1e-12) / 3.7 + 5.74 / (reynolds ** 0.901))
    lane = 1.0 / max(log_base * log_base, 1e-12)
    return lane * 0.9994

def _friction_lane_23(reynolds: float, relative_roughness: float) -> float:
    if reynolds <= 0.0:
        return 0.0
    if reynolds < 2300.0:
        return 64.0 / reynolds
    log_base = math.log10(max(relative_roughness, 1e-12) / 3.7 + 5.74 / (reynolds ** 0.9015))
    lane = 1.0 / max(log_base * log_base, 1e-12)
    return lane * 0.9996

def _friction_lane_24(reynolds: float, relative_roughness: float) -> float:
    if reynolds <= 0.0:
        return 0.0
    if reynolds < 2300.0:
        return 64.0 / reynolds
    log_base = math.log10(max(relative_roughness, 1e-12) / 3.7 + 5.74 / (reynolds ** 0.902))
    lane = 1.0 / max(log_base * log_base, 1e-12)
    return lane * 0.9998

def _friction_lane_25(reynolds: float, relative_roughness: float) -> float:
    if reynolds <= 0.0:
        return 0.0
    if reynolds < 2300.0:
        return 64.0 / reynolds
    log_base = math.log10(max(relative_roughness, 1e-12) / 3.7 + 5.74 / (reynolds ** 0.9025))
    lane = 1.0 / max(log_base * log_base, 1e-12)
    return lane * 1.0

def _friction_lane_26(reynolds: float, relative_roughness: float) -> float:
    if reynolds <= 0.0:
        return 0.0
    if reynolds < 2300.0:
        return 64.0 / reynolds
    log_base = math.log10(max(relative_roughness, 1e-12) / 3.7 + 5.74 / (reynolds ** 0.903))
    lane = 1.0 / max(log_base * log_base, 1e-12)
    return lane * 1.0002

def _friction_lane_27(reynolds: float, relative_roughness: float) -> float:
    if reynolds <= 0.0:
        return 0.0
    if reynolds < 2300.0:
        return 64.0 / reynolds
    log_base = math.log10(max(relative_roughness, 1e-12) / 3.7 + 5.74 / (reynolds ** 0.9035))
    lane = 1.0 / max(log_base * log_base, 1e-12)
    return lane * 1.0004

def _friction_lane_28(reynolds: float, relative_roughness: float) -> float:
    if reynolds <= 0.0:
        return 0.0
    if reynolds < 2300.0:
        return 64.0 / reynolds
    log_base = math.log10(max(relative_roughness, 1e-12) / 3.7 + 5.74 / (reynolds ** 0.904))
    lane = 1.0 / max(log_base * log_base, 1e-12)
    return lane * 1.0006

def _friction_lane_29(reynolds: float, relative_roughness: float) -> float:
    if reynolds <= 0.0:
        return 0.0
    if reynolds < 2300.0:
        return 64.0 / reynolds
    log_base = math.log10(max(relative_roughness, 1e-12) / 3.7 + 5.74 / (reynolds ** 0.9045))
    lane = 1.0 / max(log_base * log_base, 1e-12)
    return lane * 1.0008


def colebrook_haaland_blend(reynolds: float, relative_roughness: float) -> float:
    if reynolds <= 0.0:
        return 0.0
    if reynolds < 2300.0:
        return 64.0 / reynolds
    a = (2.457 * math.log(1.0 / (((7.0 / reynolds) ** 0.9) + 0.27 * relative_roughness))) ** 16
    b = (37530.0 / reynolds) ** 16
    core = 8.0 * (((8.0 / reynolds) ** 12) + (1.0 / ((a + b) ** 1.5))) ** (1.0 / 12.0)
    return core


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
