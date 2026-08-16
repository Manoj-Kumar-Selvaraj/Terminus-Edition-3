from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

from controlplane.operator_audit import record_action
from controlplane.reports import write_failover_status


class Command(BaseCommand):
    help = "Write failover-status.json for the desk."

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--output",
            default="/app/ha/out/failover-status.json",
        )

    def handle(self, *args, **options) -> None:
        path = Path(str(options["output"]))
        write_failover_status(path)
        record_action(
            getattr(settings, "BASE_DIR", "/app/ha"),
            action="dump_failover",
            actor="manage.py",
            node_id=getattr(settings, "AZ_ID", "az-a"),
            output=str(path),
        )
        self.stdout.write(str(path))
