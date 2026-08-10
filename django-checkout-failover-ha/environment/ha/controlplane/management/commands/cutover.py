from django.core.management.base import BaseCommand, CommandError

from controlplane.fencing import promote_standby


class Command(BaseCommand):
    help = "Move the checkout writer lease to another app box."

    def add_arguments(self, parser) -> None:
        parser.add_argument("--node", required=True)

    def handle(self, *args, **options) -> None:
        node = str(options["node"])
        if not node:
            raise CommandError("node required")
        row = promote_standby(node)
        self.stdout.write(f"{row.owner_node} epoch={row.epoch} writable={row.writable}")
