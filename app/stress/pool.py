import multiprocessing
import os
import random
import time
from queue import Empty
from typing import Any, Dict, Optional, Tuple
from app.stress.scenarios import execute_computational_workload, now_perf

LIGHT_BURST_LIMIT = 5
RETRY_DELAY_RANGE = (0.1, 0.3)


def get_next_job(
    light_queue: multiprocessing.Queue,
    heavy_queue: multiprocessing.Queue,
    light_burst: int,
) -> Tuple[Optional[Dict[str, Any]], int]:
    preferred = light_queue if light_burst < LIGHT_BURST_LIMIT else heavy_queue
    fallback = heavy_queue if preferred is light_queue else light_queue

    try:
        job = preferred.get_nowait()
        return job, (light_burst + 1 if job and job.get("queue") == "LIGHT" else 0)
    except Empty:
        pass

    try:
        job = fallback.get(timeout=0.05)
        return job, (light_burst + 1 if job and job.get("queue") == "LIGHT" else 0)
    except Empty:
        return None, light_burst


def stress_worker_proc(
    light_queue: multiprocessing.Queue,
    heavy_queue: multiprocessing.Queue,
    result_queue: multiprocessing.Queue,
    stop_event: multiprocessing.Event,
    config: Dict[str, Any],
):
    pid = os.getpid()
    rng = random.Random(pid ^ int(time.time()))
    light_burst = 0

    while not stop_event.is_set():
        job, light_burst = get_next_job(light_queue, heavy_queue, light_burst)
        if job is None:
            continue
        if job.get("sentinel"):
            break

        started = now_perf()
        result_queue.put(
            {
                "event": "started",
                "job": job,
                "worker_pid": pid,
                "started_at_perf": started,
                "heartbeat_at_perf": started,
            }
        )

        def heartbeat():
            result_queue.put(
                {
                    "event": "heartbeat",
                    "job_id": job["job_id"],
                    "worker_pid": pid,
                    "heartbeat_at_perf": now_perf(),
                }
            )

        iterations = (
            config["heavy_iterations"]
            if job["queue"] == "HEAVY"
            else config["light_iterations"]
        )

        try:
            if rng.random() < config.get("failure_rate", 0.0):
                raise RuntimeError("simulated execution failure")

            execute_computational_workload(iterations, heartbeat)
            ok = True
            error = None
        except Exception as exc:
            ok = False
            error = repr(exc)

        finished = now_perf()

        if not ok and job["attempt"] < config.get("max_retries", 2):
            job["attempt"] += 1
            job["next_retry_at_perf"] = finished + rng.uniform(*RETRY_DELAY_RANGE)
            result_queue.put(
                {
                    "event": "retry",
                    "job": job,
                    "worker_pid": pid,
                    "error": error,
                }
            )
            time.sleep(max(0.0, job["next_retry_at_perf"] - now_perf()))
            # Re-enqueue
            job["status"] = "QUEUED"
            job["queued_at_perf"] = now_perf()
            if job["queue"] == "HEAVY":
                heavy_queue.put(job)
            else:
                light_queue.put(job)
            continue

        result_queue.put(
            {
                "event": "completed",
                "job": job,
                "worker_pid": pid,
                "ok": ok,
                "error": error,
                "finished_at_perf": finished,
                "queue_wait_seconds": started - job["queued_at_perf"],
                "duration_seconds": finished - started,
                "end_to_end_seconds": finished - job["created_at_perf"],
            }
        )
