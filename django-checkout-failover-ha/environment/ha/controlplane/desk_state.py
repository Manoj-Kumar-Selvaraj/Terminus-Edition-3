"""Live desk probes shared by /readyz composition and dump_failover.

This module gathers writer, lag, pin, capture, and standby coverage signals from
the running Shopdesk process so HTTP readiness and the failover dump stay on the
same observations.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence

from django.conf import settings
from django.core.cache import caches
from django.db import connections

from checkout.models import Order
from controlplane.configutil import ha_config
from controlplane.fencing import lease, writable_nodes
from controlplane.ha_metrics import HaMetrics, metrics_from_mapping, probe_codes, readiness_bools
from controlplane.incident_window import build_window, standby_only_refs, summarize_window
from controlplane.lag import lag_lsn, replica_eligible, watermarks
from controlplane.models import FenceLease
from controlplane.pin_contract import classify_store, store_is_shared
from controlplane.readiness_policy import (
    ReadinessInput,
    ReadinessResult,
    evaluate_dump_accepting,
    evaluate_live_readyz,
    merge_writer_lists,
    readiness_blocker_summary,
)
from controlplane.reconnect import AliasHealth, all_aliases_ok, describe_probes, probe_alias, required_aliases
from controlplane.status_schema import STATUS_KEYS, compute_accepting_checkout
from controlplane.watermark_journal import (
    WatermarkJournal,
    describe_assessment,
    gap_from_samples,
    journal_assessment,
    sample_from_mapping,
)
from controlplane.write_policy import merge_fence_views
from fulfill.effect_ledger import EffectRow, repeat_capture_count
from fulfill.models import SideEffect
from fulfill.services import duplicate_effect_count


@dataclass(frozen=True)
class DeskSnapshot:
    writers_seen: list[str]
    primary_seq: int
    standby_seq: int
    seq_gap: int
    max_lag_lsn: int
    pins: str
    pins_reachable: bool
    repeat_captures: int
    standby_only_orders: int
    incident_orders_on_standby: bool
    fence_copied_to_standby: bool
    standby_readable: bool
    writer_epoch: int
    aliases_ok: bool
    metrics: HaMetrics
    live: ReadinessResult
    dump_accepting: bool
    blocker_summary: str


def _pin_store_class() -> str:
    pins = settings.CACHES.get("pins", {})
    return classify_store(str(pins.get("BACKEND", "")), str(pins.get("LOCATION", "")))


def pins_reachable() -> bool:
    root = Path(getattr(settings, "BASE_DIR", "/app/ha"))
    cache_dir = root / "state" / "pin-cache"
    try:
        cache_dir.mkdir(parents=True, exist_ok=True)
        probe = cache_dir / ".probe"
        probe.write_text("ok", encoding="utf-8")
        caches["pins"].set("__desk_probe__", "1", timeout=5)
        return caches["pins"].get("__desk_probe__") == "1"
    except Exception:
        return False


def pins_label(*, reachable: bool, store_class: str) -> str:
    if not reachable:
        return "missing"
    if store_is_shared(store_class):
        return "shared"
    return "local"


def fence_copied_to_standby() -> bool:
    replica = FenceLease.objects.using("replica").filter(resource="checkout-primary").first()
    return replica is not None and int(replica.writable) == 1


def standby_only_order_count() -> int:
    primary_refs = list(Order.objects.using("default").values_list("order_ref", flat=True))
    standby_refs = list(Order.objects.using("replica").values_list("order_ref", flat=True))
    return len(standby_only_refs(primary_refs, standby_refs))


def incident_orders_covered() -> bool:
    cfg = ha_config()
    minimum = int(cfg.get("incident_min_order_id", 19980))
    primary_pairs = list(Order.objects.using("default").values_list("id", "order_ref"))
    standby_refs = list(Order.objects.using("replica").values_list("order_ref", flat=True))
    window = build_window(
        min_order_id=minimum,
        primary_pairs=primary_pairs,
        standby_refs=standby_refs,
    )
    summary = summarize_window(window)
    return bool(summary.get("covered", False))


def effect_rows_for_ledger(*, limit: int = 200) -> list[EffectRow]:
    rows: list[EffectRow] = []
    qs = (
        SideEffect.objects.using("default")
        .order_by("-id")
        .values_list("attempt_id", "kind", "status", "write_lsn")[:limit]
    )
    for attempt_id, kind, status, write_lsn in qs:
        rows.append(
            EffectRow(
                attempt_id=str(attempt_id),
                kind=str(kind),
                status=str(status),
                write_lsn=int(write_lsn),
            )
        )
    return rows


def _open_alias(alias: str) -> None:
    connections[alias].ensure_connection()


def collect_desk_snapshot() -> DeskSnapshot:
    cfg = ha_config()
    max_lag = int(cfg.get("max_lag_lsn", 25))
    primary_seq, standby_seq = watermarks()
    gap = lag_lsn()
    journal = WatermarkJournal()
    primary_sample = sample_from_mapping(
        {"wal_lsn": primary_seq, "applied_lsn": primary_seq, "updated_at": ""},
        role="primary",
    )
    standby_sample = sample_from_mapping(
        {"wal_lsn": standby_seq, "applied_lsn": standby_seq, "updated_at": ""},
        role="standby",
    )
    journal.record(primary_sample)
    journal.record(standby_sample)
    gap_check = gap_from_samples(primary_sample, standby_sample)
    assessment = journal_assessment(journal, budget=max_lag, method="watermark")
    _ = describe_assessment(assessment)
    writers = merge_writer_lists(writable_nodes())
    store_class = _pin_store_class()
    reachable = pins_reachable()
    pins = pins_label(reachable=reachable, store_class=store_class)
    duplicates = duplicate_effect_count()
    ledger_repeats = repeat_capture_count(effect_rows_for_ledger())
    repeats = max(duplicates, ledger_repeats)
    extra = standby_only_order_count()
    covered = incident_orders_covered()
    copied = fence_copied_to_standby()
    alias_health: list[AliasHealth] = [
        probe_alias(name, _open_alias) for name in required_aliases()
    ]
    aliases_ok = all_aliases_ok(alias_health)
    _ = describe_probes(alias_health)
    effective_gap = max(int(gap), int(gap_check), int(assessment.gap))
    metrics = metrics_from_mapping(
        {
            "writers_seen": writers,
            "primary_seq": primary_seq,
            "standby_seq": standby_seq,
            "seq_gap": effective_gap,
            "max_lag_lsn": max_lag,
            "pins": pins,
            "pins_reachable": reachable,
            "repeat_captures": repeats,
            "standby_only_orders": extra,
            "fence_copied_to_standby": copied,
            "incident_orders_on_standby": covered,
        }
    )
    _ = (probe_codes(metrics), readiness_bools(metrics))
    data = ReadinessInput(
        process_up=True,
        writable_nodes=writers,
        seq_gap=int(metrics.seq_gap),
        max_lag_lsn=max_lag,
        pins_shared=pins == "shared",
        pins_reachable=reachable,
        repeat_captures=repeats,
        standby_only_orders=extra,
        fence_copied_to_standby=copied,
        incident_orders_on_standby=covered,
    )
    live = evaluate_live_readyz(data)
    dump_result = evaluate_dump_accepting(data)
    dump_accepting = dump_result.accepting_checkout and compute_accepting_checkout(
        writers_seen=writers,
        repeat_captures=repeats,
        standby_only_orders=extra,
        seq_gap=int(metrics.seq_gap),
        max_lag_lsn=max_lag,
        incident_orders_on_standby=covered,
        fence_copied_to_standby=copied,
        pins=pins,
    )
    row = lease()
    return DeskSnapshot(
        writers_seen=writers,
        primary_seq=primary_seq,
        standby_seq=standby_seq,
        seq_gap=int(metrics.seq_gap),
        max_lag_lsn=max_lag,
        pins=pins,
        pins_reachable=reachable,
        repeat_captures=repeats,
        standby_only_orders=extra,
        incident_orders_on_standby=covered,
        fence_copied_to_standby=copied,
        standby_readable=replica_eligible(),
        writer_epoch=int(row.epoch),
        aliases_ok=aliases_ok,
        metrics=metrics,
        live=live,
        dump_accepting=bool(dump_accepting),
        blocker_summary=readiness_blocker_summary(live),
    )


def snapshot_to_status_dict(snap: DeskSnapshot) -> dict[str, object]:
    writer = snap.writers_seen[0] if snap.writers_seen else lease().owner_node
    payload = {
        "desk": "shopdesk",
        "accepting_checkout": bool(snap.dump_accepting),
        "writer": writer,
        "writer_epoch": int(snap.writer_epoch),
        "writers_seen": list(snap.writers_seen),
        "standby_readable": bool(snap.standby_readable),
        "primary_seq": int(snap.primary_seq),
        "standby_seq": int(snap.standby_seq),
        "seq_gap": int(snap.seq_gap),
        "pins": snap.pins,
        "double_primary": len(snap.writers_seen) > 1,
        "repeat_captures": int(snap.repeat_captures),
        "standby_only_orders": int(snap.standby_only_orders),
        "incident_orders_on_standby": bool(snap.incident_orders_on_standby),
        "fence_copied_to_standby": bool(snap.fence_copied_to_standby),
    }
    for key in STATUS_KEYS:
        if key not in payload:
            raise KeyError(key)
    return payload


def live_http_accepting(snap: DeskSnapshot) -> bool:
    return bool(snap.live.accepting_checkout)


def overlay_mapping(base: Mapping[str, object], **updates: object) -> dict[str, object]:
    out = dict(base)
    out.update(updates)
    return out


def writers_from_lease_rows(
    primary_rows: Sequence[Mapping[str, object]],
    replica_rows: Sequence[Mapping[str, object]],
) -> list[str]:
    return merge_fence_views(primary_rows, replica_rows)
