#!/usr/bin/env bash
set -euo pipefail
ROOT="${HA_ROOT:-/app/ha}"
install -m 0644 /solution/files/router.py "$ROOT/controlplane/router.py"
install -m 0644 /solution/files/fencing.py "$ROOT/controlplane/fencing.py"
install -m 0644 /solution/files/lag.py "$ROOT/controlplane/lag.py"
install -m 0644 /solution/files/sessions.py "$ROOT/controlplane/sessions.py"
install -m 0644 /solution/files/idempotency.py "$ROOT/controlplane/idempotency.py"
install -m 0644 /solution/files/replica.py "$ROOT/controlplane/replica.py"
install -m 0644 /solution/files/reports.py "$ROOT/controlplane/reports.py"
install -m 0644 /solution/files/views.py "$ROOT/controlplane/views.py"
install -m 0644 /solution/files/settings.py "$ROOT/shopdesk/settings.py"
install -m 0644 /solution/files/fulfill_services.py "$ROOT/fulfill/services.py"
mkdir -p "$ROOT/state/pin-cache" "$ROOT/out"
export HA_ROOT="$ROOT"
export DJANGO_SETTINGS_MODULE=shopdesk.settings
export PYTHONPATH="$ROOT${PYTHONPATH:+:$PYTHONPATH}"
python3 -m py_compile \
  "$ROOT/controlplane/router.py" \
  "$ROOT/controlplane/fencing.py" \
  "$ROOT/controlplane/lag.py" \
  "$ROOT/controlplane/sessions.py" \
  "$ROOT/controlplane/idempotency.py" \
  "$ROOT/controlplane/replica.py" \
  "$ROOT/controlplane/reports.py" \
  "$ROOT/controlplane/views.py"
python3 "$ROOT/manage.py" sync_standby
python3 "$ROOT/manage.py" cutover --node az-b
python3 - <<'PY'
import os
import sys

sys.path.insert(0, os.environ["HA_ROOT"])
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "shopdesk.settings")
import django

django.setup()
from controlplane.models import FenceLease
from django.db.models import Count, Min
from fulfill.models import SideEffect, WebhookDelivery

lease = FenceLease.objects.using("default").get(resource="checkout-primary")
lease.owner_node = "az-b"
lease.writable = 1
lease.save(using="default")
replica = FenceLease.objects.using("replica").filter(resource="checkout-primary").first()
if replica is not None:
    replica.owner_node = "az-b"
    replica.epoch = lease.epoch
    replica.writable = 0
    replica.save(using="replica")

dupes = (
    SideEffect.objects.using("default")
    .values("attempt_id", "kind")
    .annotate(n=Count("id"), keep=Min("id"))
    .filter(n__gt=1)
)
for row in dupes:
    doomed = SideEffect.objects.using("default").filter(
        attempt_id=row["attempt_id"], kind=row["kind"]
    ).exclude(pk=row["keep"])
    WebhookDelivery.objects.using("default").filter(side_effect__in=doomed).delete()
    doomed.delete()
PY
python3 "$ROOT/manage.py" sync_standby
python3 "$ROOT/manage.py" dump_failover --output "$ROOT/out/failover-status.json"
