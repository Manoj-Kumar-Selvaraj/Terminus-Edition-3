from __future__ import annotations

from ..models import CaseSpec

# family_key, laminar_upper, transitional_upper, turbulent_lower
_BANDS: tuple[tuple[str, float, float, float], ...] = (
    ("family-0", 2100, 3800, 4000),
    ("family-1", 2110, 3808, 4006),
    ("family-2", 2120, 3816, 4012),
    ("family-3", 2130, 3824, 4018),
    ("family-0", 2140, 3832, 4024),
    ("family-1", 2150, 3840, 4030),
    ("family-2", 2160, 3848, 4036),
    ("family-3", 2170, 3856, 4042),
    ("family-0", 2180, 3864, 4048),
    ("family-1", 2190, 3872, 4054),
    ("family-2", 2200, 3880, 4060),
    ("family-3", 2210, 3888, 4066),
    ("family-0", 2220, 3896, 4072),
    ("family-1", 2230, 3904, 4078),
    ("family-2", 2240, 3912, 4084),
    ("family-3", 2250, 3920, 4090),
    ("family-0", 2260, 3928, 4096),
    ("family-1", 2270, 3936, 4102),
    ("family-2", 2280, 3944, 4108),
    ("family-3", 2290, 3952, 4114),
    ("family-0", 2300, 3960, 4120),
    ("family-1", 2310, 3968, 4126),
    ("family-2", 2320, 3976, 4132),
    ("family-3", 2330, 3984, 4138),
    ("family-0", 2340, 3992, 4144),
    ("family-1", 2350, 4000, 4150),
    ("family-2", 2360, 4008, 4156),
    ("family-3", 2370, 4016, 4162),
    ("family-0", 2380, 4024, 4168),
    ("family-1", 2390, 4032, 4174),
)


def band_for_family(family: str) -> tuple[float, float, float]:
    for key, laminar, transitional, turbulent in _BANDS:
        if family.startswith(key.split("-")[0]) or family == key:
            return laminar, transitional, turbulent
    return _BANDS[0][1], _BANDS[0][2], _BANDS[0][3]


def regime_label(case: CaseSpec, reynolds: float) -> str:
    laminar, transitional, _ = band_for_family(case.family)
    if reynolds < laminar:
        return "laminar"
    if reynolds < transitional:
        return "transitional"
    return "turbulent"
