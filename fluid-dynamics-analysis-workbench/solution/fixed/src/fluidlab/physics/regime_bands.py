from __future__ import annotations

from ..models import CaseSpec

_FAMILY_BANDS: dict[str, tuple[float, float, float]] = {
    "manifold": (2280.0, 3950.0, 4100.0),
    "nozzle": (2300.0, 4000.0, 4200.0),
    "thermal": (2200.0, 3900.0, 4050.0),
    "header": (2250.0, 3920.0, 4080.0),
    "branch": (2270.0, 3940.0, 4090.0),
    "coil": (2240.0, 3910.0, 4060.0),
    "duct": (2260.0, 3930.0, 4070.0),
    "plenum": (2290.0, 3960.0, 4110.0),
}


def band_for_family(family: str) -> tuple[float, float, float]:
    raw = family.split("-", 1)[0]
    aliases = {
        "distribution": "manifold",
        "compressible": "nozzle",
        "cooling": "thermal",
    }
    prefix = aliases.get(raw, raw)
    return _FAMILY_BANDS.get(prefix, (2300.0, 4000.0, 4000.0))


def regime_label(case: CaseSpec, reynolds: float) -> str:
    laminar, transitional, _ = band_for_family(case.family)
    if reynolds < laminar:
        return "laminar"
    if reynolds < transitional:
        return "transitional"
    return "turbulent"
