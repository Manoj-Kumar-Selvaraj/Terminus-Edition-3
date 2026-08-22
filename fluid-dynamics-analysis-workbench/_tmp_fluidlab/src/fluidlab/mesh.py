from __future__ import annotations

import math

from .models import MeshSpec


def mesh_summary(mesh: MeshSpec) -> dict[str, float | int]:
    aspect_component = max(0.0, 1.0 - mesh.max_aspect_ratio / 40.0)
    mean_skew_component = max(0.0, 1.0 - mesh.mean_skewness)
    max_skew_component = max(0.0, 1.0 - mesh.max_skewness)
    orth_component = min(max(mesh.min_orthogonality, 0.0), 1.0)
    count_component = min(1.0, math.log10(max(mesh.cell_count, 10)) / 6.0)
    negative_penalty = 0.35 if mesh.negative_volume_cells else 0.0
    score = max(
        0.0,
        (
            0.25 * aspect_component
            + 0.25 * mean_skew_component
            + 0.2 * max_skew_component
            + 0.2 * orth_component
            + 0.1 * count_component
            - negative_penalty
        ),
    )
    return {
        "score": score,
        "cell_count": mesh.cell_count,
        "max_aspect_ratio": mesh.max_aspect_ratio,
        "mean_skewness": mesh.mean_skewness,
        "max_skewness": mesh.max_skewness,
        "min_orthogonality": mesh.min_orthogonality,
        "negative_volume_cells": mesh.negative_volume_cells,
    }
