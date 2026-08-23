import time
from typing import Any, Dict


def now_perf() -> float:
    return time.perf_counter()


def classify_job(job_id: int, heavy_ratio: float) -> str:
    if heavy_ratio <= 0.0:
        return "LIGHT"
    if heavy_ratio >= 1.0:
        return "HEAVY"

    interval = max(1, round(1.0 / heavy_ratio))
    return "HEAVY" if job_id % interval == 0 else "LIGHT"


def build_stress_job(job_id: int, users: int, heavy_ratio: float) -> Dict[str, Any]:
    created = now_perf()
    queue_name = classify_job(job_id, heavy_ratio)
    return {
        "job_id": job_id,
        "submission_id": f"sub-{job_id}",
        "user_id": f"user-{job_id % max(1, users)}",
        "queue": queue_name,
        "status": "QUEUED",
        "attempt": 0,
        "created_at_perf": created,
        "queued_at_perf": created,
        "started_at_perf": None,
        "completed_at_perf": None,
        "next_retry_at_perf": None,
        "last_heartbeat_at_perf": None,
        "worker_pid": None,
    }


def execute_computational_workload(iterations: int, heartbeat_fn) -> int:
    """Simulates CPU compute workload with periodic heartbeats."""
    result = 0
    next_heartbeat = now_perf() + 0.5

    for i in range(iterations):
        result += i
        if i % 50_000 == 0 and now_perf() >= next_heartbeat:
            heartbeat_fn()
            next_heartbeat = now_perf() + 0.5

    return result
