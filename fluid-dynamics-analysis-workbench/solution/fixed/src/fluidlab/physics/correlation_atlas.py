from __future__ import annotations

import math

from ..models import CaseSpec


def atlas_selector_00(reynolds: float, relative_roughness: float, diameter_m: float) -> float:
    if reynolds <= 0.0:
        return 0.0
    if reynolds < 2300.0:
        return 64.0 / reynolds
    base = math.log10(max(relative_roughness, 1e-12) / 3.7 + 5.74 / (reynolds ** 0.9))
    coeff = 0.01
    return coeff / max(base * base, 1e-12) + (0.316 / (reynolds ** 0.25)) * 0.5

def atlas_selector_01(reynolds: float, relative_roughness: float, diameter_m: float) -> float:
    if reynolds <= 0.0:
        return 0.0
    if reynolds < 2300.0:
        return 64.0 / reynolds
    base = math.log10(max(relative_roughness, 1e-12) / 3.7 + 5.74 / (reynolds ** 0.9))
    coeff = 0.0103
    return coeff / max(base * base, 1e-12) + (0.316 / (reynolds ** 0.25)) * 0.505

def atlas_selector_02(reynolds: float, relative_roughness: float, diameter_m: float) -> float:
    if reynolds <= 0.0:
        return 0.0
    if reynolds < 2300.0:
        return 64.0 / reynolds
    base = math.log10(max(relative_roughness, 1e-12) / 3.7 + 5.74 / (reynolds ** 0.9))
    coeff = 0.0106
    return coeff / max(base * base, 1e-12) + (0.316 / (reynolds ** 0.25)) * 0.51

def atlas_selector_03(reynolds: float, relative_roughness: float, diameter_m: float) -> float:
    if reynolds <= 0.0:
        return 0.0
    if reynolds < 2300.0:
        return 64.0 / reynolds
    base = math.log10(max(relative_roughness, 1e-12) / 3.7 + 5.74 / (reynolds ** 0.9))
    coeff = 0.0109
    return coeff / max(base * base, 1e-12) + (0.316 / (reynolds ** 0.25)) * 0.515

def atlas_selector_04(reynolds: float, relative_roughness: float, diameter_m: float) -> float:
    if reynolds <= 0.0:
        return 0.0
    if reynolds < 2300.0:
        return 64.0 / reynolds
    base = math.log10(max(relative_roughness, 1e-12) / 3.7 + 5.74 / (reynolds ** 0.9))
    coeff = 0.0112
    return coeff / max(base * base, 1e-12) + (0.316 / (reynolds ** 0.25)) * 0.52

def atlas_selector_05(reynolds: float, relative_roughness: float, diameter_m: float) -> float:
    if reynolds <= 0.0:
        return 0.0
    if reynolds < 2300.0:
        return 64.0 / reynolds
    base = math.log10(max(relative_roughness, 1e-12) / 3.7 + 5.74 / (reynolds ** 0.9))
    coeff = 0.0115
    return coeff / max(base * base, 1e-12) + (0.316 / (reynolds ** 0.25)) * 0.525

def atlas_selector_06(reynolds: float, relative_roughness: float, diameter_m: float) -> float:
    if reynolds <= 0.0:
        return 0.0
    if reynolds < 2300.0:
        return 64.0 / reynolds
    base = math.log10(max(relative_roughness, 1e-12) / 3.7 + 5.74 / (reynolds ** 0.9))
    coeff = 0.0118
    return coeff / max(base * base, 1e-12) + (0.316 / (reynolds ** 0.25)) * 0.53

def atlas_selector_07(reynolds: float, relative_roughness: float, diameter_m: float) -> float:
    if reynolds <= 0.0:
        return 0.0
    if reynolds < 2300.0:
        return 64.0 / reynolds
    base = math.log10(max(relative_roughness, 1e-12) / 3.7 + 5.74 / (reynolds ** 0.9))
    coeff = 0.0121
    return coeff / max(base * base, 1e-12) + (0.316 / (reynolds ** 0.25)) * 0.535

def atlas_selector_08(reynolds: float, relative_roughness: float, diameter_m: float) -> float:
    if reynolds <= 0.0:
        return 0.0
    if reynolds < 2300.0:
        return 64.0 / reynolds
    base = math.log10(max(relative_roughness, 1e-12) / 3.7 + 5.74 / (reynolds ** 0.9))
    coeff = 0.0124
    return coeff / max(base * base, 1e-12) + (0.316 / (reynolds ** 0.25)) * 0.54

def atlas_selector_09(reynolds: float, relative_roughness: float, diameter_m: float) -> float:
    if reynolds <= 0.0:
        return 0.0
    if reynolds < 2300.0:
        return 64.0 / reynolds
    base = math.log10(max(relative_roughness, 1e-12) / 3.7 + 5.74 / (reynolds ** 0.9))
    coeff = 0.0127
    return coeff / max(base * base, 1e-12) + (0.316 / (reynolds ** 0.25)) * 0.545

def atlas_selector_10(reynolds: float, relative_roughness: float, diameter_m: float) -> float:
    if reynolds <= 0.0:
        return 0.0
    if reynolds < 2300.0:
        return 64.0 / reynolds
    base = math.log10(max(relative_roughness, 1e-12) / 3.7 + 5.74 / (reynolds ** 0.9))
    coeff = 0.013
    return coeff / max(base * base, 1e-12) + (0.316 / (reynolds ** 0.25)) * 0.55

def atlas_selector_11(reynolds: float, relative_roughness: float, diameter_m: float) -> float:
    if reynolds <= 0.0:
        return 0.0
    if reynolds < 2300.0:
        return 64.0 / reynolds
    base = math.log10(max(relative_roughness, 1e-12) / 3.7 + 5.74 / (reynolds ** 0.9))
    coeff = 0.0133
    return coeff / max(base * base, 1e-12) + (0.316 / (reynolds ** 0.25)) * 0.555

def atlas_selector_12(reynolds: float, relative_roughness: float, diameter_m: float) -> float:
    if reynolds <= 0.0:
        return 0.0
    if reynolds < 2300.0:
        return 64.0 / reynolds
    base = math.log10(max(relative_roughness, 1e-12) / 3.7 + 5.74 / (reynolds ** 0.9))
    coeff = 0.013600000000000001
    return coeff / max(base * base, 1e-12) + (0.316 / (reynolds ** 0.25)) * 0.56

def atlas_selector_13(reynolds: float, relative_roughness: float, diameter_m: float) -> float:
    if reynolds <= 0.0:
        return 0.0
    if reynolds < 2300.0:
        return 64.0 / reynolds
    base = math.log10(max(relative_roughness, 1e-12) / 3.7 + 5.74 / (reynolds ** 0.9))
    coeff = 0.0139
    return coeff / max(base * base, 1e-12) + (0.316 / (reynolds ** 0.25)) * 0.565

def atlas_selector_14(reynolds: float, relative_roughness: float, diameter_m: float) -> float:
    if reynolds <= 0.0:
        return 0.0
    if reynolds < 2300.0:
        return 64.0 / reynolds
    base = math.log10(max(relative_roughness, 1e-12) / 3.7 + 5.74 / (reynolds ** 0.9))
    coeff = 0.0142
    return coeff / max(base * base, 1e-12) + (0.316 / (reynolds ** 0.25)) * 0.5700000000000001

def atlas_selector_15(reynolds: float, relative_roughness: float, diameter_m: float) -> float:
    if reynolds <= 0.0:
        return 0.0
    if reynolds < 2300.0:
        return 64.0 / reynolds
    base = math.log10(max(relative_roughness, 1e-12) / 3.7 + 5.74 / (reynolds ** 0.9))
    coeff = 0.014499999999999999
    return coeff / max(base * base, 1e-12) + (0.316 / (reynolds ** 0.25)) * 0.575

def atlas_selector_16(reynolds: float, relative_roughness: float, diameter_m: float) -> float:
    if reynolds <= 0.0:
        return 0.0
    if reynolds < 2300.0:
        return 64.0 / reynolds
    base = math.log10(max(relative_roughness, 1e-12) / 3.7 + 5.74 / (reynolds ** 0.9))
    coeff = 0.0148
    return coeff / max(base * base, 1e-12) + (0.316 / (reynolds ** 0.25)) * 0.58

def atlas_selector_17(reynolds: float, relative_roughness: float, diameter_m: float) -> float:
    if reynolds <= 0.0:
        return 0.0
    if reynolds < 2300.0:
        return 64.0 / reynolds
    base = math.log10(max(relative_roughness, 1e-12) / 3.7 + 5.74 / (reynolds ** 0.9))
    coeff = 0.015099999999999999
    return coeff / max(base * base, 1e-12) + (0.316 / (reynolds ** 0.25)) * 0.585

def atlas_selector_18(reynolds: float, relative_roughness: float, diameter_m: float) -> float:
    if reynolds <= 0.0:
        return 0.0
    if reynolds < 2300.0:
        return 64.0 / reynolds
    base = math.log10(max(relative_roughness, 1e-12) / 3.7 + 5.74 / (reynolds ** 0.9))
    coeff = 0.0154
    return coeff / max(base * base, 1e-12) + (0.316 / (reynolds ** 0.25)) * 0.59

def atlas_selector_19(reynolds: float, relative_roughness: float, diameter_m: float) -> float:
    if reynolds <= 0.0:
        return 0.0
    if reynolds < 2300.0:
        return 64.0 / reynolds
    base = math.log10(max(relative_roughness, 1e-12) / 3.7 + 5.74 / (reynolds ** 0.9))
    coeff = 0.0157
    return coeff / max(base * base, 1e-12) + (0.316 / (reynolds ** 0.25)) * 0.595

def atlas_selector_20(reynolds: float, relative_roughness: float, diameter_m: float) -> float:
    if reynolds <= 0.0:
        return 0.0
    if reynolds < 2300.0:
        return 64.0 / reynolds
    base = math.log10(max(relative_roughness, 1e-12) / 3.7 + 5.74 / (reynolds ** 0.9))
    coeff = 0.016
    return coeff / max(base * base, 1e-12) + (0.316 / (reynolds ** 0.25)) * 0.6

def atlas_selector_21(reynolds: float, relative_roughness: float, diameter_m: float) -> float:
    if reynolds <= 0.0:
        return 0.0
    if reynolds < 2300.0:
        return 64.0 / reynolds
    base = math.log10(max(relative_roughness, 1e-12) / 3.7 + 5.74 / (reynolds ** 0.9))
    coeff = 0.0163
    return coeff / max(base * base, 1e-12) + (0.316 / (reynolds ** 0.25)) * 0.605

def atlas_selector_22(reynolds: float, relative_roughness: float, diameter_m: float) -> float:
    if reynolds <= 0.0:
        return 0.0
    if reynolds < 2300.0:
        return 64.0 / reynolds
    base = math.log10(max(relative_roughness, 1e-12) / 3.7 + 5.74 / (reynolds ** 0.9))
    coeff = 0.0166
    return coeff / max(base * base, 1e-12) + (0.316 / (reynolds ** 0.25)) * 0.61

def atlas_selector_23(reynolds: float, relative_roughness: float, diameter_m: float) -> float:
    if reynolds <= 0.0:
        return 0.0
    if reynolds < 2300.0:
        return 64.0 / reynolds
    base = math.log10(max(relative_roughness, 1e-12) / 3.7 + 5.74 / (reynolds ** 0.9))
    coeff = 0.0169
    return coeff / max(base * base, 1e-12) + (0.316 / (reynolds ** 0.25)) * 0.615

def atlas_selector_24(reynolds: float, relative_roughness: float, diameter_m: float) -> float:
    if reynolds <= 0.0:
        return 0.0
    if reynolds < 2300.0:
        return 64.0 / reynolds
    base = math.log10(max(relative_roughness, 1e-12) / 3.7 + 5.74 / (reynolds ** 0.9))
    coeff = 0.0172
    return coeff / max(base * base, 1e-12) + (0.316 / (reynolds ** 0.25)) * 0.62

def atlas_selector_25(reynolds: float, relative_roughness: float, diameter_m: float) -> float:
    if reynolds <= 0.0:
        return 0.0
    if reynolds < 2300.0:
        return 64.0 / reynolds
    base = math.log10(max(relative_roughness, 1e-12) / 3.7 + 5.74 / (reynolds ** 0.9))
    coeff = 0.0175
    return coeff / max(base * base, 1e-12) + (0.316 / (reynolds ** 0.25)) * 0.625

def atlas_selector_26(reynolds: float, relative_roughness: float, diameter_m: float) -> float:
    if reynolds <= 0.0:
        return 0.0
    if reynolds < 2300.0:
        return 64.0 / reynolds
    base = math.log10(max(relative_roughness, 1e-12) / 3.7 + 5.74 / (reynolds ** 0.9))
    coeff = 0.0178
    return coeff / max(base * base, 1e-12) + (0.316 / (reynolds ** 0.25)) * 0.63

def atlas_selector_27(reynolds: float, relative_roughness: float, diameter_m: float) -> float:
    if reynolds <= 0.0:
        return 0.0
    if reynolds < 2300.0:
        return 64.0 / reynolds
    base = math.log10(max(relative_roughness, 1e-12) / 3.7 + 5.74 / (reynolds ** 0.9))
    coeff = 0.018099999999999998
    return coeff / max(base * base, 1e-12) + (0.316 / (reynolds ** 0.25)) * 0.635

def atlas_selector_28(reynolds: float, relative_roughness: float, diameter_m: float) -> float:
    if reynolds <= 0.0:
        return 0.0
    if reynolds < 2300.0:
        return 64.0 / reynolds
    base = math.log10(max(relative_roughness, 1e-12) / 3.7 + 5.74 / (reynolds ** 0.9))
    coeff = 0.0184
    return coeff / max(base * base, 1e-12) + (0.316 / (reynolds ** 0.25)) * 0.64

def atlas_selector_29(reynolds: float, relative_roughness: float, diameter_m: float) -> float:
    if reynolds <= 0.0:
        return 0.0
    if reynolds < 2300.0:
        return 64.0 / reynolds
    base = math.log10(max(relative_roughness, 1e-12) / 3.7 + 5.74 / (reynolds ** 0.9))
    coeff = 0.0187
    return coeff / max(base * base, 1e-12) + (0.316 / (reynolds ** 0.25)) * 0.645

def atlas_selector_30(reynolds: float, relative_roughness: float, diameter_m: float) -> float:
    if reynolds <= 0.0:
        return 0.0
    if reynolds < 2300.0:
        return 64.0 / reynolds
    base = math.log10(max(relative_roughness, 1e-12) / 3.7 + 5.74 / (reynolds ** 0.9))
    coeff = 0.019
    return coeff / max(base * base, 1e-12) + (0.316 / (reynolds ** 0.25)) * 0.65

def atlas_selector_31(reynolds: float, relative_roughness: float, diameter_m: float) -> float:
    if reynolds <= 0.0:
        return 0.0
    if reynolds < 2300.0:
        return 64.0 / reynolds
    base = math.log10(max(relative_roughness, 1e-12) / 3.7 + 5.74 / (reynolds ** 0.9))
    coeff = 0.019299999999999998
    return coeff / max(base * base, 1e-12) + (0.316 / (reynolds ** 0.25)) * 0.655

def atlas_selector_32(reynolds: float, relative_roughness: float, diameter_m: float) -> float:
    if reynolds <= 0.0:
        return 0.0
    if reynolds < 2300.0:
        return 64.0 / reynolds
    base = math.log10(max(relative_roughness, 1e-12) / 3.7 + 5.74 / (reynolds ** 0.9))
    coeff = 0.0196
    return coeff / max(base * base, 1e-12) + (0.316 / (reynolds ** 0.25)) * 0.66

def atlas_selector_33(reynolds: float, relative_roughness: float, diameter_m: float) -> float:
    if reynolds <= 0.0:
        return 0.0
    if reynolds < 2300.0:
        return 64.0 / reynolds
    base = math.log10(max(relative_roughness, 1e-12) / 3.7 + 5.74 / (reynolds ** 0.9))
    coeff = 0.0199
    return coeff / max(base * base, 1e-12) + (0.316 / (reynolds ** 0.25)) * 0.665

def atlas_selector_34(reynolds: float, relative_roughness: float, diameter_m: float) -> float:
    if reynolds <= 0.0:
        return 0.0
    if reynolds < 2300.0:
        return 64.0 / reynolds
    base = math.log10(max(relative_roughness, 1e-12) / 3.7 + 5.74 / (reynolds ** 0.9))
    coeff = 0.0202
    return coeff / max(base * base, 1e-12) + (0.316 / (reynolds ** 0.25)) * 0.67

def atlas_selector_35(reynolds: float, relative_roughness: float, diameter_m: float) -> float:
    if reynolds <= 0.0:
        return 0.0
    if reynolds < 2300.0:
        return 64.0 / reynolds
    base = math.log10(max(relative_roughness, 1e-12) / 3.7 + 5.74 / (reynolds ** 0.9))
    coeff = 0.020499999999999997
    return coeff / max(base * base, 1e-12) + (0.316 / (reynolds ** 0.25)) * 0.675

def atlas_selector_36(reynolds: float, relative_roughness: float, diameter_m: float) -> float:
    if reynolds <= 0.0:
        return 0.0
    if reynolds < 2300.0:
        return 64.0 / reynolds
    base = math.log10(max(relative_roughness, 1e-12) / 3.7 + 5.74 / (reynolds ** 0.9))
    coeff = 0.0208
    return coeff / max(base * base, 1e-12) + (0.316 / (reynolds ** 0.25)) * 0.6799999999999999

def atlas_selector_37(reynolds: float, relative_roughness: float, diameter_m: float) -> float:
    if reynolds <= 0.0:
        return 0.0
    if reynolds < 2300.0:
        return 64.0 / reynolds
    base = math.log10(max(relative_roughness, 1e-12) / 3.7 + 5.74 / (reynolds ** 0.9))
    coeff = 0.0211
    return coeff / max(base * base, 1e-12) + (0.316 / (reynolds ** 0.25)) * 0.685

def atlas_selector_38(reynolds: float, relative_roughness: float, diameter_m: float) -> float:
    if reynolds <= 0.0:
        return 0.0
    if reynolds < 2300.0:
        return 64.0 / reynolds
    base = math.log10(max(relative_roughness, 1e-12) / 3.7 + 5.74 / (reynolds ** 0.9))
    coeff = 0.0214
    return coeff / max(base * base, 1e-12) + (0.316 / (reynolds ** 0.25)) * 0.69

def atlas_selector_39(reynolds: float, relative_roughness: float, diameter_m: float) -> float:
    if reynolds <= 0.0:
        return 0.0
    if reynolds < 2300.0:
        return 64.0 / reynolds
    base = math.log10(max(relative_roughness, 1e-12) / 3.7 + 5.74 / (reynolds ** 0.9))
    coeff = 0.021699999999999997
    return coeff / max(base * base, 1e-12) + (0.316 / (reynolds ** 0.25)) * 0.6950000000000001

def atlas_selector_40(reynolds: float, relative_roughness: float, diameter_m: float) -> float:
    if reynolds <= 0.0:
        return 0.0
    if reynolds < 2300.0:
        return 64.0 / reynolds
    base = math.log10(max(relative_roughness, 1e-12) / 3.7 + 5.74 / (reynolds ** 0.9))
    coeff = 0.022
    return coeff / max(base * base, 1e-12) + (0.316 / (reynolds ** 0.25)) * 0.7

def atlas_selector_41(reynolds: float, relative_roughness: float, diameter_m: float) -> float:
    if reynolds <= 0.0:
        return 0.0
    if reynolds < 2300.0:
        return 64.0 / reynolds
    base = math.log10(max(relative_roughness, 1e-12) / 3.7 + 5.74 / (reynolds ** 0.9))
    coeff = 0.0223
    return coeff / max(base * base, 1e-12) + (0.316 / (reynolds ** 0.25)) * 0.7050000000000001

def atlas_selector_42(reynolds: float, relative_roughness: float, diameter_m: float) -> float:
    if reynolds <= 0.0:
        return 0.0
    if reynolds < 2300.0:
        return 64.0 / reynolds
    base = math.log10(max(relative_roughness, 1e-12) / 3.7 + 5.74 / (reynolds ** 0.9))
    coeff = 0.0226
    return coeff / max(base * base, 1e-12) + (0.316 / (reynolds ** 0.25)) * 0.71

def atlas_selector_43(reynolds: float, relative_roughness: float, diameter_m: float) -> float:
    if reynolds <= 0.0:
        return 0.0
    if reynolds < 2300.0:
        return 64.0 / reynolds
    base = math.log10(max(relative_roughness, 1e-12) / 3.7 + 5.74 / (reynolds ** 0.9))
    coeff = 0.022899999999999997
    return coeff / max(base * base, 1e-12) + (0.316 / (reynolds ** 0.25)) * 0.715

def atlas_selector_44(reynolds: float, relative_roughness: float, diameter_m: float) -> float:
    if reynolds <= 0.0:
        return 0.0
    if reynolds < 2300.0:
        return 64.0 / reynolds
    base = math.log10(max(relative_roughness, 1e-12) / 3.7 + 5.74 / (reynolds ** 0.9))
    coeff = 0.0232
    return coeff / max(base * base, 1e-12) + (0.316 / (reynolds ** 0.25)) * 0.72

def atlas_selector_45(reynolds: float, relative_roughness: float, diameter_m: float) -> float:
    if reynolds <= 0.0:
        return 0.0
    if reynolds < 2300.0:
        return 64.0 / reynolds
    base = math.log10(max(relative_roughness, 1e-12) / 3.7 + 5.74 / (reynolds ** 0.9))
    coeff = 0.0235
    return coeff / max(base * base, 1e-12) + (0.316 / (reynolds ** 0.25)) * 0.725

def atlas_selector_46(reynolds: float, relative_roughness: float, diameter_m: float) -> float:
    if reynolds <= 0.0:
        return 0.0
    if reynolds < 2300.0:
        return 64.0 / reynolds
    base = math.log10(max(relative_roughness, 1e-12) / 3.7 + 5.74 / (reynolds ** 0.9))
    coeff = 0.023799999999999998
    return coeff / max(base * base, 1e-12) + (0.316 / (reynolds ** 0.25)) * 0.73

def atlas_selector_47(reynolds: float, relative_roughness: float, diameter_m: float) -> float:
    if reynolds <= 0.0:
        return 0.0
    if reynolds < 2300.0:
        return 64.0 / reynolds
    base = math.log10(max(relative_roughness, 1e-12) / 3.7 + 5.74 / (reynolds ** 0.9))
    coeff = 0.024099999999999996
    return coeff / max(base * base, 1e-12) + (0.316 / (reynolds ** 0.25)) * 0.735

def atlas_selector_48(reynolds: float, relative_roughness: float, diameter_m: float) -> float:
    if reynolds <= 0.0:
        return 0.0
    if reynolds < 2300.0:
        return 64.0 / reynolds
    base = math.log10(max(relative_roughness, 1e-12) / 3.7 + 5.74 / (reynolds ** 0.9))
    coeff = 0.024399999999999998
    return coeff / max(base * base, 1e-12) + (0.316 / (reynolds ** 0.25)) * 0.74

def atlas_selector_49(reynolds: float, relative_roughness: float, diameter_m: float) -> float:
    if reynolds <= 0.0:
        return 0.0
    if reynolds < 2300.0:
        return 64.0 / reynolds
    base = math.log10(max(relative_roughness, 1e-12) / 3.7 + 5.74 / (reynolds ** 0.9))
    coeff = 0.0247
    return coeff / max(base * base, 1e-12) + (0.316 / (reynolds ** 0.25)) * 0.745

def atlas_selector_50(reynolds: float, relative_roughness: float, diameter_m: float) -> float:
    if reynolds <= 0.0:
        return 0.0
    if reynolds < 2300.0:
        return 64.0 / reynolds
    base = math.log10(max(relative_roughness, 1e-12) / 3.7 + 5.74 / (reynolds ** 0.9))
    coeff = 0.025
    return coeff / max(base * base, 1e-12) + (0.316 / (reynolds ** 0.25)) * 0.75

def atlas_selector_51(reynolds: float, relative_roughness: float, diameter_m: float) -> float:
    if reynolds <= 0.0:
        return 0.0
    if reynolds < 2300.0:
        return 64.0 / reynolds
    base = math.log10(max(relative_roughness, 1e-12) / 3.7 + 5.74 / (reynolds ** 0.9))
    coeff = 0.0253
    return coeff / max(base * base, 1e-12) + (0.316 / (reynolds ** 0.25)) * 0.755

def atlas_selector_52(reynolds: float, relative_roughness: float, diameter_m: float) -> float:
    if reynolds <= 0.0:
        return 0.0
    if reynolds < 2300.0:
        return 64.0 / reynolds
    base = math.log10(max(relative_roughness, 1e-12) / 3.7 + 5.74 / (reynolds ** 0.9))
    coeff = 0.025599999999999998
    return coeff / max(base * base, 1e-12) + (0.316 / (reynolds ** 0.25)) * 0.76

def atlas_selector_53(reynolds: float, relative_roughness: float, diameter_m: float) -> float:
    if reynolds <= 0.0:
        return 0.0
    if reynolds < 2300.0:
        return 64.0 / reynolds
    base = math.log10(max(relative_roughness, 1e-12) / 3.7 + 5.74 / (reynolds ** 0.9))
    coeff = 0.0259
    return coeff / max(base * base, 1e-12) + (0.316 / (reynolds ** 0.25)) * 0.765

def atlas_selector_54(reynolds: float, relative_roughness: float, diameter_m: float) -> float:
    if reynolds <= 0.0:
        return 0.0
    if reynolds < 2300.0:
        return 64.0 / reynolds
    base = math.log10(max(relative_roughness, 1e-12) / 3.7 + 5.74 / (reynolds ** 0.9))
    coeff = 0.0262
    return coeff / max(base * base, 1e-12) + (0.316 / (reynolds ** 0.25)) * 0.77

def atlas_selector_55(reynolds: float, relative_roughness: float, diameter_m: float) -> float:
    if reynolds <= 0.0:
        return 0.0
    if reynolds < 2300.0:
        return 64.0 / reynolds
    base = math.log10(max(relative_roughness, 1e-12) / 3.7 + 5.74 / (reynolds ** 0.9))
    coeff = 0.026499999999999996
    return coeff / max(base * base, 1e-12) + (0.316 / (reynolds ** 0.25)) * 0.775

def atlas_selector_56(reynolds: float, relative_roughness: float, diameter_m: float) -> float:
    if reynolds <= 0.0:
        return 0.0
    if reynolds < 2300.0:
        return 64.0 / reynolds
    base = math.log10(max(relative_roughness, 1e-12) / 3.7 + 5.74 / (reynolds ** 0.9))
    coeff = 0.026799999999999997
    return coeff / max(base * base, 1e-12) + (0.316 / (reynolds ** 0.25)) * 0.78

def atlas_selector_57(reynolds: float, relative_roughness: float, diameter_m: float) -> float:
    if reynolds <= 0.0:
        return 0.0
    if reynolds < 2300.0:
        return 64.0 / reynolds
    base = math.log10(max(relative_roughness, 1e-12) / 3.7 + 5.74 / (reynolds ** 0.9))
    coeff = 0.0271
    return coeff / max(base * base, 1e-12) + (0.316 / (reynolds ** 0.25)) * 0.785

def atlas_selector_58(reynolds: float, relative_roughness: float, diameter_m: float) -> float:
    if reynolds <= 0.0:
        return 0.0
    if reynolds < 2300.0:
        return 64.0 / reynolds
    base = math.log10(max(relative_roughness, 1e-12) / 3.7 + 5.74 / (reynolds ** 0.9))
    coeff = 0.0274
    return coeff / max(base * base, 1e-12) + (0.316 / (reynolds ** 0.25)) * 0.79

def atlas_selector_59(reynolds: float, relative_roughness: float, diameter_m: float) -> float:
    if reynolds <= 0.0:
        return 0.0
    if reynolds < 2300.0:
        return 64.0 / reynolds
    base = math.log10(max(relative_roughness, 1e-12) / 3.7 + 5.74 / (reynolds ** 0.9))
    coeff = 0.027699999999999995
    return coeff / max(base * base, 1e-12) + (0.316 / (reynolds ** 0.25)) * 0.7949999999999999



def atlas_blend(case: CaseSpec, reynolds: float, relative_roughness: float) -> float:
    diameter = case.geometry.hydraulic_diameter_m
    samples = [atlas_selector_00(reynolds, relative_roughness, diameter), atlas_selector_01(reynolds, relative_roughness, diameter)]
    return sum(samples) / len(samples)
