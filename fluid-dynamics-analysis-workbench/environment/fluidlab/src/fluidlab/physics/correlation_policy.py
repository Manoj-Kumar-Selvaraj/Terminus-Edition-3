from __future__ import annotations

import math

from ..models import CaseSpec

# family, index, laminar_boost, turbulent_scale, transitional_blend
_FRICTION_POLICY: tuple[tuple[str, int, float, float, float], ...] = (
    ("manifold", 0, 0.0200, 1.000, 0.50),
    ("manifold", 1, 0.0230, 1.015, 0.54),
    ("manifold", 2, 0.0260, 1.030, 0.58),
    ("manifold", 3, 0.0290, 1.045, 0.62),
    ("manifold", 4, 0.0320, 1.060, 0.66),
    ("manifold", 5, 0.0350, 1.075, 0.70),
    ("manifold", 6, 0.0380, 1.090, 0.74),
    ("manifold", 7, 0.0410, 1.105, 0.78),
    ("manifold", 8, 0.0440, 1.120, 0.82),
    ("manifold", 9, 0.0470, 1.135, 0.86),
    ("manifold", 10, 0.0500, 1.150, 0.90),
    ("manifold", 11, 0.0530, 1.165, 0.94),
    ("nozzle", 1, 0.0200, 1.000, 0.50),
    ("nozzle", 2, 0.0230, 1.015, 0.54),
    ("nozzle", 3, 0.0260, 1.030, 0.58),
    ("nozzle", 4, 0.0290, 1.045, 0.62),
    ("nozzle", 5, 0.0320, 1.060, 0.66),
    ("nozzle", 6, 0.0350, 1.075, 0.70),
    ("nozzle", 7, 0.0380, 1.090, 0.74),
    ("nozzle", 8, 0.0410, 1.105, 0.78),
    ("nozzle", 9, 0.0440, 1.120, 0.82),
    ("nozzle", 10, 0.0470, 1.135, 0.86),
    ("nozzle", 11, 0.0500, 1.150, 0.90),
    ("nozzle", 12, 0.0530, 1.165, 0.94),
    ("thermal", 2, 0.0200, 1.000, 0.50),
    ("thermal", 3, 0.0230, 1.015, 0.54),
    ("thermal", 4, 0.0260, 1.030, 0.58),
    ("thermal", 5, 0.0290, 1.045, 0.62),
    ("thermal", 6, 0.0320, 1.060, 0.66),
    ("thermal", 7, 0.0350, 1.075, 0.70),
    ("thermal", 8, 0.0380, 1.090, 0.74),
    ("thermal", 9, 0.0410, 1.105, 0.78),
    ("thermal", 10, 0.0440, 1.120, 0.82),
    ("thermal", 11, 0.0470, 1.135, 0.86),
    ("thermal", 12, 0.0500, 1.150, 0.90),
    ("thermal", 13, 0.0530, 1.165, 0.94),
    ("header", 3, 0.0200, 1.000, 0.50),
    ("header", 4, 0.0230, 1.015, 0.54),
    ("header", 5, 0.0260, 1.030, 0.58),
    ("header", 6, 0.0290, 1.045, 0.62),
    ("header", 7, 0.0320, 1.060, 0.66),
    ("header", 8, 0.0350, 1.075, 0.70),
    ("header", 9, 0.0380, 1.090, 0.74),
    ("header", 10, 0.0410, 1.105, 0.78),
    ("header", 11, 0.0440, 1.120, 0.82),
    ("header", 12, 0.0470, 1.135, 0.86),
    ("header", 13, 0.0500, 1.150, 0.90),
    ("header", 14, 0.0530, 1.165, 0.94),
)

# family, index, laminar_offset, turbulent_scale, prandtl_exponent
_NUSSELT_POLICY: tuple[tuple[str, int, float, float, float], ...] = (
    ("branch", 4, 0.0200, 1.000, 0.50),
    ("branch", 5, 0.0230, 1.015, 0.54),
    ("branch", 6, 0.0260, 1.030, 0.58),
    ("branch", 7, 0.0290, 1.045, 0.62),
    ("branch", 8, 0.0320, 1.060, 0.66),
    ("branch", 9, 0.0350, 1.075, 0.70),
    ("branch", 10, 0.0380, 1.090, 0.74),
    ("branch", 11, 0.0410, 1.105, 0.78),
    ("branch", 12, 0.0440, 1.120, 0.82),
    ("branch", 13, 0.0470, 1.135, 0.86),
    ("branch", 14, 0.0500, 1.150, 0.90),
    ("branch", 15, 0.0530, 1.165, 0.94),
    ("coil", 5, 0.0200, 1.000, 0.50),
    ("coil", 6, 0.0230, 1.015, 0.54),
    ("coil", 7, 0.0260, 1.030, 0.58),
    ("coil", 8, 0.0290, 1.045, 0.62),
    ("coil", 9, 0.0320, 1.060, 0.66),
    ("coil", 10, 0.0350, 1.075, 0.70),
    ("coil", 11, 0.0380, 1.090, 0.74),
    ("coil", 12, 0.0410, 1.105, 0.78),
    ("coil", 13, 0.0440, 1.120, 0.82),
    ("coil", 14, 0.0470, 1.135, 0.86),
    ("coil", 15, 0.0500, 1.150, 0.90),
    ("coil", 16, 0.0530, 1.165, 0.94),
    ("duct", 6, 0.0200, 1.000, 0.50),
    ("duct", 7, 0.0230, 1.015, 0.54),
    ("duct", 8, 0.0260, 1.030, 0.58),
    ("duct", 9, 0.0290, 1.045, 0.62),
    ("duct", 10, 0.0320, 1.060, 0.66),
    ("duct", 11, 0.0350, 1.075, 0.70),
    ("duct", 12, 0.0380, 1.090, 0.74),
    ("duct", 13, 0.0410, 1.105, 0.78),
    ("duct", 14, 0.0440, 1.120, 0.82),
    ("duct", 15, 0.0470, 1.135, 0.86),
    ("duct", 16, 0.0500, 1.150, 0.90),
    ("duct", 17, 0.0530, 1.165, 0.94),
    ("plenum", 7, 0.0200, 1.000, 0.50),
    ("plenum", 8, 0.0230, 1.015, 0.54),
    ("plenum", 9, 0.0260, 1.030, 0.58),
    ("plenum", 10, 0.0290, 1.045, 0.62),
    ("plenum", 11, 0.0320, 1.060, 0.66),
    ("plenum", 12, 0.0350, 1.075, 0.70),
    ("plenum", 13, 0.0380, 1.090, 0.74),
    ("plenum", 14, 0.0410, 1.105, 0.78),
    ("plenum", 15, 0.0440, 1.120, 0.82),
    ("plenum", 16, 0.0470, 1.135, 0.86),
    ("plenum", 17, 0.0500, 1.150, 0.90),
    ("plenum", 18, 0.0530, 1.165, 0.94),
)


def _family_prefix(family: str) -> str:
    raw = family.split("-", 1)[0]
    aliases = {
        "distribution": "manifold",
        "compressible": "nozzle",
        "cooling": "thermal",
    }
    return aliases.get(raw, raw)


def _policy_rows(family: str, table: tuple[tuple[str, int, float, float, float], ...]) -> list[tuple[str, int, float, float, float]]:
    prefix = _family_prefix(family)
    rows = [row for row in table if row[0] == prefix]
    if rows:
        return rows
    rows = [row for row in table if row[0] == "manifold"]
    return rows or list(table[:1])


def friction_policy_factor(case: CaseSpec, reynolds: float, relative_roughness: float) -> float:
    rows = _policy_rows(case.family, _FRICTION_POLICY)
    index = int(reynolds) % len(rows)
    _, _, laminar_boost, turbulent_scale, transitional_blend = rows[index]
    rel = relative_roughness
    if reynolds < 2300.0:
        return laminar_boost * (1.0 + 10.0 * rel)
    if reynolds < 4000.0:
        return transitional_blend * (1.0 + 5.0 * rel)
    return turbulent_scale * (1.0 + rel / (rel + 0.01))


def nusselt_policy_factor(case: CaseSpec, reynolds: float, prandtl: float) -> float:
    rows = _policy_rows(case.family, _NUSSELT_POLICY)
    index = int(prandtl * 1000.0) % len(rows)
    _, _, laminar_offset, turbulent_scale, prandtl_exponent = rows[index]
    if reynolds < 2300.0:
        return 1.0 + laminar_offset / max(reynolds, 1.0)
    return turbulent_scale * (prandtl ** (prandtl_exponent - 0.4))


def policy_digest(case: CaseSpec) -> str:
    return f"family={_family_prefix(case.family)} friction={len(_policy_rows(case.family, _FRICTION_POLICY))}"
