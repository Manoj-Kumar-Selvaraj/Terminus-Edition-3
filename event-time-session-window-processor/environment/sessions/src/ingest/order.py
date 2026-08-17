from __future__ import annotations

from src.records import Event


def sort_key(event: Event) -> tuple[int, str, str, str]:
    return (event.event_time_ms, event.tenant_id, event.user_id, event.event_id)


def sort_for_input(events: list[Event]) -> list[Event]:
    return sorted(events, key=sort_key)


def order_for_mode(events: list[Event], feed: bool) -> list[Event]:
    if feed:
        return list(events)
    return sort_for_input(events)


def same_event_time_group(events: list[Event]) -> dict[int, list[Event]]:
    groups: dict[int, list[Event]] = {}
    for event in events:
        groups.setdefault(event.event_time_ms, []).append(event)
    return groups


def permutation_equivalent_for_input(left: list[Event], right: list[Event]) -> bool:
    return [sort_key(e) for e in sort_for_input(left)] == [sort_key(e) for e in sort_for_input(right)]
