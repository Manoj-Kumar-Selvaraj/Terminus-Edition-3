from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from controlplane.cutover_fsm import CutoverState, begin_fence, complete_promote
from controlplane.fencing import promote_standby
from controlplane.operator_audit import record_action


class Command(BaseCommand):
    help = "Move the checkout writer lease to another app box."

    def add_arguments(self, parser) -> None:
        parser.add_argument("--node", required=True)

    def handle(self, *args, **options) -> None:
        node = str(options["node"])
        if not node:
            raise CommandError("node required")
        state = CutoverState(active_writer=getattr(settings, "AZ_ID", "az-a"), epoch=1)
        begin_fence(state, target=node)
        row = promote_standby(node)
        complete_promote(state, target=node, new_epoch=int(row.epoch) + 1)
        record_action(
            getattr(settings, "BASE_DIR", "/app/ha"),
            action="cutover",
            actor="manage.py",
            node_id=node,
            epoch=row.epoch,
            writable=row.writable,
        )
        self.stdout.write(f"{row.owner_node} epoch={row.epoch} writable={row.writable}")
