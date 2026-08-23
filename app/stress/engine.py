import multiprocessing
import os
import random
import threading
import time
import uuid
from collections import Counter
from datetime import datetime, timezone
from queue import Empty
from typing import Any, Dict, List, Optional
from app.cache.cache_service import CacheService, get_cache_service
from app.cache.models import StressMetricsEntry
from app.config import settings
from app.logging_utils import get_logger
from app.stress.models import StressConfig, StressReport, StressStatus
from app.stress.pool import stress_worker_proc
from app.stress.scenarios import build_stress_job, now_perf
from app.stress.stats import calculate_fairness, latency_stats

try:
    import psutil
except ModuleNotFoundError:
    psutil = None

logger = get_logger("stress-engine")


def approx_qsize(q: multiprocessing.Queue) -> int:
    try:
        return q.qsize()
    except (NotImplementedError, AttributeError):
        return 0


class StressEngine:
    """Orchestrates standalone Load & Stress evaluation scenarios for AlgoFight."""

    _instance: Optional["StressEngine"] = None
    _lock = threading.Lock()

    def __init__(self, cache_service: Optional[CacheService] = None):
        self.cache = cache_service or get_cache_service()
        self.lock = threading.RLock()

        self.light_queue: multiprocessing.Queue = multiprocessing.Queue()
        self.heavy_queue: multiprocessing.Queue = multiprocessing.Queue()
        self.result_queue: multiprocessing.Queue = multiprocessing.Queue()

        self.workers: List[Dict[str, Any]] = []
        self.state: str = "idle"
        self.current_report_id: str = ""
        self.total_jobs: int = 0
        self.completed: int = 0
        self.successful: int = 0
        self.failed: int = 0
        self.retries: int = 0
        self.recovered: int = 0

        self.started_at: Optional[datetime] = None
        self.started_at_perf: float = 0.0
        self.finished_at: Optional[datetime] = None
        self.last_error: Optional[str] = None

        self.scaler_thread: Optional[threading.Thread] = None
        self.collector_thread: Optional[threading.Thread] = None
        self.recovery_thread: Optional[threading.Thread] = None

        self.config: Dict[str, Any] = {}
        self.submissions: Dict[int, Dict[str, Any]] = {}
        self.processing: Dict[int, Dict[str, Any]] = {}
        self.completed_ids: set[int] = set()

        self.queue_waits: List[float] = []
        self.durations: List[float] = []
        self.end_to_end: List[float] = []
        self.light_end_to_end: List[float] = []
        self.heavy_end_to_end: List[float] = []
        self.user_completions: Counter = Counter()
        self.job_distribution: Counter = Counter()

    @classmethod
    def get_instance(cls) -> "StressEngine":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def start(self, config: StressConfig) -> Dict[str, Any]:
        with self.lock:
            if self.state in {"starting", "running", "stopping"}:
                return {
                    "status": "error",
                    "message": f"Stress engine is already active in state: {self.state}",
                }

            self._reset_for_new_run(config.total_jobs)
            self.current_report_id = f"stress-{str(uuid.uuid4())[:8]}"
            self.config = config.model_dump()
            self.state = "starting"

            # Pre-populate jobs in parallel queues
            for job_id in range(config.total_jobs):
                job = build_stress_job(job_id, config.users, config.heavy_ratio)
                self.submissions[job_id] = job
                self.job_distribution[job["queue"]] += 1
                if job["queue"] == "HEAVY":
                    self.heavy_queue.put(job)
                else:
                    self.light_queue.put(job)

            # Start initial worker pool
            for _ in range(settings.min_workers):
                self._start_worker_locked()

            self.started_at = datetime.now(timezone.utc)
            self.started_at_perf = now_perf()
            self.state = "running"

            self.scaler_thread = threading.Thread(target=self._scaler_loop, daemon=True)
            self.collector_thread = threading.Thread(target=self._result_collector, daemon=True)
            self.recovery_thread = threading.Thread(target=self._recovery_loop, daemon=True)
            self.scaler_thread.start()
            self.collector_thread.start()
            self.recovery_thread.start()

        logger.info(
            f"Stress test started with {config.total_jobs} jobs and {settings.min_workers} workers",
            extra={"reportId": self.current_report_id, "jobs": config.total_jobs},
        )

        return {
            "status": "started",
            "report_id": self.current_report_id,
            "total_jobs": config.total_jobs,
            "workers": settings.min_workers,
            "job_distribution": dict(self.job_distribution),
            "config": self.config,
        }

    def stop(self) -> Dict[str, Any]:
        with self.lock:
            if self.state not in {"starting", "running"}:
                return {"status": "error", "message": f"Stress engine is not running (state={self.state})"}
            self.state = "stopping"

        self._stop_all_workers()

        with self.lock:
            self.finished_at = datetime.now(timezone.utc)
            self.state = "stopped"
            report = self._build_report_locked()
            self.cache.stress_store.add_report(self._to_cache_entry(report))

        logger.info("Stress test stopped by user request", extra={"reportId": self.current_report_id})
        return {"status": "stopped", "report": report.model_dump()}

    def get_status(self) -> StressStatus:
        with self.lock:
            elapsed = self._elapsed_locked()
            throughput = self.completed / elapsed if elapsed > 0 else 0.0
            progress = (self.completed / self.total_jobs * 100.0) if self.total_jobs > 0 else 0.0

            cpu = psutil.cpu_percent(interval=None) if psutil is not None else 0.0
            ram = psutil.virtual_memory().percent if psutil is not None else 0.0

            light_depth = approx_qsize(self.light_queue)
            heavy_depth = approx_qsize(self.heavy_queue)

            return StressStatus(
                state=self.state,
                progress_percent=round(progress, 1),
                total_jobs=self.total_jobs,
                completed_jobs=self.completed,
                successful_jobs=self.successful,
                failed_jobs=self.failed,
                retry_events=self.retries,
                recovered_jobs=self.recovered,
                active_workers=len(self.workers),
                light_queue_depth=light_depth,
                heavy_queue_depth=heavy_depth,
                processing_jobs=len(self.processing),
                throughput_rps=round(throughput, 2),
                cpu_percent=cpu,
                ram_percent=ram,
                elapsed_seconds=round(elapsed, 2),
                queue_wait_seconds=latency_stats(self.queue_waits),
                end_to_end_latency_seconds=latency_stats(self.end_to_end),
                job_distribution=dict(self.job_distribution),
                started_at=self.started_at.isoformat() if self.started_at else None,
                finished_at=self.finished_at.isoformat() if self.finished_at else None,
                last_error=self.last_error,
            )

    def get_report(self) -> Optional[StressReport]:
        with self.lock:
            if not self.started_at:
                latest = self.cache.stress_store.get_latest()
                if latest:
                    return self._from_cache_entry(latest)
                return None
            return self._build_report_locked()

    def _reset_for_new_run(self, total_jobs: int):
        self._close_queues()
        self.light_queue = multiprocessing.Queue()
        self.heavy_queue = multiprocessing.Queue()
        self.result_queue = multiprocessing.Queue()
        self.workers = []
        self.total_jobs = total_jobs
        self.completed = 0
        self.successful = 0
        self.failed = 0
        self.retries = 0
        self.recovered = 0
        self.started_at = None
        self.started_at_perf = 0.0
        self.finished_at = None
        self.last_error = None
        self.submissions = {}
        self.processing = {}
        self.completed_ids = set()
        self.queue_waits = []
        self.durations = []
        self.end_to_end = []
        self.light_end_to_end = []
        self.heavy_end_to_end = []
        self.user_completions = Counter()
        self.job_distribution = Counter()

    def _close_queues(self):
        for q in (self.light_queue, self.heavy_queue, self.result_queue):
            try:
                q.close()
                q.join_thread()
            except Exception:
                pass

    def _start_worker_locked(self):
        stop_event = multiprocessing.Event()
        process = multiprocessing.Process(
            target=stress_worker_proc,
            args=(self.light_queue, self.heavy_queue, self.result_queue, stop_event, self.config),
        )
        process.start()
        self.workers.append({"process": process, "stop_event": stop_event})
        logger.info(f"Worker spawned (pid={process.pid}); active workers: {len(self.workers)}")

    def _stop_one_worker(self) -> bool:
        with self.lock:
            if len(self.workers) <= settings.min_workers:
                return False
            worker_info = self.workers.pop()

        process = worker_info["process"]
        worker_info["stop_event"].set()
        self.light_queue.put({"sentinel": True})
        self.heavy_queue.put({"sentinel": True})
        process.join(timeout=settings.join_timeout_seconds)
        if process.is_alive():
            process.terminate()
            process.join(timeout=settings.join_timeout_seconds)

        logger.info(f"Worker stopped; active workers: {len(self.workers)}")
        return True

    def _stop_all_workers(self):
        with self.lock:
            workers = list(self.workers)
            self.workers.clear()

        for w in workers:
            w["stop_event"].set()
            self.light_queue.put({"sentinel": True})
            self.heavy_queue.put({"sentinel": True})

        for w in workers:
            w["process"].join(timeout=settings.join_timeout_seconds)
            if w["process"].is_alive():
                w["process"].terminate()
                w["process"].join(timeout=settings.join_timeout_seconds)

    def _result_collector(self):
        while True:
            with self.lock:
                state = self.state
                completed = self.completed
                total = self.total_jobs

            if state not in {"running", "stopping"} and completed >= total:
                return

            try:
                event = self.result_queue.get(timeout=0.5)
            except Empty:
                if state not in {"running", "stopping"}:
                    return
                continue

            event_name = event["event"]

            with self.lock:
                if event_name == "started":
                    job = event["job"]
                    job_id = job["job_id"]
                    curr = self.submissions.get(job_id)
                    if curr and curr["status"] == "QUEUED":
                        curr["status"] = "PROCESSING"
                        curr["started_at_perf"] = event["started_at_perf"]
                        curr["last_heartbeat_at_perf"] = event["heartbeat_at_perf"]
                        curr["worker_pid"] = event["worker_pid"]
                        self.processing[job_id] = curr

                elif event_name == "heartbeat":
                    job = self.processing.get(event["job_id"])
                    if job and job["worker_pid"] == event["worker_pid"]:
                        job["last_heartbeat_at_perf"] = event["heartbeat_at_perf"]

                elif event_name == "retry":
                    job = event["job"]
                    curr = self.submissions.get(job["job_id"])
                    if curr and curr["status"] == "PROCESSING":
                        curr.update(job)
                        curr["status"] = "QUEUED"
                        curr["worker_pid"] = None
                        self.processing.pop(job["job_id"], None)
                        self.retries += 1
                        self.last_error = event["error"]

                elif event_name == "completed":
                    job = event["job"]
                    job_id = job["job_id"]
                    curr = self.submissions.get(job_id)
                    if job_id in self.completed_ids:
                        continue
                    if not curr or curr["status"] != "PROCESSING":
                        continue

                    curr["status"] = "COMPLETED" if event["ok"] else "FAILED"
                    curr["completed_at_perf"] = event["finished_at_perf"]
                    curr["worker_pid"] = None
                    self.processing.pop(job_id, None)
                    self.completed_ids.add(job_id)
                    self.completed += 1
                    self.user_completions[curr["user_id"]] += 1

                    if event["ok"]:
                        self.successful += 1
                    else:
                        self.failed += 1
                        self.last_error = event["error"]

                    self.queue_waits.append(event["queue_wait_seconds"])
                    self.durations.append(event["duration_seconds"])
                    self.end_to_end.append(event["end_to_end_seconds"])
                    if curr["queue"] == "HEAVY":
                        self.heavy_end_to_end.append(event["end_to_end_seconds"])
                    else:
                        self.light_end_to_end.append(event["end_to_end_seconds"])

                    if self.completed >= self.total_jobs and self.state == "running":
                        self.state = "completed"
                        self.finished_at = datetime.now(timezone.utc)
                        report = self._build_report_locked()
                        self.cache.stress_store.add_report(self._to_cache_entry(report))

            if self.completed >= self.total_jobs:
                self._stop_all_workers()
                logger.info(
                    "Stress benchmark run completed successfully",
                    extra={"completed": self.completed, "reportId": self.current_report_id},
                )
                return

    def _scaler_loop(self):
        last_scale = 0.0

        while True:
            time.sleep(1.0)
            cpu = psutil.cpu_percent(interval=None) if psutil is not None else 0.0

            with self.lock:
                if self.state != "running":
                    return
                remaining = self.total_jobs - self.completed
                worker_count = len(self.workers)

            if time.perf_counter() - last_scale < settings.scale_cooldown_seconds:
                continue

            if cpu < settings.scale_up_cpu_threshold and remaining > worker_count and worker_count < settings.max_workers:
                with self.lock:
                    if self.state == "running" and len(self.workers) < settings.max_workers:
                        self._start_worker_locked()
                        last_scale = time.perf_counter()

            elif cpu < settings.scale_down_cpu_threshold and worker_count > settings.min_workers:
                if self._stop_one_worker():
                    last_scale = time.perf_counter()

    def _recovery_loop(self):
        while True:
            time.sleep(1.0)
            stale_jobs = []

            with self.lock:
                if self.state != "running":
                    return

                cutoff = now_perf() - settings.stale_heartbeat_seconds
                for job in list(self.processing.values())[:100]:
                    hb = job.get("last_heartbeat_at_perf") or job.get("started_at_perf") or 0.0
                    if hb < cutoff:
                        stale_jobs.append(job)

                for job in stale_jobs:
                    if job["job_id"] in self.completed_ids:
                        continue
                    job["attempt"] += 1
                    job["status"] = "QUEUED"
                    job["worker_pid"] = None
                    job["next_retry_at_perf"] = now_perf() + random.uniform(0.1, 0.3)
                    self.processing.pop(job["job_id"], None)
                    self.recovered += 1
                    if job["queue"] == "HEAVY":
                        self.heavy_queue.put(job)
                    else:
                        self.light_queue.put(job)

            if stale_jobs:
                logger.warn(f"Recovered {len(stale_jobs)} stale processing jobs")

    def _elapsed_locked(self) -> float:
        if not self.started_at_perf:
            return 0.0
        if self.finished_at and self.state in {"completed", "stopped", "failed"}:
            return (self.finished_at - self.started_at).total_seconds() if self.started_at else 0.0
        return now_perf() - self.started_at_perf

    def _build_report_locked(self) -> StressReport:
        elapsed = self._elapsed_locked()
        throughput = self.completed / elapsed if elapsed > 0 else 0.0
        return StressReport(
            report_id=self.current_report_id or "stress-latest",
            scenario=self.config.get("scenario", "concurrent"),
            status=self.state,
            total_jobs=self.total_jobs,
            completed_jobs=self.completed,
            successful_jobs=self.successful,
            failed_jobs=self.failed,
            retry_events=self.retries,
            recovered_jobs=self.recovered,
            duration_seconds=round(elapsed, 2),
            throughput_rps=round(throughput, 2),
            job_distribution=dict(self.job_distribution),
            queue_wait_seconds=latency_stats(self.queue_waits),
            execution_duration_seconds=latency_stats(self.durations),
            end_to_end_latency_seconds=latency_stats(self.end_to_end),
            light_end_to_end_latency_seconds=latency_stats(self.light_end_to_end),
            heavy_end_to_end_latency_seconds=latency_stats(self.heavy_end_to_end),
            fairness=calculate_fairness(dict(self.user_completions)),
            config=self.config,
            started_at=self.started_at.isoformat() if self.started_at else None,
            finished_at=self.finished_at.isoformat() if self.finished_at else None,
            last_error=self.last_error,
        )

    def _to_cache_entry(self, report: StressReport) -> StressMetricsEntry:
        return StressMetricsEntry(
            report_id=report.report_id,
            run_id=report.report_id,
            scenario=report.scenario,
            status=report.status,
            total_jobs=report.total_jobs,
            completed_jobs=report.completed_jobs,
            successful_jobs=report.successful_jobs,
            failed_jobs=report.failed_jobs,
            retry_events=report.retry_events,
            recovered_jobs=report.recovered_jobs,
            duration_seconds=report.duration_seconds,
            throughput_rps=report.throughput_rps,
            queue_wait_stats=report.queue_wait_seconds,
            execution_duration_stats=report.execution_duration_seconds,
            end_to_end_latency_stats=report.end_to_end_latency_seconds,
            light_end_to_end_stats=report.light_end_to_end_latency_seconds,
            heavy_end_to_end_stats=report.heavy_end_to_end_latency_seconds,
            fairness=report.fairness,
            config=report.config,
        )

    def _from_cache_entry(self, entry: StressMetricsEntry) -> StressReport:
        return StressReport(
            report_id=entry.report_id,
            scenario=entry.scenario,
            status=entry.status,
            total_jobs=entry.total_jobs,
            completed_jobs=entry.completed_jobs,
            successful_jobs=entry.successful_jobs,
            failed_jobs=entry.failed_jobs,
            retry_events=entry.retry_events,
            recovered_jobs=entry.recovered_jobs,
            duration_seconds=entry.duration_seconds,
            throughput_rps=entry.throughput_rps,
            job_distribution={},
            queue_wait_seconds=entry.queue_wait_stats,
            execution_duration_seconds=entry.execution_duration_stats,
            end_to_end_latency_seconds=entry.end_to_end_latency_stats,
            light_end_to_end_latency_seconds=entry.light_end_to_end_stats,
            heavy_end_to_end_latency_seconds=entry.heavy_end_to_end_stats,
            fairness=entry.fairness,
            config=entry.config,
            started_at=entry.iso_time,
            finished_at=entry.iso_time,
            last_error=None,
        )


def get_stress_engine() -> StressEngine:
    return StressEngine.get_instance()
