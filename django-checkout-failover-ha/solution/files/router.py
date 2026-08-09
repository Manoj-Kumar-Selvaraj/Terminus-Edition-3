from __future__ import annotations

from django.conf import settings

from controlplane.lag import replica_eligible
from controlplane.sessions import has_sticky_pin


class ShopdeskRouter:
    def db_for_read(self, model, **hints):
        return None

    def db_for_write(self, model, **hints):
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
