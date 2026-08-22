from __future__ import annotations

import math

from ..models import MeshSpec


def _aspect_score(max_aspect_ratio: float) -> float:
    return max(0.0, 1.0 - max_aspect_ratio / 40.0)


def _skew_score(mean_skewness: float, max_skewness: float) -> float:
    return 0.55 * max(0.0, 1.0 - mean_skewness) + 0.45 * max(0.0, 1.0 - max_skewness)


def _orthogonality_score(min_orthogonality: float) -> float:
    return min(max(min_orthogonality, 0.0), 1.0)


def _count_score(cell_count: int) -> float:
    return min(1.0, math.log10(max(cell_count, 10)) / 6.0)


def _negative_volume_penalty(negative_volume_cells: int) -> float:
    return 0.35 if negative_volume_cells else 0.0


def composite_mesh_score(mesh: MeshSpec) -> float:
    score = (
        0.25 * _aspect_score(mesh.max_aspect_ratio)
        + 0.25 * _skew_score(mesh.mean_skewness, mesh.max_skewness)
        + 0.2 * _orthogonality_score(mesh.min_orthogonality)
        + 0.1 * _count_score(mesh.cell_count)
        - _negative_volume_penalty(mesh.negative_volume_cells)
    )
    return max(0.0, min(1.0, score))
