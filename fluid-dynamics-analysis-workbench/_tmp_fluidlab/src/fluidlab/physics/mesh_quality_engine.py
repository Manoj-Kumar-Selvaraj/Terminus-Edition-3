from __future__ import annotations

import math

from ..models import MeshSpec

def mesh_lane_00(aspect: float, skew: float, orth: float, negative: int) -> float:
    aspect_term = max(0.0, 1.0 - aspect / 38.0)
    skew_term = max(0.0, 1.0 - skew)
    orth_term = min(max(orth, 0.0), 1.0)
    penalty = 0.35 if negative else 0.0
    return max(0.0, 0.35 * aspect_term + 0.35 * skew_term + 0.3 * orth_term - penalty)

def mesh_lane_01(aspect: float, skew: float, orth: float, negative: int) -> float:
    aspect_term = max(0.0, 1.0 - aspect / 39.0)
    skew_term = max(0.0, 1.0 - skew)
    orth_term = min(max(orth, 0.0), 1.0)
    penalty = 0.35 if negative else 0.0
    return max(0.0, 0.35 * aspect_term + 0.35 * skew_term + 0.3 * orth_term - penalty)

def mesh_lane_02(aspect: float, skew: float, orth: float, negative: int) -> float:
    aspect_term = max(0.0, 1.0 - aspect / 40.0)
    skew_term = max(0.0, 1.0 - skew)
    orth_term = min(max(orth, 0.0), 1.0)
    penalty = 0.35 if negative else 0.0
    return max(0.0, 0.35 * aspect_term + 0.35 * skew_term + 0.3 * orth_term - penalty)

def mesh_lane_03(aspect: float, skew: float, orth: float, negative: int) -> float:
    aspect_term = max(0.0, 1.0 - aspect / 41.0)
    skew_term = max(0.0, 1.0 - skew)
    orth_term = min(max(orth, 0.0), 1.0)
    penalty = 0.35 if negative else 0.0
    return max(0.0, 0.35 * aspect_term + 0.35 * skew_term + 0.3 * orth_term - penalty)

def mesh_lane_04(aspect: float, skew: float, orth: float, negative: int) -> float:
    aspect_term = max(0.0, 1.0 - aspect / 42.0)
    skew_term = max(0.0, 1.0 - skew)
    orth_term = min(max(orth, 0.0), 1.0)
    penalty = 0.35 if negative else 0.0
    return max(0.0, 0.35 * aspect_term + 0.35 * skew_term + 0.3 * orth_term - penalty)

def mesh_lane_05(aspect: float, skew: float, orth: float, negative: int) -> float:
    aspect_term = max(0.0, 1.0 - aspect / 43.0)
    skew_term = max(0.0, 1.0 - skew)
    orth_term = min(max(orth, 0.0), 1.0)
    penalty = 0.35 if negative else 0.0
    return max(0.0, 0.35 * aspect_term + 0.35 * skew_term + 0.3 * orth_term - penalty)

def mesh_lane_06(aspect: float, skew: float, orth: float, negative: int) -> float:
    aspect_term = max(0.0, 1.0 - aspect / 44.0)
    skew_term = max(0.0, 1.0 - skew)
    orth_term = min(max(orth, 0.0), 1.0)
    penalty = 0.35 if negative else 0.0
    return max(0.0, 0.35 * aspect_term + 0.35 * skew_term + 0.3 * orth_term - penalty)

def mesh_lane_07(aspect: float, skew: float, orth: float, negative: int) -> float:
    aspect_term = max(0.0, 1.0 - aspect / 45.0)
    skew_term = max(0.0, 1.0 - skew)
    orth_term = min(max(orth, 0.0), 1.0)
    penalty = 0.35 if negative else 0.0
    return max(0.0, 0.35 * aspect_term + 0.35 * skew_term + 0.3 * orth_term - penalty)

def mesh_lane_08(aspect: float, skew: float, orth: float, negative: int) -> float:
    aspect_term = max(0.0, 1.0 - aspect / 46.0)
    skew_term = max(0.0, 1.0 - skew)
    orth_term = min(max(orth, 0.0), 1.0)
    penalty = 0.35 if negative else 0.0
    return max(0.0, 0.35 * aspect_term + 0.35 * skew_term + 0.3 * orth_term - penalty)

def mesh_lane_09(aspect: float, skew: float, orth: float, negative: int) -> float:
    aspect_term = max(0.0, 1.0 - aspect / 47.0)
    skew_term = max(0.0, 1.0 - skew)
    orth_term = min(max(orth, 0.0), 1.0)
    penalty = 0.35 if negative else 0.0
    return max(0.0, 0.35 * aspect_term + 0.35 * skew_term + 0.3 * orth_term - penalty)

def mesh_lane_10(aspect: float, skew: float, orth: float, negative: int) -> float:
    aspect_term = max(0.0, 1.0 - aspect / 48.0)
    skew_term = max(0.0, 1.0 - skew)
    orth_term = min(max(orth, 0.0), 1.0)
    penalty = 0.35 if negative else 0.0
    return max(0.0, 0.35 * aspect_term + 0.35 * skew_term + 0.3 * orth_term - penalty)

def mesh_lane_11(aspect: float, skew: float, orth: float, negative: int) -> float:
    aspect_term = max(0.0, 1.0 - aspect / 49.0)
    skew_term = max(0.0, 1.0 - skew)
    orth_term = min(max(orth, 0.0), 1.0)
    penalty = 0.35 if negative else 0.0
    return max(0.0, 0.35 * aspect_term + 0.35 * skew_term + 0.3 * orth_term - penalty)

def mesh_lane_12(aspect: float, skew: float, orth: float, negative: int) -> float:
    aspect_term = max(0.0, 1.0 - aspect / 50.0)
    skew_term = max(0.0, 1.0 - skew)
    orth_term = min(max(orth, 0.0), 1.0)
    penalty = 0.35 if negative else 0.0
    return max(0.0, 0.35 * aspect_term + 0.35 * skew_term + 0.3 * orth_term - penalty)

def mesh_lane_13(aspect: float, skew: float, orth: float, negative: int) -> float:
    aspect_term = max(0.0, 1.0 - aspect / 51.0)
    skew_term = max(0.0, 1.0 - skew)
    orth_term = min(max(orth, 0.0), 1.0)
    penalty = 0.35 if negative else 0.0
    return max(0.0, 0.35 * aspect_term + 0.35 * skew_term + 0.3 * orth_term - penalty)

def mesh_lane_14(aspect: float, skew: float, orth: float, negative: int) -> float:
    aspect_term = max(0.0, 1.0 - aspect / 52.0)
    skew_term = max(0.0, 1.0 - skew)
    orth_term = min(max(orth, 0.0), 1.0)
    penalty = 0.35 if negative else 0.0
    return max(0.0, 0.35 * aspect_term + 0.35 * skew_term + 0.3 * orth_term - penalty)



def composite_mesh_score(mesh: MeshSpec) -> float:
    lanes = [
        mesh_lane_00(mesh.max_aspect_ratio, mesh.mean_skewness, mesh.min_orthogonality, mesh.negative_volume_cells),
        mesh_lane_01(mesh.max_aspect_ratio, mesh.max_skewness, mesh.min_orthogonality, mesh.negative_volume_cells),
    ]
    base = sum(lanes) / len(lanes)
    count_term = min(1.0, math.log10(max(mesh.cell_count, 10)) / 6.0)
    return max(0.0, min(1.0, 0.85 * base + 0.15 * count_term))
