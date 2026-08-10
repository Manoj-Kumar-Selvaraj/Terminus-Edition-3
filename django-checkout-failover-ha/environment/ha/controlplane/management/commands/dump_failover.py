from pathlib import Path

from django.core.management.base import BaseCommand

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
        self.stdout.write(str(path))
