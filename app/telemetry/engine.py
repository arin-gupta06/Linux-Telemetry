import threading
import time
from typing import Any, Dict, List, Optional
from app.cache.cache_service import CacheService, get_cache_service
from app.cache.models import (
    BattleMetricsEntry,
    BattleParticipantMetrics,
    ExecutionTelemetryEntry,
    PinoLogEntry,
    RawTelemetryPoint,
)
from app.logging_utils import get_logger
from app.telemetry.collectors import SystemCollector
from app.telemetry.metrics import (
    active_battles_gauge,
    active_workers_gauge,
    battles_counter,
    compile_duration_histogram,
    cpu_gauge,
    execution_duration_histogram,
    heavy_queue_gauge,
    light_queue_gauge,
    logs_ingested_counter,
    ram_gauge,
    throughput_gauge,
    verdicts_counter,
)
from app.telemetry.models import (
    BattleIngestPayload,
    ExecutionIngestPayload,
    SystemVitals,
)
from app.telemetry.pino_parser import PinoParser

logger = get_logger("telemetry-engine")


class TelemetryEngine:
    """Orchestrates telemetry ingestion, Pino log processing, and real-time aggregation."""

    _instance: Optional["TelemetryEngine"] = None
    _lock = threading.Lock()

    def __init__(self, cache_service: Optional[CacheService] = None):
        self.cache = cache_service or get_cache_service()
        self._running = True
        self._sampler_thread = threading.Thread(target=self._periodic_sampler, daemon=True)
        self._sampler_thread.start()

    @classmethod
    def get_instance(cls) -> "TelemetryEngine":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def ingest_pino_log(self, raw_log: str | Dict[str, Any]) -> PinoLogEntry:
        entry = PinoParser.parse_log(raw_log)
        self.cache.log_store.add_log(entry)
        logs_ingested_counter.labels(level=entry.level_name).inc()

        exec_telemetry = PinoParser.extract_execution_telemetry(entry)
        if exec_telemetry:
            self.ingest_execution(exec_telemetry)

        battle_telemetry = PinoParser.extract_battle_telemetry(entry)
        if battle_telemetry:
            self.ingest_battle(battle_telemetry)

        return entry

    def ingest_pino_batch(self, raw_logs: List[Dict[str, Any]]) -> int:
        count = 0
        for log_item in raw_logs:
            self.ingest_pino_log(log_item)
            count += 1
        return count

    def ingest_execution(self, payload: ExecutionIngestPayload | ExecutionTelemetryEntry) -> ExecutionTelemetryEntry:
        if isinstance(payload, ExecutionIngestPayload):
            entry = ExecutionTelemetryEntry(
                submission_id=payload.submission_id,
                user_id=payload.user_id,
                problem_id=payload.problem_id,
                battle_id=payload.battle_id,
                language=payload.language,
                compile_time_ms=payload.compile_time_ms,
                execution_time_ms=payload.execution_time_ms,
                cpu_time_ms=payload.cpu_time_ms,
                peak_memory_kb=payload.peak_memory_kb,
                verdict=payload.verdict.upper(),
                exit_code=payload.exit_code,
                pass_count=payload.pass_count,
                total_testcases=payload.total_testcases,
                testcases=payload.testcases,
            )
        else:
            entry = payload

        self.cache.execution_store.add_execution(entry)
        verdicts_counter.labels(verdict=entry.verdict, language=entry.language).inc()

        if entry.execution_time_ms > 0:
            execution_duration_histogram.observe(entry.execution_time_ms / 1000.0)
        if entry.compile_time_ms > 0:
            compile_duration_histogram.observe(entry.compile_time_ms / 1000.0)

        return entry

    def ingest_battle(self, payload: BattleIngestPayload | BattleMetricsEntry) -> BattleMetricsEntry:
        if isinstance(payload, BattleIngestPayload):
            participants = list(payload.participants)
            if not participants and (payload.player1 or payload.player2):
                if payload.player1: participants.append(payload.player1)
                if payload.player2: participants.append(payload.player2)

            speed_delta = payload.speed_delta_ms or 0.0
            memory_delta = payload.memory_delta_kb or 0.0
            if len(participants) >= 2 and payload.speed_delta_ms is None:
                speed_delta = abs(participants[0].execution_time_ms - participants[1].execution_time_ms)
                memory_delta = abs(participants[0].peak_memory_kb - participants[1].peak_memory_kb)

            entry = BattleMetricsEntry(
                battle_id=payload.battle_id,
                room_id=payload.room_id,
                battle_type=payload.battle_type,
                problem_id=payload.problem_id,
                problem_title=payload.problem_title,
                status=payload.status,
                duration_seconds=payload.duration_seconds,
                participants=participants,
                player1=participants[0] if len(participants) > 0 else None,
                player2=participants[1] if len(participants) > 1 else None,
                winner_id=payload.winner_id,
                speed_delta_ms=speed_delta,
                memory_delta_kb=memory_delta,
                rankings=payload.rankings,
            )
        else:
            entry = payload

        self.cache.battle_store.add_or_update(entry)
        battles_counter.inc()
        return entry

    def get_system_vitals(self) -> SystemVitals:
        raw_summary = self.cache.raw_store.get_summary()
        battle_summary = self.cache.battle_store.get_summary()
        return SystemCollector.get_vitals(
            active_workers=raw_summary.get("current_workers", 0),
            throughput_rps=raw_summary.get("current_throughput", 0.0),
            active_battles=battle_summary.get("active_battles", 0),
        )

    def _periodic_sampler(self):
        while self._running:
            try:
                vitals = self.get_system_vitals()
                point = RawTelemetryPoint(
                    cpu_percent=vitals.cpu_percent,
                    ram_percent=vitals.ram_percent,
                    active_workers=vitals.active_workers,
                    light_queue_depth=vitals.light_queue_depth,
                    heavy_queue_depth=vitals.heavy_queue_depth,
                    throughput_rps=vitals.throughput_rps,
                    active_battles=vitals.active_battles,
                    load_avg=vitals.load_avg,
                )
                self.cache.raw_store.add_point(point)

                cpu_gauge.set(vitals.cpu_percent)
                ram_gauge.set(vitals.ram_percent)
                active_workers_gauge.set(vitals.active_workers)
                throughput_gauge.set(vitals.throughput_rps)
                light_queue_gauge.set(vitals.light_queue_depth)
                heavy_queue_gauge.set(vitals.heavy_queue_depth)
                active_battles_gauge.set(vitals.active_battles)

            except Exception as e:
                logger.error(f"Error in periodic telemetry sampler: {e}")

            time.sleep(1.0)


def get_telemetry_engine() -> TelemetryEngine:
    return TelemetryEngine.get_instance()
