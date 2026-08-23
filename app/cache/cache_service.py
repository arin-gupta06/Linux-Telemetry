import threading
from typing import Optional
from app.cache.battle_store import BattleMetricsStore
from app.cache.execution_store import ExecutionStore
from app.cache.log_store import PinoLogStore
from app.cache.raw_store import RawTelemetryStore
from app.cache.stress_store import StressMetricsStore
from app.config import settings


class CacheService:
    """Unified Telemetry & Metrics Cache Service for AlgoFight."""

    _instance: Optional["CacheService"] = None
    _lock = threading.Lock()

    def __init__(self):
        self.raw_store = RawTelemetryStore(capacity=settings.cache_max_raw_entries)
        self.log_store = PinoLogStore(capacity=settings.cache_max_log_entries)
        self.battle_store = BattleMetricsStore(capacity=settings.cache_max_battles)
        self.execution_store = ExecutionStore(capacity=settings.cache_max_executions)
        self.stress_store = StressMetricsStore(capacity=settings.cache_max_stress_reports)

    @classmethod
    def get_instance(cls) -> "CacheService":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def get_overall_stats(self) -> dict:
        return {
            "raw_telemetry": self.raw_store.get_summary(),
            "logs": self.log_store.get_stats(),
            "battles": self.battle_store.get_summary(),
            "executions": self.execution_store.get_summary(),
            "stress_reports_count": len(self.stress_store.get_recent(100)),
        }


def get_cache_service() -> CacheService:
    return CacheService.get_instance()
