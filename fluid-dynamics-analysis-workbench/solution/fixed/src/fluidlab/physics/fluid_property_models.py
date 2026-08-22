from __future__ import annotations

from ..models import FluidSpec


def sutherland_viscosity(reference_mu: float, reference_k: float, temperature_k: float, sutherland_k: float = 110.4) -> float:
    return reference_mu * ((temperature_k / reference_k) ** 1.5) * (reference_k + sutherland_k) / max(temperature_k + sutherland_k, 1e-9)


def liquid_density_correction(reference: float, bulk_k: float, reference_k: float, beta: float) -> float:
    delta = bulk_k - reference_k
    return reference * (1.0 - beta * delta)


def thermal_conductivity_linear(base: float, temperature_k: float, reference_k: float, slope: float) -> float:
    return max(1e-6, base + slope * (temperature_k - reference_k))


def cp_polynomial(base: float, temperature_k: float, reference_k: float, c1: float, c2: float) -> float:
    delta = temperature_k - reference_k
    return max(1.0, base + c1 * delta + c2 * delta * delta)


def effective_properties(fluid: FluidSpec, bulk_temperature_k: float) -> dict[str, float]:
    mu = sutherland_viscosity(fluid.dynamic_viscosity_pa_s, fluid.reference_temperature_k, bulk_temperature_k)
    cp = cp_polynomial(fluid.cp_j_kgk, bulk_temperature_k, fluid.reference_temperature_k, 0.05, 0.0001)
    k = thermal_conductivity_linear(fluid.thermal_conductivity_w_mk, bulk_temperature_k, fluid.reference_temperature_k, 0.0002)
    return {
        "dynamic_viscosity_pa_s": mu,
        "cp_j_kgk": cp,
        "thermal_conductivity_w_mk": k,
    }
