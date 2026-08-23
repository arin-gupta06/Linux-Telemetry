import threading
import time
from typing import List, Optional
from app.cache.models import RawTelemetryPoint
from app.cache.ring_buffer import ThreadSafeRingBuffer


class RawTelemetryStore:
    """Stores high-frequency raw telemetry time series."""

    def __init__(self, capacity: int = 50_000):
        self.buffer = ThreadSafeRingBuffer[RawTelemetryPoint](capacity=capacity)
        self._lock = threading.RLock()

    def add_point(self, point: RawTelemetryPoint) -> None:
        self.buffer.append(point)

    def get_recent(self, limit: int = 60) -> List[RawTelemetryPoint]:
        return self.buffer.get_recent(limit)

    def get_since(self, timestamp: float) -> List[RawTelemetryPoint]:
        all_points = self.buffer.get_all()
        return [p for p in all_points if p.timestamp >= timestamp]

    def get_summary(self) -> dict:
        recent = self.buffer.get_recent(10)
        if not recent:
            return {
                "count": 0,
                "current_cpu": 0.0,
                "current_ram": 0.0,
                "current_throughput": 0.0,
                "current_workers": 0,
            }
        latest = recent[-1]
        return {
            "count": self.buffer.size(),
            "total_samples": self.buffer.total_appended(),
            "current_cpu": latest.cpu_percent,
            "current_ram": latest.ram_percent,
            "current_throughput": latest.throughput_rps,
            "current_workers": latest.active_workers,
            "active_battles": latest.active_battles,
        }
