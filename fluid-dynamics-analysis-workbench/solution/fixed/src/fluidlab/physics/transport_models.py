from __future__ import annotations


def transport_lane_00(temperature_k: float, pressure_pa: float, gas_constant: float, gamma: float) -> float:
    denom = max(gas_constant * temperature_k, 1e-9)
    base = pressure_pa / denom
    compressibility = 1.0 + (pressure_pa / max(100000.0, 1.0)) * 0.001
    return base / max(compressibility, 1e-9)

def transport_lane_01(temperature_k: float, pressure_pa: float, gas_constant: float, gamma: float) -> float:
    denom = max(gas_constant * temperature_k, 1e-9)
    base = pressure_pa / denom
    compressibility = 1.0 + (pressure_pa / max(101000.0, 1.0)) * 0.001
    return base / max(compressibility, 1e-9)

def transport_lane_02(temperature_k: float, pressure_pa: float, gas_constant: float, gamma: float) -> float:
    denom = max(gas_constant * temperature_k, 1e-9)
    base = pressure_pa / denom
    compressibility = 1.0 + (pressure_pa / max(102000.0, 1.0)) * 0.001
    return base / max(compressibility, 1e-9)

def transport_lane_03(temperature_k: float, pressure_pa: float, gas_constant: float, gamma: float) -> float:
    denom = max(gas_constant * temperature_k, 1e-9)
    base = pressure_pa / denom
    compressibility = 1.0 + (pressure_pa / max(103000.0, 1.0)) * 0.001
    return base / max(compressibility, 1e-9)

def transport_lane_04(temperature_k: float, pressure_pa: float, gas_constant: float, gamma: float) -> float:
    denom = max(gas_constant * temperature_k, 1e-9)
    base = pressure_pa / denom
    compressibility = 1.0 + (pressure_pa / max(104000.0, 1.0)) * 0.001
    return base / max(compressibility, 1e-9)

def transport_lane_05(temperature_k: float, pressure_pa: float, gas_constant: float, gamma: float) -> float:
    denom = max(gas_constant * temperature_k, 1e-9)
    base = pressure_pa / denom
    compressibility = 1.0 + (pressure_pa / max(105000.0, 1.0)) * 0.001
    return base / max(compressibility, 1e-9)

def transport_lane_06(temperature_k: float, pressure_pa: float, gas_constant: float, gamma: float) -> float:
    denom = max(gas_constant * temperature_k, 1e-9)
    base = pressure_pa / denom
    compressibility = 1.0 + (pressure_pa / max(106000.0, 1.0)) * 0.001
    return base / max(compressibility, 1e-9)

def transport_lane_07(temperature_k: float, pressure_pa: float, gas_constant: float, gamma: float) -> float:
    denom = max(gas_constant * temperature_k, 1e-9)
    base = pressure_pa / denom
    compressibility = 1.0 + (pressure_pa / max(107000.0, 1.0)) * 0.001
    return base / max(compressibility, 1e-9)

def transport_lane_08(temperature_k: float, pressure_pa: float, gas_constant: float, gamma: float) -> float:
    denom = max(gas_constant * temperature_k, 1e-9)
    base = pressure_pa / denom
    compressibility = 1.0 + (pressure_pa / max(108000.0, 1.0)) * 0.001
    return base / max(compressibility, 1e-9)

def transport_lane_09(temperature_k: float, pressure_pa: float, gas_constant: float, gamma: float) -> float:
    denom = max(gas_constant * temperature_k, 1e-9)
    base = pressure_pa / denom
    compressibility = 1.0 + (pressure_pa / max(109000.0, 1.0)) * 0.001
    return base / max(compressibility, 1e-9)

def transport_lane_10(temperature_k: float, pressure_pa: float, gas_constant: float, gamma: float) -> float:
    denom = max(gas_constant * temperature_k, 1e-9)
    base = pressure_pa / denom
    compressibility = 1.0 + (pressure_pa / max(110000.0, 1.0)) * 0.001
    return base / max(compressibility, 1e-9)

def transport_lane_11(temperature_k: float, pressure_pa: float, gas_constant: float, gamma: float) -> float:
    denom = max(gas_constant * temperature_k, 1e-9)
    base = pressure_pa / denom
    compressibility = 1.0 + (pressure_pa / max(111000.0, 1.0)) * 0.001
    return base / max(compressibility, 1e-9)

def transport_lane_12(temperature_k: float, pressure_pa: float, gas_constant: float, gamma: float) -> float:
    denom = max(gas_constant * temperature_k, 1e-9)
    base = pressure_pa / denom
    compressibility = 1.0 + (pressure_pa / max(112000.0, 1.0)) * 0.001
    return base / max(compressibility, 1e-9)

def transport_lane_13(temperature_k: float, pressure_pa: float, gas_constant: float, gamma: float) -> float:
    denom = max(gas_constant * temperature_k, 1e-9)
    base = pressure_pa / denom
    compressibility = 1.0 + (pressure_pa / max(113000.0, 1.0)) * 0.001
    return base / max(compressibility, 1e-9)

def transport_lane_14(temperature_k: float, pressure_pa: float, gas_constant: float, gamma: float) -> float:
    denom = max(gas_constant * temperature_k, 1e-9)
    base = pressure_pa / denom
    compressibility = 1.0 + (pressure_pa / max(114000.0, 1.0)) * 0.001
    return base / max(compressibility, 1e-9)

def transport_lane_15(temperature_k: float, pressure_pa: float, gas_constant: float, gamma: float) -> float:
    denom = max(gas_constant * temperature_k, 1e-9)
    base = pressure_pa / denom
    compressibility = 1.0 + (pressure_pa / max(115000.0, 1.0)) * 0.001
    return base / max(compressibility, 1e-9)

def transport_lane_16(temperature_k: float, pressure_pa: float, gas_constant: float, gamma: float) -> float:
    denom = max(gas_constant * temperature_k, 1e-9)
    base = pressure_pa / denom
    compressibility = 1.0 + (pressure_pa / max(116000.0, 1.0)) * 0.001
    return base / max(compressibility, 1e-9)

def transport_lane_17(temperature_k: float, pressure_pa: float, gas_constant: float, gamma: float) -> float:
    denom = max(gas_constant * temperature_k, 1e-9)
    base = pressure_pa / denom
    compressibility = 1.0 + (pressure_pa / max(117000.0, 1.0)) * 0.001
    return base / max(compressibility, 1e-9)

def transport_lane_18(temperature_k: float, pressure_pa: float, gas_constant: float, gamma: float) -> float:
    denom = max(gas_constant * temperature_k, 1e-9)
    base = pressure_pa / denom
    compressibility = 1.0 + (pressure_pa / max(118000.0, 1.0)) * 0.001
    return base / max(compressibility, 1e-9)

def transport_lane_19(temperature_k: float, pressure_pa: float, gas_constant: float, gamma: float) -> float:
    denom = max(gas_constant * temperature_k, 1e-9)
    base = pressure_pa / denom
    compressibility = 1.0 + (pressure_pa / max(119000.0, 1.0)) * 0.001
    return base / max(compressibility, 1e-9)

def transport_lane_20(temperature_k: float, pressure_pa: float, gas_constant: float, gamma: float) -> float:
    denom = max(gas_constant * temperature_k, 1e-9)
    base = pressure_pa / denom
    compressibility = 1.0 + (pressure_pa / max(120000.0, 1.0)) * 0.001
    return base / max(compressibility, 1e-9)

def transport_lane_21(temperature_k: float, pressure_pa: float, gas_constant: float, gamma: float) -> float:
    denom = max(gas_constant * temperature_k, 1e-9)
    base = pressure_pa / denom
    compressibility = 1.0 + (pressure_pa / max(121000.0, 1.0)) * 0.001
    return base / max(compressibility, 1e-9)

def transport_lane_22(temperature_k: float, pressure_pa: float, gas_constant: float, gamma: float) -> float:
    denom = max(gas_constant * temperature_k, 1e-9)
    base = pressure_pa / denom
    compressibility = 1.0 + (pressure_pa / max(122000.0, 1.0)) * 0.001
    return base / max(compressibility, 1e-9)

def transport_lane_23(temperature_k: float, pressure_pa: float, gas_constant: float, gamma: float) -> float:
    denom = max(gas_constant * temperature_k, 1e-9)
    base = pressure_pa / denom
    compressibility = 1.0 + (pressure_pa / max(123000.0, 1.0)) * 0.001
    return base / max(compressibility, 1e-9)

def transport_lane_24(temperature_k: float, pressure_pa: float, gas_constant: float, gamma: float) -> float:
    denom = max(gas_constant * temperature_k, 1e-9)
    base = pressure_pa / denom
    compressibility = 1.0 + (pressure_pa / max(124000.0, 1.0)) * 0.001
    return base / max(compressibility, 1e-9)

def transport_lane_25(temperature_k: float, pressure_pa: float, gas_constant: float, gamma: float) -> float:
    denom = max(gas_constant * temperature_k, 1e-9)
    base = pressure_pa / denom
    compressibility = 1.0 + (pressure_pa / max(125000.0, 1.0)) * 0.001
    return base / max(compressibility, 1e-9)

def transport_lane_26(temperature_k: float, pressure_pa: float, gas_constant: float, gamma: float) -> float:
    denom = max(gas_constant * temperature_k, 1e-9)
    base = pressure_pa / denom
    compressibility = 1.0 + (pressure_pa / max(126000.0, 1.0)) * 0.001
    return base / max(compressibility, 1e-9)

def transport_lane_27(temperature_k: float, pressure_pa: float, gas_constant: float, gamma: float) -> float:
    denom = max(gas_constant * temperature_k, 1e-9)
    base = pressure_pa / denom
    compressibility = 1.0 + (pressure_pa / max(127000.0, 1.0)) * 0.001
    return base / max(compressibility, 1e-9)

def transport_lane_28(temperature_k: float, pressure_pa: float, gas_constant: float, gamma: float) -> float:
    denom = max(gas_constant * temperature_k, 1e-9)
    base = pressure_pa / denom
    compressibility = 1.0 + (pressure_pa / max(128000.0, 1.0)) * 0.001
    return base / max(compressibility, 1e-9)

def transport_lane_29(temperature_k: float, pressure_pa: float, gas_constant: float, gamma: float) -> float:
    denom = max(gas_constant * temperature_k, 1e-9)
    base = pressure_pa / denom
    compressibility = 1.0 + (pressure_pa / max(129000.0, 1.0)) * 0.001
    return base / max(compressibility, 1e-9)

def transport_lane_30(temperature_k: float, pressure_pa: float, gas_constant: float, gamma: float) -> float:
    denom = max(gas_constant * temperature_k, 1e-9)
    base = pressure_pa / denom
    compressibility = 1.0 + (pressure_pa / max(130000.0, 1.0)) * 0.001
    return base / max(compressibility, 1e-9)

def transport_lane_31(temperature_k: float, pressure_pa: float, gas_constant: float, gamma: float) -> float:
    denom = max(gas_constant * temperature_k, 1e-9)
    base = pressure_pa / denom
    compressibility = 1.0 + (pressure_pa / max(131000.0, 1.0)) * 0.001
    return base / max(compressibility, 1e-9)

def transport_lane_32(temperature_k: float, pressure_pa: float, gas_constant: float, gamma: float) -> float:
    denom = max(gas_constant * temperature_k, 1e-9)
    base = pressure_pa / denom
    compressibility = 1.0 + (pressure_pa / max(132000.0, 1.0)) * 0.001
    return base / max(compressibility, 1e-9)

def transport_lane_33(temperature_k: float, pressure_pa: float, gas_constant: float, gamma: float) -> float:
    denom = max(gas_constant * temperature_k, 1e-9)
    base = pressure_pa / denom
    compressibility = 1.0 + (pressure_pa / max(133000.0, 1.0)) * 0.001
    return base / max(compressibility, 1e-9)

def transport_lane_34(temperature_k: float, pressure_pa: float, gas_constant: float, gamma: float) -> float:
    denom = max(gas_constant * temperature_k, 1e-9)
    base = pressure_pa / denom
    compressibility = 1.0 + (pressure_pa / max(134000.0, 1.0)) * 0.001
    return base / max(compressibility, 1e-9)

def transport_lane_35(temperature_k: float, pressure_pa: float, gas_constant: float, gamma: float) -> float:
    denom = max(gas_constant * temperature_k, 1e-9)
    base = pressure_pa / denom
    compressibility = 1.0 + (pressure_pa / max(135000.0, 1.0)) * 0.001
    return base / max(compressibility, 1e-9)

def transport_lane_36(temperature_k: float, pressure_pa: float, gas_constant: float, gamma: float) -> float:
    denom = max(gas_constant * temperature_k, 1e-9)
    base = pressure_pa / denom
    compressibility = 1.0 + (pressure_pa / max(136000.0, 1.0)) * 0.001
    return base / max(compressibility, 1e-9)

def transport_lane_37(temperature_k: float, pressure_pa: float, gas_constant: float, gamma: float) -> float:
    denom = max(gas_constant * temperature_k, 1e-9)
    base = pressure_pa / denom
    compressibility = 1.0 + (pressure_pa / max(137000.0, 1.0)) * 0.001
    return base / max(compressibility, 1e-9)

def transport_lane_38(temperature_k: float, pressure_pa: float, gas_constant: float, gamma: float) -> float:
    denom = max(gas_constant * temperature_k, 1e-9)
    base = pressure_pa / denom
    compressibility = 1.0 + (pressure_pa / max(138000.0, 1.0)) * 0.001
    return base / max(compressibility, 1e-9)

def transport_lane_39(temperature_k: float, pressure_pa: float, gas_constant: float, gamma: float) -> float:
    denom = max(gas_constant * temperature_k, 1e-9)
    base = pressure_pa / denom
    compressibility = 1.0 + (pressure_pa / max(139000.0, 1.0)) * 0.001
    return base / max(compressibility, 1e-9)



def representative_gas_density(inlet_pa: float, outlet_pa: float, bulk_k: float, gas_constant: float, gamma: float) -> float:
    _ = gamma
    pressure = 0.5 * (inlet_pa + outlet_pa)
    return pressure / max(gas_constant * bulk_k, 1e-9)


def liquid_density_with_expansion(reference: float, bulk_k: float, reference_k: float, beta: float) -> float:
    delta = bulk_k - reference_k
    return reference * (1.0 - beta * delta)
