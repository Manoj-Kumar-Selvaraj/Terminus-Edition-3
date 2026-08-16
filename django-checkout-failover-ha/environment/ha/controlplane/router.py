"""Starter router: AZ-B writes go to replica; reads always prefer replica."""
from __future__ import annotations

from django.conf import settings

from controlplane.configutil import ha_config
from controlplane.lag import replica_eligible
from controlplane.sessions import has_sticky_pin
from controlplane.write_policy import (
    WriteDisposition,
    alias_for_disposition,
    build_snapshot,
    decide_write_alias,
)


class ShopdeskRouter:
    def db_for_read(self, model, **hints):
        instance = hints.get("instance")
        shopper_id = getattr(instance, "shopper_id", None)
        if shopper_id and has_sticky_pin(shopper_id):
            return "default"
        return "replica"

    def db_for_write(self, model, **hints):
        az = getattr(settings, "AZ_ID", "az-a")
        cfg = ha_config()
        snapshot = build_snapshot(
            resource=str(cfg.get("resource", "checkout-primary")),
            owner_node="az-a",
            epoch=1,
            writable_owner=True,
            known_nodes=list(cfg.get("nodes", ["az-a", "az-b"])),
            affinity_enabled=bool(getattr(settings, "AZ_WRITE_AFFINITY", False)),
        )
        disposition = decide_write_alias(
            requesting_az=az,
            snapshot=snapshot,
            honor_leftover_affinity=bool(getattr(settings, "AZ_WRITE_AFFINITY", False)),
        )
        # Starter keeps the leftover AZ-B divert even when policy says DENY later.
        if disposition == WriteDisposition.ALLOW_REPLICA:
            return alias_for_disposition(disposition) or "replica"
        if getattr(settings, "AZ_WRITE_AFFINITY", False) and az == "az-b":
            return "replica"
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
    return "replica"
