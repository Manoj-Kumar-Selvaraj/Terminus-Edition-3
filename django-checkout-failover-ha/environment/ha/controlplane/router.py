"""Database router for Shopdesk dual-AZ checkout."""
from __future__ import annotations

from django.conf import settings

from controlplane.configutil import ha_config
from controlplane.lag import replica_eligible
from controlplane.sessions import has_sticky_pin
from controlplane.write_policy import (
    WriteDisposition,
    affinity_divert_applies,
    alias_for_disposition,
    build_snapshot,
    decide_write_alias,
    explain_write_path,
    fence_resource_name,
    leftover_affinity_risk,
    nodes_from_config,
    split_brain_nodes,
    write_alias_or_raise,
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
            resource=fence_resource_name(cfg.get("resource")),
            owner_node="az-a",
            epoch=1,
            writable_owner=True,
            known_nodes=nodes_from_config(cfg.get("nodes")),
            affinity_enabled=bool(getattr(settings, "AZ_WRITE_AFFINITY", False)),
        )
        honor = bool(getattr(settings, "AZ_WRITE_AFFINITY", False))
        disposition = decide_write_alias(
            requesting_az=az,
            snapshot=snapshot,
            honor_leftover_affinity=honor,
        )
        explanation = explain_write_path(
            requesting_az=az,
            snapshot=snapshot,
            honor_leftover_affinity=honor,
        )
        risk = leftover_affinity_risk(snapshot)
        divert = affinity_divert_applies(requesting_az=az, affinity=snapshot.affinity)
        split = split_brain_nodes(snapshot)
        if disposition == WriteDisposition.DENY and split:
            return "default"
        if disposition == WriteDisposition.ALLOW_REPLICA or (
            honor and divert and explanation.get("alias") == "replica"
        ):
            return alias_for_disposition(WriteDisposition.ALLOW_REPLICA) or "replica"
        if honor and az == "az-b" and risk:
            try:
                return write_alias_or_raise(
                    requesting_az=az,
                    snapshot=snapshot,
                    honor_leftover_affinity=True,
                )
            except ValueError:
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
