"""Platform/source capability registry used by plans, lab, and offline intake."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Iterable
from .errors import InvalidRequest
from .models import SourceMode


@dataclass(frozen=True)
class SourceDefinition:
    source_id: str
    artifact_families: frozenset[str]
    platforms: frozenset[str]
    modes: frozenset[SourceMode]
    max_payload_bytes: int
    default_required: bool
    time_field: str
    quality_traits: frozenset[str]


SOURCES: dict[str, SourceDefinition] = {
    "filesystem": SourceDefinition("filesystem", frozenset({"filesystem.metadata", "filesystem.content", "filesystem.mft"}), frozenset({"linux", "windows", "macos"}), frozenset({SourceMode.LIVE, SourceMode.OFFLINE}), 64_000_000, True, "captured_at", frozenset({"recovered", "incomplete"})),
    "eventlog": SourceDefinition("eventlog", frozenset({"eventlog.system", "eventlog.security", "eventlog.application"}), frozenset({"windows", "linux", "macos"}), frozenset({SourceMode.LIVE, SourceMode.OFFLINE}), 32_000_000, True, "event_time", frozenset({"corrupt", "recovered", "incomplete"})),
    "volatile-state": SourceDefinition("volatile-state", frozenset({"volatile.processes", "volatile.network", "volatile.sessions"}), frozenset({"linux", "windows", "macos"}), frozenset({SourceMode.LIVE}), 24_000_000, False, "captured_at", frozenset({"incomplete"})),
    "registry": SourceDefinition("registry", frozenset({"registry.autoruns", "registry.services", "registry.user"}), frozenset({"windows"}), frozenset({SourceMode.LIVE, SourceMode.OFFLINE}), 24_000_000, False, "key_last_write", frozenset({"recovered", "corrupt"})),
    "browser": SourceDefinition("browser", frozenset({"browser.history", "browser.downloads", "browser.extensions"}), frozenset({"linux", "windows", "macos"}), frozenset({SourceMode.LIVE, SourceMode.OFFLINE}), 40_000_000, False, "event_time", frozenset({"recovered", "incomplete"})),
    "execution-trace": SourceDefinition("execution-trace", frozenset({"execution.prefetch", "execution.amcache", "execution.shellbags"}), frozenset({"windows"}), frozenset({SourceMode.LIVE, SourceMode.OFFLINE}), 40_000_000, False, "event_time", frozenset({"recovered", "corrupt", "incomplete"})),
}


class SourceCatalog:
    def __init__(self, definitions: dict[str, SourceDefinition] | None = None):
        self.definitions = definitions or SOURCES

    def get(self, source_id: str) -> SourceDefinition:
        try:
            return self.definitions[source_id]
        except KeyError as exc:
            raise InvalidRequest(f"unknown acquisition source {source_id}") from exc

    def supports(self, source_id: str, platform: str, mode: SourceMode, families: Iterable[str]) -> tuple[bool, list[str]]:
        definition = self.get(source_id)
        reasons: list[str] = []
        if platform.lower() not in definition.platforms:
            reasons.append("platform_unsupported")
        if mode not in definition.modes:
            reasons.append("mode_unsupported")
        requested = set(families)
        unknown = sorted(requested - definition.artifact_families)
        if unknown:
            reasons.append("artifact_family_unsupported:" + ",".join(unknown))
        return not reasons, reasons

    def validate_artifact_family(self, source_id: str, family: str) -> str:
        definition = self.get(source_id)
        normalized = family.strip().lower()
        if normalized not in definition.artifact_families:
            raise InvalidRequest(f"artifact family {family} is not valid for {source_id}")
        return normalized

    def describe(self) -> list[dict[str, Any]]:
        return [
            {
                "source_id": source.source_id,
                "artifact_families": sorted(source.artifact_families),
                "platforms": sorted(source.platforms),
                "modes": sorted(mode.value for mode in source.modes),
                "max_payload_bytes": source.max_payload_bytes,
                "default_required": source.default_required,
                "time_field": source.time_field,
                "quality_traits": sorted(source.quality_traits),
            }
            for source in sorted(self.definitions.values(), key=lambda item: item.source_id)
        ]

    def aggregate_limits(self, requests: Iterable[dict[str, Any]]) -> dict[str, int]:
        totals: dict[str, int] = {}
        for request in requests:
            case_id = str(request["case_id"])
            totals[case_id] = totals.get(case_id, 0) + int(request["byte_limit"])
        return totals
