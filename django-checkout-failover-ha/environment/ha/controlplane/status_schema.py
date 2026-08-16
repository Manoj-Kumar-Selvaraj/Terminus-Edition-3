"""Failover status document schema and builders for dump_failover."""
from __future__ import annotations

from dataclasses import asdict, dataclass, fields
from typing import Any, Mapping, Sequence


STATUS_KEYS = (
    "desk",
    "accepting_checkout",
    "writer",
    "writer_epoch",
    "writers_seen",
    "standby_readable",
    "primary_seq",
    "standby_seq",
    "seq_gap",
    "pins",
    "double_primary",
    "repeat_captures",
    "standby_only_orders",
    "incident_orders_on_standby",
    "fence_copied_to_standby",
)


@dataclass
class FailoverStatus:
    desk: str
    accepting_checkout: bool
    writer: str
    writer_epoch: int
    writers_seen: list[str]
    standby_readable: bool
    primary_seq: int
    standby_seq: int
    seq_gap: int
    pins: str
    double_primary: bool
    repeat_captures: int
    standby_only_orders: int
    incident_orders_on_standby: bool
    fence_copied_to_standby: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def validate_status_object(raw: Mapping[str, Any]) -> list[str]:
    errors: list[str] = []
    for key in STATUS_KEYS:
        if key not in raw:
            errors.append(f"missing:{key}")
    for key in raw.keys():
        if key not in STATUS_KEYS:
            errors.append(f"unknown:{key}")
    if "pins" in raw and raw["pins"] not in {"shared", "local", "missing"}:
        errors.append("pins:invalid")
    if "writers_seen" in raw and not isinstance(raw["writers_seen"], list):
        errors.append("writers_seen:not_list")
    bool_keys = (
        "accepting_checkout",
        "standby_readable",
        "double_primary",
        "incident_orders_on_standby",
        "fence_copied_to_standby",
    )
    for key in bool_keys:
        if key in raw and not isinstance(raw[key], bool):
            errors.append(f"{key}:not_bool")
    int_keys = (
        "writer_epoch",
        "primary_seq",
        "standby_seq",
        "seq_gap",
        "repeat_captures",
        "standby_only_orders",
    )
    for key in int_keys:
        if key in raw and type(raw[key]) is not int:
            errors.append(f"{key}:not_int")
    return errors


def compute_accepting_checkout(
    *,
    writers_seen: Sequence[str],
    repeat_captures: int,
    standby_only_orders: int,
    seq_gap: int,
    max_lag_lsn: int,
    incident_orders_on_standby: bool,
    fence_copied_to_standby: bool,
    pins: str,
) -> bool:
    if len([w for w in writers_seen if w]) != 1:
        return False
    if int(repeat_captures) != 0:
        return False
    if int(standby_only_orders) != 0:
        return False
    if int(seq_gap) > int(max_lag_lsn):
        return False
    if not incident_orders_on_standby:
        return False
    if fence_copied_to_standby:
        return False
    if pins != "shared":
        return False
    return True


def build_status(
    *,
    desk: str,
    writer: str,
    writer_epoch: int,
    writers_seen: Sequence[str],
    standby_readable: bool,
    primary_seq: int,
    standby_seq: int,
    max_lag_lsn: int,
    pins: str,
    repeat_captures: int,
    standby_only_orders: int,
    incident_orders_on_standby: bool,
    fence_copied_to_standby: bool,
) -> FailoverStatus:
    writers = [str(w) for w in writers_seen]
    gap = max(0, int(primary_seq) - int(standby_seq))
    accepting = compute_accepting_checkout(
        writers_seen=writers,
        repeat_captures=repeat_captures,
        standby_only_orders=standby_only_orders,
        seq_gap=gap,
        max_lag_lsn=max_lag_lsn,
        incident_orders_on_standby=incident_orders_on_standby,
        fence_copied_to_standby=fence_copied_to_standby,
        pins=pins,
    )
    return FailoverStatus(
        desk=desk,
        accepting_checkout=accepting,
        writer=writer,
        writer_epoch=int(writer_epoch),
        writers_seen=writers,
        standby_readable=bool(standby_readable),
        primary_seq=int(primary_seq),
        standby_seq=int(standby_seq),
        seq_gap=gap,
        pins=pins,
        double_primary=len(writers) > 1,
        repeat_captures=int(repeat_captures),
        standby_only_orders=int(standby_only_orders),
        incident_orders_on_standby=bool(incident_orders_on_standby),
        fence_copied_to_standby=bool(fence_copied_to_standby),
    )


def status_field_names() -> tuple[str, ...]:
    return tuple(f.name for f in fields(FailoverStatus))
