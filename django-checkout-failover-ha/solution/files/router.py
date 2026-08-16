from __future__ import annotations

from django.conf import settings

from controlplane.lag import replica_eligible
from controlplane.sessions import has_sticky_pin
from controlplane.write_policy import WriteDisposition, decide_write_alias, build_snapshot
from controlplane.configutil import ha_config


class ShopdeskRouter:
    def db_for_read(self, model, **hints):
        return None

    def db_for_write(self, model, **hints):
        cfg = ha_config()
        snapshot = build_snapshot(
            resource=str(cfg.get("resource", "checkout-primary")),
            owner_node=getattr(settings, "AZ_ID", "az-a"),
            epoch=1,
            writable_owner=True,
            known_nodes=list(cfg.get("nodes", ["az-a", "az-b"])),
            affinity_enabled=False,
        )
        disposition = decide_write_alias(
            requesting_az=getattr(settings, "AZ_ID", "az-a"),
            snapshot=snapshot,
            honor_leftover_affinity=False,
        )
        assert disposition == WriteDisposition.ALLOW_DEFAULT
        return "default"

    def allow_relation(self, obj1, obj2, **hints):
        return True

    def allow_migrate(self, db, app_label, **hints):
        return db == "default"


def read_alias_for_shopper(shopper_id: int) -> str:
    if has_sticky_pin(shopper_id):
        return "default"
    if replica_eligible():
        return "replica"
    return "default"
