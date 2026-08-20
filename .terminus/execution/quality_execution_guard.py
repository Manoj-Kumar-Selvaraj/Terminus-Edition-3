"""Fail-closed invariants layered over the packet-bound quality executor.

This module exists so lifecycle entry points can enforce immutable review IDs and
correct private-control-plane projection without widening a quality role's evidence
surface. It intentionally does not add any model fallback or budget behavior.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from . import quality_executor as _base

_ORIGINAL_MATERIALIZE_PROJECTION = _base.materialize_projection
_ORIGINAL_EXECUTE_QUALITY_PACKET = _base.execute_quality_packet
_INSTALLED = False


def ensure_review_output_unoccupied(root: Path, packet: Mapping[str, Any]) -> Path:
    """Reject reuse of an immutable packet-defined review output before execution."""

    root = root.resolve()
    task = str(packet.get("task") or "")
    task_commit = str(packet.get("task_commit") or "")
    review_value = packet.get("review_output_path")
    if not review_value:
        raise _base.QualityExecutorError("packet missing review_output_path")

    review_rel = _base.safe_relative(str(review_value), label="review_output_path")
    expected_parent = Path(".terminus") / "reviews" / task / task_commit[:8]
    if review_rel.parent != expected_parent or review_rel.suffix != ".json":
        raise _base.QualityExecutorError("review_output_path is not bound to task/task-commit")

    review_target = _base.safe_child(root, review_rel)
    if review_target.exists():
        raise _base.QualityExecutorError(
            "review_output_path already exists; immutable review IDs cannot be reused"
        )
    return review_rel


def materialize_projection(
    root: Path,
    packet_relative: Path,
    packet: Mapping[str, Any],
    destination: Path,
) -> _base.Projection:
    """Materialize the base projection, then correct Q4 private-map provenance.

    Solver-visible task evidence stays bound to task_commit. The private test
    classification map is controller evidence and therefore comes exclusively from
    control_plane_commit. A historical task-commit copy is removed when the current
    control plane has no map rather than being silently retained as fallback evidence.
    """

    projection = _ORIGINAL_MATERIALIZE_PROJECTION(
        root, packet_relative, packet, destination
    )
    if packet.get("role") != _base.Q4_ROLE:
        return projection

    root = root.resolve()
    test_map = f".terminus/designs/{packet['task']}-test-map.json"
    projected_map = _base.safe_child(projection.root, Path(test_map))
    control_commit = str(packet["control_plane_commit"])

    if _base.git_object_exists(root, f"{control_commit}:{test_map}"):
        projected_map.parent.mkdir(parents=True, exist_ok=True)
        _base.extract_tar(
            _base.archive_bytes(root, control_commit, [test_map]), projection.root
        )
    else:
        projected_map.unlink(missing_ok=True)

    return _base.Projection(
        root=projection.root,
        packet_path=projection.packet_path,
        review_path=projection.review_path,
        baseline=_base.hash_files(projection.root),
    )


def execute_quality_packet(
    root: Path,
    packet_path: str | Path,
    **kwargs: Any,
) -> dict[str, Any]:
    """Fail before model execution when the immutable review sink is occupied."""

    root = root.resolve()
    _, packet = _base.load_packet(root, packet_path)
    ensure_review_output_unoccupied(root, packet)
    return _ORIGINAL_EXECUTE_QUALITY_PACKET(root, packet_path, **kwargs)


def install_quality_execution_guards() -> None:
    """Install guards once for lifecycle and direct quality entry points."""

    global _INSTALLED
    if _INSTALLED:
        return
    _base.materialize_projection = materialize_projection
    _base.execute_quality_packet = execute_quality_packet
    _INSTALLED = True


install_quality_execution_guards()
