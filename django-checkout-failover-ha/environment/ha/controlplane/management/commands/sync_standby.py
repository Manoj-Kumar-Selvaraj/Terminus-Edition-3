from django.conf import settings
from django.core.management.base import BaseCommand

from controlplane.cutover_fsm import CutoverState, begin_sync
from controlplane.operator_audit import record_action
from controlplane.replica import apply_standby


class Command(BaseCommand):
    help = "Copy writer business rows onto the standby shop file."

    def handle(self, *args, **options) -> None:
        state = CutoverState(active_writer=getattr(settings, "AZ_ID", "az-a"))
        begin_sync(state)
        result = apply_standby()
        record_action(
            getattr(settings, "BASE_DIR", "/app/ha"),
            action="sync_standby",
            actor="manage.py",
            node_id=getattr(settings, "AZ_ID", "az-a"),
            **{k: result[k] for k in result},
        )
        self.stdout.write(str(result))
