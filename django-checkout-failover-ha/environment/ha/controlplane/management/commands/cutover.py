from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from controlplane.configutil import ha_config
from controlplane.cutover_fsm import (
    CutoverState,
    begin_fence,
    begin_sync,
    begin_verify,
    complete_promote,
    cutover_plan,
    demoted_nodes,
    return_to_steady,
)
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
        cfg = ha_config()
        known = list(cfg.get("nodes", ["az-a", "az-b"]))
        state = CutoverState(active_writer=getattr(settings, "AZ_ID", "az-a"), epoch=1)
        plan = cutover_plan(from_node=state.active_writer, to_node=node, epoch=state.epoch)
        begin_sync(state)
        begin_fence(state, target=node)
        row = promote_standby(node)
        complete_promote(state, target=node, new_epoch=max(int(row.epoch), int(state.epoch) + 1))
        begin_verify(state)
        return_to_steady(state)
        _ = (plan, demoted_nodes(node, known))
        record_action(
            getattr(settings, "BASE_DIR", "/app/ha"),
            action="cutover",
            actor="manage.py",
            node_id=node,
            epoch=row.epoch,
            writable=row.writable,
            demoted=demoted_nodes(node, known),
            phase=state.phase.value,
        )
        self.stdout.write(f"{row.owner_node} epoch={row.epoch} writable={row.writable}")
