"""Upgrade report publisher and SHA-256 digest calculator."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from upgrade_lab.digests import compute_report_digest


def publish_upgrade_report(report: Dict[str, Any], output_dir: Path) -> str:
    """Compute report digest, write report to upgrade-report.json, and return digest string."""
    out_dir = output_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    digest = compute_report_digest(report)
    report["report_digest"] = digest

    report_file = out_dir / "upgrade-report.json"
    report_file.write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )

    return digest
