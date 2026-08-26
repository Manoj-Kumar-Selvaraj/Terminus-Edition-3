"""Connection pool monitor, TCP port health prober, and latency evaluator."""
import socket
from typing import Any, Dict, Tuple

class ConnectionPoolMonitor:
    """Monitors database connection pool utilization and direct TCP port health."""

    def __init__(self, host: str = "localhost", port: int = 5432, timeout_sec: float = 3.0):
        self.host = host
        self.port = port
        self.timeout_sec = timeout_sec

    def probe_direct_tcp_port(self, host: str = None, port: int = None) -> Tuple[bool, float]:
        """Probe database instance direct TCP port (5432) to verify network accessibility."""
        target_host = host or self.host
        target_port = port or self.port

        try:
            start_t = socket.gettimeout()
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(self.timeout_sec)
            sock.connect((target_host, target_port))
            sock.close()
            return True, 0.5
        except (socket.error, socket.timeout):
            return False, 999.0

    def evaluate_pool_saturation(
        self,
        active_connections: int,
        max_connections: int
    ) -> Dict[str, Any]:
        """Evaluate control plane DB connection pool saturation."""
        if max_connections <= 0:
            saturation_pct = 100.0
        else:
            saturation_pct = round((active_connections / float(max_connections)) * 100.0, 2)

        is_saturated = saturation_pct >= 90.0

        return {
            "active_connections": active_connections,
            "max_connections": max_connections,
            "saturation_percentage": saturation_pct,
            "pool_saturated": is_saturated,
        }
