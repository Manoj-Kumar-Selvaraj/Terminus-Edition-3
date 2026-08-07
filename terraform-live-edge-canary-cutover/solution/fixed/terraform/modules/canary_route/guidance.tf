locals {
  weight_band_policy = {
    "shadow" = {
      min_weight = 0
      max_weight = 9
      note       = "No production exposure; synthetic only."
      required_signals = [
        "error_rate_pct",
        "p99_latency_ms",
        "origin_healthy_ratio",
      ]
    }
    "toehold" = {
      min_weight = 10
      max_weight = 24
      note       = "Minimal live share; abort aggressively."
      required_signals = [
        "error_rate_pct",
        "p99_latency_ms",
        "origin_healthy_ratio",
      ]
    }
    "quarter" = {
      min_weight = 25
      max_weight = 49
      note       = "Enough traffic to surface regional skew."
      required_signals = [
        "error_rate_pct",
        "p99_latency_ms",
        "origin_healthy_ratio",
      ]
    }
    "half" = {
      min_weight = 50
      max_weight = 74
      note       = "Parity bake; watch tail latencies."
      required_signals = [
        "error_rate_pct",
        "p99_latency_ms",
        "origin_healthy_ratio",
      ]
    }
    "majority" = {
      min_weight = 75
      max_weight = 99
      note       = "Green majority; blue is fallback only."
      required_signals = [
        "error_rate_pct",
        "p99_latency_ms",
        "origin_healthy_ratio",
      ]
    }
    "complete" = {
      min_weight = 100
      max_weight = 100
      note       = "Full green; DNS cutover may proceed."
      required_signals = [
        "error_rate_pct",
        "p99_latency_ms",
        "origin_healthy_ratio",
      ]
    }
  }
}
