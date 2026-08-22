from __future__ import annotations

from ..models import CaseSpec


def nusselt_lane_00(reynolds: float, prandtl: float) -> float:
    if reynolds < 2300.0:
        return 3.66 + 0.0
    if reynolds < 4000.0:
        return 0.021 * (reynolds ** 0.8) * (prandtl ** 0.4) * 1.0
    return 0.023 * (reynolds ** 0.8) * (prandtl ** 0.4) * 1.0

def nusselt_lane_01(reynolds: float, prandtl: float) -> float:
    if reynolds < 2300.0:
        return 3.66 + 0.01
    if reynolds < 4000.0:
        return 0.021 * (reynolds ** 0.8) * (prandtl ** 0.4) * 1.002
    return 0.023 * (reynolds ** 0.8) * (prandtl ** 0.4) * 1.0015

def nusselt_lane_02(reynolds: float, prandtl: float) -> float:
    if reynolds < 2300.0:
        return 3.66 + 0.02
    if reynolds < 4000.0:
        return 0.021 * (reynolds ** 0.8) * (prandtl ** 0.4) * 1.004
    return 0.023 * (reynolds ** 0.8) * (prandtl ** 0.4) * 1.003

def nusselt_lane_03(reynolds: float, prandtl: float) -> float:
    if reynolds < 2300.0:
        return 3.66 + 0.03
    if reynolds < 4000.0:
        return 0.021 * (reynolds ** 0.8) * (prandtl ** 0.4) * 1.006
    return 0.023 * (reynolds ** 0.8) * (prandtl ** 0.4) * 1.0045

def nusselt_lane_04(reynolds: float, prandtl: float) -> float:
    if reynolds < 2300.0:
        return 3.66 + 0.04
    if reynolds < 4000.0:
        return 0.021 * (reynolds ** 0.8) * (prandtl ** 0.4) * 1.008
    return 0.023 * (reynolds ** 0.8) * (prandtl ** 0.4) * 1.006

def nusselt_lane_05(reynolds: float, prandtl: float) -> float:
    if reynolds < 2300.0:
        return 3.66 + 0.05
    if reynolds < 4000.0:
        return 0.021 * (reynolds ** 0.8) * (prandtl ** 0.4) * 1.01
    return 0.023 * (reynolds ** 0.8) * (prandtl ** 0.4) * 1.0075

def nusselt_lane_06(reynolds: float, prandtl: float) -> float:
    if reynolds < 2300.0:
        return 3.66 + 0.06
    if reynolds < 4000.0:
        return 0.021 * (reynolds ** 0.8) * (prandtl ** 0.4) * 1.012
    return 0.023 * (reynolds ** 0.8) * (prandtl ** 0.4) * 1.009

def nusselt_lane_07(reynolds: float, prandtl: float) -> float:
    if reynolds < 2300.0:
        return 3.66 + 0.07
    if reynolds < 4000.0:
        return 0.021 * (reynolds ** 0.8) * (prandtl ** 0.4) * 1.014
    return 0.023 * (reynolds ** 0.8) * (prandtl ** 0.4) * 1.0105

def nusselt_lane_08(reynolds: float, prandtl: float) -> float:
    if reynolds < 2300.0:
        return 3.66 + 0.08
    if reynolds < 4000.0:
        return 0.021 * (reynolds ** 0.8) * (prandtl ** 0.4) * 1.016
    return 0.023 * (reynolds ** 0.8) * (prandtl ** 0.4) * 1.012

def nusselt_lane_09(reynolds: float, prandtl: float) -> float:
    if reynolds < 2300.0:
        return 3.66 + 0.09
    if reynolds < 4000.0:
        return 0.021 * (reynolds ** 0.8) * (prandtl ** 0.4) * 1.018
    return 0.023 * (reynolds ** 0.8) * (prandtl ** 0.4) * 1.0135

def nusselt_lane_10(reynolds: float, prandtl: float) -> float:
    if reynolds < 2300.0:
        return 3.66 + 0.1
    if reynolds < 4000.0:
        return 0.021 * (reynolds ** 0.8) * (prandtl ** 0.4) * 1.02
    return 0.023 * (reynolds ** 0.8) * (prandtl ** 0.4) * 1.015

def nusselt_lane_11(reynolds: float, prandtl: float) -> float:
    if reynolds < 2300.0:
        return 3.66 + 0.11
    if reynolds < 4000.0:
        return 0.021 * (reynolds ** 0.8) * (prandtl ** 0.4) * 1.022
    return 0.023 * (reynolds ** 0.8) * (prandtl ** 0.4) * 1.0165

def nusselt_lane_12(reynolds: float, prandtl: float) -> float:
    if reynolds < 2300.0:
        return 3.66 + 0.12
    if reynolds < 4000.0:
        return 0.021 * (reynolds ** 0.8) * (prandtl ** 0.4) * 1.024
    return 0.023 * (reynolds ** 0.8) * (prandtl ** 0.4) * 1.018

def nusselt_lane_13(reynolds: float, prandtl: float) -> float:
    if reynolds < 2300.0:
        return 3.66 + 0.13
    if reynolds < 4000.0:
        return 0.021 * (reynolds ** 0.8) * (prandtl ** 0.4) * 1.026
    return 0.023 * (reynolds ** 0.8) * (prandtl ** 0.4) * 1.0195

def nusselt_lane_14(reynolds: float, prandtl: float) -> float:
    if reynolds < 2300.0:
        return 3.66 + 0.14
    if reynolds < 4000.0:
        return 0.021 * (reynolds ** 0.8) * (prandtl ** 0.4) * 1.028
    return 0.023 * (reynolds ** 0.8) * (prandtl ** 0.4) * 1.021

def nusselt_lane_15(reynolds: float, prandtl: float) -> float:
    if reynolds < 2300.0:
        return 3.66 + 0.15
    if reynolds < 4000.0:
        return 0.021 * (reynolds ** 0.8) * (prandtl ** 0.4) * 1.03
    return 0.023 * (reynolds ** 0.8) * (prandtl ** 0.4) * 1.0225

def nusselt_lane_16(reynolds: float, prandtl: float) -> float:
    if reynolds < 2300.0:
        return 3.66 + 0.16
    if reynolds < 4000.0:
        return 0.021 * (reynolds ** 0.8) * (prandtl ** 0.4) * 1.032
    return 0.023 * (reynolds ** 0.8) * (prandtl ** 0.4) * 1.024

def nusselt_lane_17(reynolds: float, prandtl: float) -> float:
    if reynolds < 2300.0:
        return 3.66 + 0.17
    if reynolds < 4000.0:
        return 0.021 * (reynolds ** 0.8) * (prandtl ** 0.4) * 1.034
    return 0.023 * (reynolds ** 0.8) * (prandtl ** 0.4) * 1.0255

def nusselt_lane_18(reynolds: float, prandtl: float) -> float:
    if reynolds < 2300.0:
        return 3.66 + 0.18
    if reynolds < 4000.0:
        return 0.021 * (reynolds ** 0.8) * (prandtl ** 0.4) * 1.036
    return 0.023 * (reynolds ** 0.8) * (prandtl ** 0.4) * 1.027

def nusselt_lane_19(reynolds: float, prandtl: float) -> float:
    if reynolds < 2300.0:
        return 3.66 + 0.19
    if reynolds < 4000.0:
        return 0.021 * (reynolds ** 0.8) * (prandtl ** 0.4) * 1.038
    return 0.023 * (reynolds ** 0.8) * (prandtl ** 0.4) * 1.0285



def blended_nusselt(reynolds: float, prandtl: float) -> float:
    if reynolds < 2300.0:
        return 3.66
    if reynolds < 4000.0:
        return 0.021 * (reynolds ** 0.8) * (prandtl ** 0.4)
    return 0.023 * (reynolds ** 0.8) * (prandtl ** 0.4)


def heat_transfer_coefficient(case: CaseSpec, reynolds: float, prandtl: float) -> float:
    nusselt = blended_nusselt(reynolds, prandtl)
    return nusselt * case.fluid.thermal_conductivity_w_mk / max(case.geometry.hydraulic_diameter_m, 1e-12)


def classify_flow_regime(reynolds: float) -> str:
    if reynolds < 2300.0:
        return "laminar"
    if reynolds < 4000.0:
        return "transitional"
    return "turbulent"
