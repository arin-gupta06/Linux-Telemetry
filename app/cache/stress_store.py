import threading
from collections import OrderedDict
from typing import Dict, List, Optional
from app.cache.models import StressMetricsEntry


class StressMetricsStore:
    """Stores reports and real-time history of stress and load test runs."""

    def __init__(self, capacity: int = 500):
        self.capacity = capacity
        self._reports: OrderedDict[str, StressMetricsEntry] = OrderedDict()
        self._latest_report: Optional[StressMetricsEntry] = None
        self._lock = threading.RLock()

    def add_report(self, entry: StressMetricsEntry) -> None:
        with self._lock:
            if entry.report_id in self._reports:
                self._reports.move_to_end(entry.report_id)
            self._reports[entry.report_id] = entry
            self._latest_report = entry
            while len(self._reports) > self.capacity:
                self._reports.popitem(last=False)

    def get(self, report_id: str) -> Optional[StressMetricsEntry]:
        with self._lock:
            return self._reports.get(report_id)

    def get_latest(self) -> Optional[StressMetricsEntry]:
        with self._lock:
            return self._latest_report

    def get_recent(self, limit: int = 20) -> List[StressMetricsEntry]:
        with self._lock:
            return list(self._reports.values())[-limit:]
