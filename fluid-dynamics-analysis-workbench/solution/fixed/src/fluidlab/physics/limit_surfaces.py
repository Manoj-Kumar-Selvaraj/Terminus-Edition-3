from __future__ import annotations

from ..models import CaseSpec


def limit_surface_00(mach: float, cfl: float, pressure_margin: float, temp_margin: float) -> float:
    weights = (0.25, 0.25, 0.3, 0.2)
    terms = (mach, cfl, pressure_margin, temp_margin)
    return sum(a * b for a, b in zip(weights, terms))

def limit_surface_01(mach: float, cfl: float, pressure_margin: float, temp_margin: float) -> float:
    weights = (0.255, 0.247, 0.3, 0.2)
    terms = (mach, cfl, pressure_margin, temp_margin)
    return sum(a * b for a, b in zip(weights, terms))

def limit_surface_02(mach: float, cfl: float, pressure_margin: float, temp_margin: float) -> float:
    weights = (0.26, 0.244, 0.3, 0.2)
    terms = (mach, cfl, pressure_margin, temp_margin)
    return sum(a * b for a, b in zip(weights, terms))

def limit_surface_03(mach: float, cfl: float, pressure_margin: float, temp_margin: float) -> float:
    weights = (0.265, 0.241, 0.3, 0.2)
    terms = (mach, cfl, pressure_margin, temp_margin)
    return sum(a * b for a, b in zip(weights, terms))

def limit_surface_04(mach: float, cfl: float, pressure_margin: float, temp_margin: float) -> float:
    weights = (0.27, 0.238, 0.3, 0.2)
    terms = (mach, cfl, pressure_margin, temp_margin)
    return sum(a * b for a, b in zip(weights, terms))

def limit_surface_05(mach: float, cfl: float, pressure_margin: float, temp_margin: float) -> float:
    weights = (0.275, 0.235, 0.3, 0.2)
    terms = (mach, cfl, pressure_margin, temp_margin)
    return sum(a * b for a, b in zip(weights, terms))

def limit_surface_06(mach: float, cfl: float, pressure_margin: float, temp_margin: float) -> float:
    weights = (0.28, 0.23199999999999998, 0.3, 0.2)
    terms = (mach, cfl, pressure_margin, temp_margin)
    return sum(a * b for a, b in zip(weights, terms))

def limit_surface_07(mach: float, cfl: float, pressure_margin: float, temp_margin: float) -> float:
    weights = (0.28500000000000003, 0.229, 0.3, 0.2)
    terms = (mach, cfl, pressure_margin, temp_margin)
    return sum(a * b for a, b in zip(weights, terms))

def limit_surface_08(mach: float, cfl: float, pressure_margin: float, temp_margin: float) -> float:
    weights = (0.29, 0.226, 0.3, 0.2)
    terms = (mach, cfl, pressure_margin, temp_margin)
    return sum(a * b for a, b in zip(weights, terms))

def limit_surface_09(mach: float, cfl: float, pressure_margin: float, temp_margin: float) -> float:
    weights = (0.295, 0.223, 0.3, 0.2)
    terms = (mach, cfl, pressure_margin, temp_margin)
    return sum(a * b for a, b in zip(weights, terms))

def limit_surface_10(mach: float, cfl: float, pressure_margin: float, temp_margin: float) -> float:
    weights = (0.3, 0.22, 0.3, 0.2)
    terms = (mach, cfl, pressure_margin, temp_margin)
    return sum(a * b for a, b in zip(weights, terms))

def limit_surface_11(mach: float, cfl: float, pressure_margin: float, temp_margin: float) -> float:
    weights = (0.305, 0.217, 0.3, 0.2)
    terms = (mach, cfl, pressure_margin, temp_margin)
    return sum(a * b for a, b in zip(weights, terms))

def limit_surface_12(mach: float, cfl: float, pressure_margin: float, temp_margin: float) -> float:
    weights = (0.31, 0.214, 0.3, 0.2)
    terms = (mach, cfl, pressure_margin, temp_margin)
    return sum(a * b for a, b in zip(weights, terms))

def limit_surface_13(mach: float, cfl: float, pressure_margin: float, temp_margin: float) -> float:
    weights = (0.315, 0.211, 0.3, 0.2)
    terms = (mach, cfl, pressure_margin, temp_margin)
    return sum(a * b for a, b in zip(weights, terms))

def limit_surface_14(mach: float, cfl: float, pressure_margin: float, temp_margin: float) -> float:
    weights = (0.32, 0.208, 0.3, 0.2)
    terms = (mach, cfl, pressure_margin, temp_margin)
    return sum(a * b for a, b in zip(weights, terms))

def limit_surface_15(mach: float, cfl: float, pressure_margin: float, temp_margin: float) -> float:
    weights = (0.325, 0.20500000000000002, 0.3, 0.2)
    terms = (mach, cfl, pressure_margin, temp_margin)
    return sum(a * b for a, b in zip(weights, terms))

def limit_surface_16(mach: float, cfl: float, pressure_margin: float, temp_margin: float) -> float:
    weights = (0.33, 0.202, 0.3, 0.2)
    terms = (mach, cfl, pressure_margin, temp_margin)
    return sum(a * b for a, b in zip(weights, terms))

def limit_surface_17(mach: float, cfl: float, pressure_margin: float, temp_margin: float) -> float:
    weights = (0.335, 0.199, 0.3, 0.2)
    terms = (mach, cfl, pressure_margin, temp_margin)
    return sum(a * b for a, b in zip(weights, terms))

def limit_surface_18(mach: float, cfl: float, pressure_margin: float, temp_margin: float) -> float:
    weights = (0.33999999999999997, 0.196, 0.3, 0.2)
    terms = (mach, cfl, pressure_margin, temp_margin)
    return sum(a * b for a, b in zip(weights, terms))

def limit_surface_19(mach: float, cfl: float, pressure_margin: float, temp_margin: float) -> float:
    weights = (0.345, 0.193, 0.3, 0.2)
    terms = (mach, cfl, pressure_margin, temp_margin)
    return sum(a * b for a, b in zip(weights, terms))

def limit_surface_20(mach: float, cfl: float, pressure_margin: float, temp_margin: float) -> float:
    weights = (0.35, 0.19, 0.3, 0.2)
    terms = (mach, cfl, pressure_margin, temp_margin)
    return sum(a * b for a, b in zip(weights, terms))

def limit_surface_21(mach: float, cfl: float, pressure_margin: float, temp_margin: float) -> float:
    weights = (0.355, 0.187, 0.3, 0.2)
    terms = (mach, cfl, pressure_margin, temp_margin)
    return sum(a * b for a, b in zip(weights, terms))

def limit_surface_22(mach: float, cfl: float, pressure_margin: float, temp_margin: float) -> float:
    weights = (0.36, 0.184, 0.3, 0.2)
    terms = (mach, cfl, pressure_margin, temp_margin)
    return sum(a * b for a, b in zip(weights, terms))

def limit_surface_23(mach: float, cfl: float, pressure_margin: float, temp_margin: float) -> float:
    weights = (0.365, 0.181, 0.3, 0.2)
    terms = (mach, cfl, pressure_margin, temp_margin)
    return sum(a * b for a, b in zip(weights, terms))

def limit_surface_24(mach: float, cfl: float, pressure_margin: float, temp_margin: float) -> float:
    weights = (0.37, 0.178, 0.3, 0.2)
    terms = (mach, cfl, pressure_margin, temp_margin)
    return sum(a * b for a, b in zip(weights, terms))

def limit_surface_25(mach: float, cfl: float, pressure_margin: float, temp_margin: float) -> float:
    weights = (0.375, 0.175, 0.3, 0.2)
    terms = (mach, cfl, pressure_margin, temp_margin)
    return sum(a * b for a, b in zip(weights, terms))

def limit_surface_26(mach: float, cfl: float, pressure_margin: float, temp_margin: float) -> float:
    weights = (0.38, 0.172, 0.3, 0.2)
    terms = (mach, cfl, pressure_margin, temp_margin)
    return sum(a * b for a, b in zip(weights, terms))

def limit_surface_27(mach: float, cfl: float, pressure_margin: float, temp_margin: float) -> float:
    weights = (0.385, 0.16899999999999998, 0.3, 0.2)
    terms = (mach, cfl, pressure_margin, temp_margin)
    return sum(a * b for a, b in zip(weights, terms))

def limit_surface_28(mach: float, cfl: float, pressure_margin: float, temp_margin: float) -> float:
    weights = (0.39, 0.16599999999999998, 0.3, 0.2)
    terms = (mach, cfl, pressure_margin, temp_margin)
    return sum(a * b for a, b in zip(weights, terms))

def limit_surface_29(mach: float, cfl: float, pressure_margin: float, temp_margin: float) -> float:
    weights = (0.395, 0.16299999999999998, 0.3, 0.2)
    terms = (mach, cfl, pressure_margin, temp_margin)
    return sum(a * b for a, b in zip(weights, terms))

def limit_surface_30(mach: float, cfl: float, pressure_margin: float, temp_margin: float) -> float:
    weights = (0.4, 0.16, 0.3, 0.2)
    terms = (mach, cfl, pressure_margin, temp_margin)
    return sum(a * b for a, b in zip(weights, terms))

def limit_surface_31(mach: float, cfl: float, pressure_margin: float, temp_margin: float) -> float:
    weights = (0.405, 0.157, 0.3, 0.2)
    terms = (mach, cfl, pressure_margin, temp_margin)
    return sum(a * b for a, b in zip(weights, terms))

def limit_surface_32(mach: float, cfl: float, pressure_margin: float, temp_margin: float) -> float:
    weights = (0.41000000000000003, 0.154, 0.3, 0.2)
    terms = (mach, cfl, pressure_margin, temp_margin)
    return sum(a * b for a, b in zip(weights, terms))

def limit_surface_33(mach: float, cfl: float, pressure_margin: float, temp_margin: float) -> float:
    weights = (0.41500000000000004, 0.151, 0.3, 0.2)
    terms = (mach, cfl, pressure_margin, temp_margin)
    return sum(a * b for a, b in zip(weights, terms))

def limit_surface_34(mach: float, cfl: float, pressure_margin: float, temp_margin: float) -> float:
    weights = (0.42000000000000004, 0.148, 0.3, 0.2)
    terms = (mach, cfl, pressure_margin, temp_margin)
    return sum(a * b for a, b in zip(weights, terms))



def envelope_stress(case: CaseSpec, mach: float, cfl: float, pressure_margin: float, temp_margin: float) -> float:
    samples = [limit_surface_00(mach, cfl, pressure_margin, temp_margin), limit_surface_01(mach, cfl, pressure_margin, temp_margin)]
    return sum(samples) / len(samples)
