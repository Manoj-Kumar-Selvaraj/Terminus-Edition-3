from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ClosedIdentity:
    tenant_id: str
    user_id: str
    start_ms: int
    end_ms: int

    def key(self) -> tuple[str, str, int, int]:
        return (self.tenant_id, self.user_id, self.start_ms, self.end_ms)


@dataclass
class CloseLog:
    seen: set[tuple[str, str, int, int]] = field(default_factory=set)

    def should_emit(self, ident: ClosedIdentity) -> bool:
        k = ident.key()
        if k in self.seen:
            return False
        self.seen.add(k)
        return True
