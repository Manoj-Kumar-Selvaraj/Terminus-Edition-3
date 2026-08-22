from __future__ import annotations

from ..models import CaseSpec, OperatingPointSpec


def available_head_pa(point: OperatingPointSpec) -> float:
    return max(point.inlet_total_pressure_pa - point.outlet_static_pressure_pa, 1e-9)


def head_utilization(pressure_drop_pa: float, point: OperatingPointSpec) -> float:
    return pressure_drop_pa / available_head_pa(point)


def compressible_head_cap(case: CaseSpec, point: OperatingPointSpec, uncapped_drop_pa: float) -> float:
    if case.fluid.model != "ideal_gas":
        return uncapped_drop_pa
    available = available_head_pa(point)
    return min(uncapped_drop_pa * 0.88, available * 0.92)
