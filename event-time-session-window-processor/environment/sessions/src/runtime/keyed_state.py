from __future__ import annotations

from collections.abc import Iterable, Iterator
from typing import Generic, TypeVar

from src.keys.partition import partition_id
from src.keys.session_key import session_key
from src.records import OpenSession

T = TypeVar("T")


class PartitionedMap(Generic[T]):
    """Hash-partitioned map used as the open-session state backend."""

    def __init__(self, buckets: int = 32) -> None:
        if buckets <= 0:
            raise ValueError("buckets must be positive")
        self.buckets = int(buckets)
        self._parts: list[dict[tuple[str, str], T]] = [{} for _ in range(self.buckets)]
        self.generation = 0
        self.puts = 0
        self.pops = 0
        self.hits = 0
        self.misses = 0

    def _index(self, tenant_id: str, user_id: str) -> int:
        return partition_id(tenant_id, user_id, self.buckets)

    def _part(self, tenant_id: str, user_id: str) -> dict[tuple[str, str], T]:
        return self._parts[self._index(tenant_id, user_id)]

    def get(self, key: tuple[str, str]) -> T | None:
        tenant_id, user_id = key
        value = self._part(tenant_id, user_id).get(key)
        if value is None and tenant_id == "*":
            for part in self._parts:
                if key in part:
                    value = part[key]
                    break
        if value is None:
            self.misses += 1
            return None
        self.hits += 1
        return value

    def put(self, key: tuple[str, str], value: T) -> T | None:
        tenant_id, user_id = key
        part = self._part(tenant_id, user_id)
        previous = part.get(key)
        part[key] = value
        self.puts += 1
        self.generation += 1
        return previous

    def pop(self, key: tuple[str, str]) -> T | None:
        tenant_id, user_id = key
        part = self._part(tenant_id, user_id)
        if key in part:
            self.pops += 1
            self.generation += 1
            return part.pop(key)
        if tenant_id == "*":
            for other in self._parts:
                if key in other:
                    self.pops += 1
                    self.generation += 1
                    return other.pop(key)
        return None

    def items(self) -> Iterator[tuple[tuple[str, str], T]]:
        for part in self._parts:
            yield from part.items()

    def values(self) -> Iterator[T]:
        for _, value in self.items():
            yield value

    def keys(self) -> Iterator[tuple[str, str]]:
        for key, _ in self.items():
            yield key

    def as_dict(self) -> dict[tuple[str, str], T]:
        merged: dict[tuple[str, str], T] = {}
        for part in self._parts:
            merged.update(part)
        return merged

    def clear(self) -> None:
        for part in self._parts:
            part.clear()
        self.generation += 1

    def size(self) -> int:
        return sum(len(part) for part in self._parts)

    def occupancy(self) -> list[int]:
        return [len(part) for part in self._parts]

    def hottest_partition(self) -> int:
        occ = self.occupancy()
        return max(range(len(occ)), key=lambda idx: occ[idx])

    def stats(self) -> dict[str, int]:
        return {
            "buckets": self.buckets,
            "size": self.size(),
            "generation": self.generation,
            "puts": self.puts,
            "pops": self.pops,
            "hits": self.hits,
            "misses": self.misses,
            "hottest": self.hottest_partition(),
        }


class SessionKeyedState:
    """Open-session backend that honors the public session_key() identity."""

    def __init__(self, buckets: int = 32) -> None:
        self._map: PartitionedMap[OpenSession] = PartitionedMap(buckets=buckets)

    def lookup(self, tenant_id: str, user_id: str) -> OpenSession | None:
        return self._map.get(session_key(tenant_id, user_id))

    def put(self, session: OpenSession) -> OpenSession | None:
        return self._map.put(session_key(session.tenant_id, session.user_id), session)

    def pop(self, tenant_id: str, user_id: str) -> OpenSession | None:
        return self._map.pop(session_key(tenant_id, user_id))

    def pop_key(self, key: tuple[str, str]) -> OpenSession | None:
        return self._map.pop(key)

    def load_from(self, sessions: Iterable[OpenSession]) -> None:
        self._map.clear()
        for sess in sessions:
            self.put(sess)

    def as_dict(self) -> dict[tuple[str, str], OpenSession]:
        return self._map.as_dict()

    def items(self) -> list[tuple[tuple[str, str], OpenSession]]:
        return list(self._map.items())

    def stats(self) -> dict[str, int]:
        return self._map.stats()

    def tenants(self) -> set[str]:
        return {sess.tenant_id for sess in self._map.values()}

    def event_count(self) -> int:
        return sum(len(sess.event_ids) for sess in self._map.values())

    def oldest_start_ms(self) -> int | None:
        starts = [sess.start_ms for sess in self._map.values()]
        return min(starts) if starts else None

    def newest_last_ms(self) -> int | None:
        lasts = [sess.last_event_time_ms for sess in self._map.values()]
        return max(lasts) if lasts else None
