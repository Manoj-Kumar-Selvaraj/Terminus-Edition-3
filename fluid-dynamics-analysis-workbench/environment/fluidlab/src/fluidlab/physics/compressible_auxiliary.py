from __future__ import annotations

import math


def gas_density_with_compressibility(
    pressure_pa: float,
    temperature_k: float,
    gas_constant: float,
    gamma: float,
) -> float:
    ideal = pressure_pa / max(gas_constant * temperature_k, 1e-9)
    compressibility = 1.0 + (pressure_pa / max(101325.0, 1.0)) * 0.001 * (gamma - 1.0)
    return ideal / max(compressibility, 1e-9)


def isentropic_mach_from_velocity(velocity_m_s: float, sound_speed_m_s: float) -> float:
    return velocity_m_s / max(sound_speed_m_s, 1e-9)


def isentropic_pressure_ratio(mach: float, gamma: float) -> float:
    return (1.0 + 0.5 * (gamma - 1.0) * mach ** 2) ** (-gamma / (gamma - 1.0))


def choked_mass_flux(gamma: float, gas_constant: float, temperature_k: float, total_pressure_pa: float) -> float:
    exponent = (gamma + 1.0) / (2.0 * (gamma - 1.0))
    coeff = math.sqrt(gamma / gas_constant / temperature_k) * (2.0 / (gamma + 1.0)) ** exponent
    return total_pressure_pa * coeff


def fanno_pressure_drop(
    mach: float,
    gamma: float,
    total_pressure_pa: float,
    friction_factor: float,
    length_over_diameter: float,
) -> float:
    if mach <= 0.0:
        return 0.0
    numerator = 1.0 + 0.5 * (gamma - 1.0) * mach ** 2
    denominator = 1.0 + (gamma - 1.0) / 2.0 * mach ** 2
    fanno_term = (1.0 / max(gamma * mach ** 2, 1e-9)) + (gamma + 1.0) / (2.0 * gamma) * math.log(numerator / max(denominator, 1e-9))
    return total_pressure_pa * friction_factor * length_over_diameter * fanno_term * 0.01
