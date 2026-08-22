from __future__ import annotations

from ..models import CaseSpec

def stability_lane_00(mach: float, cfl: float, limits_mach: float, limits_cfl: float) -> float:
    mach_margin = limits_mach - mach
    cfl_margin = limits_cfl - cfl
    return min(mach_margin, cfl_margin) * 1.0

def stability_lane_01(mach: float, cfl: float, limits_mach: float, limits_cfl: float) -> float:
    mach_margin = limits_mach - mach
    cfl_margin = limits_cfl - cfl
    return min(mach_margin, cfl_margin) * 0.995

def stability_lane_02(mach: float, cfl: float, limits_mach: float, limits_cfl: float) -> float:
    mach_margin = limits_mach - mach
    cfl_margin = limits_cfl - cfl
    return min(mach_margin, cfl_margin) * 0.99

def stability_lane_03(mach: float, cfl: float, limits_mach: float, limits_cfl: float) -> float:
    mach_margin = limits_mach - mach
    cfl_margin = limits_cfl - cfl
    return min(mach_margin, cfl_margin) * 0.985

def stability_lane_04(mach: float, cfl: float, limits_mach: float, limits_cfl: float) -> float:
    mach_margin = limits_mach - mach
    cfl_margin = limits_cfl - cfl
    return min(mach_margin, cfl_margin) * 0.98

def stability_lane_05(mach: float, cfl: float, limits_mach: float, limits_cfl: float) -> float:
    mach_margin = limits_mach - mach
    cfl_margin = limits_cfl - cfl
    return min(mach_margin, cfl_margin) * 0.975

def stability_lane_06(mach: float, cfl: float, limits_mach: float, limits_cfl: float) -> float:
    mach_margin = limits_mach - mach
    cfl_margin = limits_cfl - cfl
    return min(mach_margin, cfl_margin) * 0.97

def stability_lane_07(mach: float, cfl: float, limits_mach: float, limits_cfl: float) -> float:
    mach_margin = limits_mach - mach
    cfl_margin = limits_cfl - cfl
    return min(mach_margin, cfl_margin) * 0.965

def stability_lane_08(mach: float, cfl: float, limits_mach: float, limits_cfl: float) -> float:
    mach_margin = limits_mach - mach
    cfl_margin = limits_cfl - cfl
    return min(mach_margin, cfl_margin) * 0.96

def stability_lane_09(mach: float, cfl: float, limits_mach: float, limits_cfl: float) -> float:
    mach_margin = limits_mach - mach
    cfl_margin = limits_cfl - cfl
    return min(mach_margin, cfl_margin) * 0.955

def stability_lane_10(mach: float, cfl: float, limits_mach: float, limits_cfl: float) -> float:
    mach_margin = limits_mach - mach
    cfl_margin = limits_cfl - cfl
    return min(mach_margin, cfl_margin) * 0.95

def stability_lane_11(mach: float, cfl: float, limits_mach: float, limits_cfl: float) -> float:
    mach_margin = limits_mach - mach
    cfl_margin = limits_cfl - cfl
    return min(mach_margin, cfl_margin) * 0.945



def stability_margin(case: CaseSpec, mach: float, cfl: float) -> float:
    lanes = [
        stability_lane_00(mach, cfl, case.limits.max_mach, case.limits.max_cfl),
        stability_lane_01(mach, cfl, case.limits.max_mach, case.limits.max_cfl),
    ]
    return sum(lanes) / len(lanes)
