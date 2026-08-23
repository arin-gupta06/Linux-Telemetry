import threading
from collections import OrderedDict
from typing import Dict, List, Optional
from app.cache.models import ExecutionTelemetryEntry


class ExecutionStore:
    """Stores detailed submission execution telemetry and testcase traces."""

    def __init__(self, capacity: int = 10_000):
        self.capacity = capacity
        self._executions: OrderedDict[str, ExecutionTelemetryEntry] = OrderedDict()
        self._lock = threading.RLock()

    def add_execution(self, entry: ExecutionTelemetryEntry) -> None:
        with self._lock:
            if entry.submission_id in self._executions:
                self._executions.move_to_end(entry.submission_id)
            self._executions[entry.submission_id] = entry
            while len(self._executions) > self.capacity:
                self._executions.popitem(last=False)

    def get(self, submission_id: str) -> Optional[ExecutionTelemetryEntry]:
        with self._lock:
            return self._executions.get(submission_id)

    def get_recent(self, limit: int = 50) -> List[ExecutionTelemetryEntry]:
        with self._lock:
            values = list(self._executions.values())
            return values[-limit:]

    def get_by_user(self, user_id: str, limit: int = 20) -> List[ExecutionTelemetryEntry]:
        with self._lock:
            matches = [e for e in self._executions.values() if e.user_id == user_id]
            return matches[-limit:]

    def get_summary(self) -> dict:
        with self._lock:
            items = list(self._executions.values())
            total = len(items)
            if not total:
                return {"total_executions": 0, "accepted_rate": 0.0, "avg_exec_time_ms": 0.0}

            accepted = len([e for e in items if e.verdict == "ACCEPTED"])
            exec_times = [e.execution_time_ms for e in items if e.execution_time_ms > 0]
            avg_exec = sum(exec_times) / len(exec_times) if exec_times else 0.0

            return {
                "total_executions": total,
                "accepted_count": accepted,
                "accepted_rate_percent": round((accepted / total) * 100, 1),
                "avg_execution_time_ms": round(avg_exec, 2),
            }
