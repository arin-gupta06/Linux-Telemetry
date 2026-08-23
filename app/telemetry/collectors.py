import os
import time
from typing import List
from app.telemetry.models import SystemVitals

try:
    import psutil
except ModuleNotFoundError:
    psutil = None

START_TIME = time.time()


class SystemCollector:
    """Collects host Linux hardware and OS metrics."""

    @staticmethod
    def get_vitals(
        active_workers: int = 0,
        light_depth: int = 0,
        heavy_depth: int = 0,
        throughput_rps: float = 0.0,
        active_battles: int = 0,
    ) -> SystemVitals:
        cpu_pct = 0.0
        per_cpu: List[float] = []
        ram_pct = 0.0
        ram_used_mb = 0.0
        ram_total_mb = 0.0
        ram_free_mb = 0.0
        swap_pct = 0.0
        load_avg: List[float] = []

        if psutil is not None:
            try:
                cpu_pct = psutil.cpu_percent(interval=None)
                per_cpu = psutil.cpu_percent(interval=None, percpu=True)
                mem = psutil.virtual_memory()
                ram_pct = mem.percent
                ram_used_mb = round(mem.used / (1024 * 1024), 1)
                ram_total_mb = round(mem.total / (1024 * 1024), 1)
                ram_free_mb = round(mem.available / (1024 * 1024), 1)
                swap = psutil.swap_memory()
                swap_pct = swap.percent
            except Exception:
                pass

        try:
            load_avg = list(os.getloadavg())
        except (AttributeError, OSError):
            load_avg = [0.0, 0.0, 0.0]

        uptime = time.time() - START_TIME

        return SystemVitals(
            cpu_percent=cpu_pct,
            per_cpu_percent=per_cpu,
            ram_percent=ram_pct,
            ram_used_mb=ram_used_mb,
            ram_total_mb=ram_total_mb,
            ram_free_mb=ram_free_mb,
            swap_percent=swap_pct,
            load_avg=load_avg,
            active_workers=active_workers,
            light_queue_depth=light_depth,
            heavy_queue_depth=heavy_depth,
            throughput_rps=throughput_rps,
            active_battles=active_battles,
            uptime_seconds=round(uptime, 1),
        )
