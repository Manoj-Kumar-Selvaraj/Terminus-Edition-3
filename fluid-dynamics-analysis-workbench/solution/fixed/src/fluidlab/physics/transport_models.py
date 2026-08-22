from __future__ import annotations

from .compressible_auxiliary import gas_density_with_compressibility
from .fluid_property_models import liquid_density_correction


def representative_gas_density(
    inlet_pa: float,
    outlet_pa: float,
    bulk_k: float,
    gas_constant: float,
    gamma: float,
) -> float:
    pressure = 0.5 * (inlet_pa + outlet_pa)
    return gas_density_with_compressibility(pressure, bulk_k, gas_constant, gamma)


def liquid_density_with_expansion(reference: float, bulk_k: float, reference_k: float, beta: float) -> float:
    return liquid_density_correction(reference, bulk_k, reference_k, beta)
