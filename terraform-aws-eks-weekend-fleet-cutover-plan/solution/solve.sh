#!/usr/bin/env bash
# Install the reference module implementation, then render the review document
# with the workspace's own renderer.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MODULE_DIR="/app/environment/terraform/modules/eks_weekend_fleet"
REFERENCE_DIR="${HERE}/terraform/modules/eks_weekend_fleet"

test -d "${REFERENCE_DIR}"
test -d "${MODULE_DIR}"

# Environment ships only a variable/provider shell. Replace the module tree with
# the known-good implementation rather than patching empty placeholders.
rm -f "${MODULE_DIR}"/*.tf
cp -a "${REFERENCE_DIR}/." "${MODULE_DIR}/"

# Drop any workspace state left behind by an earlier init so the renderer picks
# the providers up from the vendored mirror.
rm -rf /app/environment/terraform/.terraform

/app/environment/scripts/render-eks-weekend-plan
/app/environment/scripts/simulate-eks-weekend-cutover

python3 - <<'PY'
import json
import sys
from pathlib import Path

path = Path("/app/output/eks_weekend_fleet_plan.json")
if not path.is_file():
    sys.exit(f"missing plan document: {path}")
doc = json.loads(path.read_text(encoding="utf-8"))
if not str(doc.get("format_version", "")).startswith("1."):
    sys.exit(f"unexpected format_version: {doc.get('format_version')!r}")
if doc.get("errored") is not False or doc.get("complete") is not True:
    sys.exit("plan document is incomplete or errored")
if not doc.get("resource_changes"):
    sys.exit("plan document has no resource_changes")
print(f"oracle plan ok: {len(doc['resource_changes'])} resources")

timeline = Path("/app/output/eks_weekend_cutover_timeline.json")
if not timeline.is_file():
    sys.exit(f"missing cutover timeline: {timeline}")
cutover = json.loads(timeline.read_text(encoding="utf-8"))
if cutover.get("ok") is not True:
    sys.exit(f"cutover timeline not ok: {cutover.get('error')!r}")
print(f"oracle cutover ok: {len(cutover.get('steps', []))} steps")
PY
