from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

from .models import Config


def _rounded(value: object, digits: int) -> object:
    if isinstance(value, float):
        return round(value, digits)
    if isinstance(value, dict):
        return {key: _rounded(item, digits) for key, item in value.items()}
    if isinstance(value, list):
        return [_rounded(item, digits) for item in value]
    return value


def publication_revision(case_results: list[dict[str, object]]) -> str:
    digest = hashlib.sha256()
    for case in case_results:
        digest.update(str(case["case_id"]).encode("utf-8"))
        digest.update(str(case["source_digest"]).encode("utf-8"))
        digest.update(str(case["status"]).encode("utf-8"))
    return digest.hexdigest()[:20]


def _resolve_path(root: Path, configured: Path) -> Path:
    normalized = str(configured).replace("\\", "/")
    if normalized == "/app/fluidlab":
        return root
    if normalized.startswith("/app/fluidlab/"):
        return root / normalized.removeprefix("/app/fluidlab/")
    path = Path(normalized)
    if path.is_absolute():
        return path
    return root / path


def write_reports(
    config: Config,
    case_results: list[dict[str, object]],
    fleet_rollup: dict[str, object],
    root: Path,
) -> dict[str, str]:
    output_dir = _resolve_path(root, config.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    checkpoint_name = Path(str(config.checkpoint_name).replace("\\", "/"))
    if str(checkpoint_name).replace("\\", "/").startswith("/app/fluidlab/") or checkpoint_name.is_absolute():
        checkpoint_path = _resolve_path(root, checkpoint_name)
    else:
        checkpoint_path = output_dir / checkpoint_name
    checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path = output_dir / config.summary_name
    csv_path = output_dir / config.csv_name
    revision = publication_revision(case_results)
    severity_rank = {status: index for index, status in enumerate(config.severity_order)}
    overall_status = min((case["status"] for case in case_results), key=lambda item: severity_rank[item])
    summary_payload = {
        "schema_version": config.schema_version,
        "system_name": config.system_name,
        "publication_revision": revision,
        "status": overall_status,
        "fleet_rollup": _rounded(fleet_rollup, config.round_digits),
        "cases": _rounded(case_results, config.round_digits),
    }
    summary_path.write_text(json.dumps(summary_payload, indent=2) + "\n", encoding="utf-8")
    csv_rows: list[dict[str, object]] = []
    for case in case_results:
        for point in case["operating_points"]:
            csv_rows.append(
                {
                    "case_id": case["case_id"],
                    "point_id": point["point_id"],
                    "status": point["status"],
                    "flow_regime": point["flow_regime"],
                    "density_kg_m3": round(point["metrics"]["density_kg_m3"], config.round_digits),
                    "velocity_m_s": round(point["metrics"]["velocity_m_s"], config.round_digits),
                    "reynolds": round(point["metrics"]["reynolds"], config.round_digits),
                    "mach": round(point["metrics"]["mach"], config.round_digits),
                    "cfl": round(point["metrics"]["cfl"], config.round_digits),
                    "pressure_drop_pa": round(point["metrics"]["pressure_drop_pa"], config.round_digits),
                    "outlet_temperature_k": round(point["metrics"]["outlet_temperature_k"], config.round_digits),
                    "heat_transfer_coefficient_w_m2k": round(
                        point["metrics"]["heat_transfer_coefficient_w_m2k"], config.round_digits
                    ),
                    "mesh_score": round(case["mesh"]["score"], config.round_digits),
                    "converged": point["convergence"]["converged"],
                    "finding_count": len(point["findings"]),
                }
            )
    csv_rows.sort(key=lambda row: (row["case_id"], severity_rank[row["status"]], row["point_id"]))
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=config.csv_fields)
        writer.writeheader()
        for row in csv_rows:
            writer.writerow(row)
    checkpoint_payload = {
        "schema_version": config.schema_version,
        "publication_revision": revision,
        "status": overall_status,
        "cases": [
            {"case_id": case["case_id"], "source_digest": case["source_digest"], "status": case["status"]}
            for case in case_results
        ],
        "artifacts": [
            {"path": str(summary_path)},
            {"path": str(csv_path)},
            {"path": str(checkpoint_path)},
        ],
    }
    checkpoint_path.write_text(json.dumps(checkpoint_payload, indent=2) + "\n", encoding="utf-8")
    return {
        "summary": str(summary_path),
        "csv": str(csv_path),
        "checkpoint": str(checkpoint_path),
    }
