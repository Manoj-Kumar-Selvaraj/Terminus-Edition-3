from __future__ import annotations

from dataclasses import dataclass

from src.time.watermark import comparison_watermark, observe, raw_watermark


@dataclass
class WatermarkTrack:
    max_observed_event_time_ms: int | None = None

    def peek_comparison(self, allowed_lateness_ms: int) -> int | None:
        return comparison_watermark(self.max_observed_event_time_ms, allowed_lateness_ms)

    def peek_raw(self, allowed_lateness_ms: int) -> int | None:
        return raw_watermark(self.max_observed_event_time_ms, allowed_lateness_ms)

    def record(self, event_time_ms: int) -> int:
        self.max_observed_event_time_ms = observe(self.max_observed_event_time_ms, event_time_ms)
        return int(self.max_observed_event_time_ms)

    def sync_from(self, max_observed: int | None) -> None:
        self.max_observed_event_time_ms = max_observed
