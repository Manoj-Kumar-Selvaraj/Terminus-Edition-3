from __future__ import annotations

from ..models import CaseSpec


def stability_margin(case: CaseSpec, mach: float, cfl: float) -> float:
    mach_margin = case.limits.max_mach - mach
    cfl_margin = case.limits.max_cfl - cfl
    coupling = 0.5 * (mach / max(case.limits.max_mach, 1e-9) + cfl / max(case.limits.max_cfl, 1e-9))
    return min(mach_margin, cfl_margin) * (1.0 - 0.05 * coupling)
