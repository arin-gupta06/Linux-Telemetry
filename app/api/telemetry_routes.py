from typing import Any, Dict, List, Optional, Union
from fastapi import APIRouter, HTTPException, Query
from app.cache.cache_service import get_cache_service
from app.cache.models import (
    BattleMetricsEntry,
    ExecutionTelemetryEntry,
    PinoLogEntry,
    RawTelemetryPoint,
)
from app.telemetry.engine import get_telemetry_engine
from app.telemetry.models import (
    BattleIngestPayload,
    ExecutionIngestPayload,
    RuntimePoolTelemetryPayload,
    QueueTelemetryPayload,
)

router = APIRouter(prefix="/telemetry", tags=["Telemetry & Logs"])


@router.post("/ingest", response_model=ExecutionTelemetryEntry)
def ingest_execution_telemetry(payload: ExecutionIngestPayload):
    """Ingest execution telemetry for a submission from the main application."""
    engine = get_telemetry_engine()
    return engine.ingest_execution(payload)


@router.post("/battle", response_model=BattleMetricsEntry)
def ingest_battle_telemetry(payload: BattleIngestPayload):
    """Ingest 1v1 battle event telemetry comparing player performance."""
    engine = get_telemetry_engine()
    return engine.ingest_battle(payload)


@router.post("/logs")
def ingest_pino_logs(payload: Union[List[Dict[str, Any]], Dict[str, Any]]):
    """
    Ingest single or batch Pino-formatted structured JSON logs.
    Automatically extracts execution or battle metrics if detected.
    """
    engine = get_telemetry_engine()
    if isinstance(payload, list):
        count = engine.ingest_pino_batch(payload)
        return {"status": "ok", "ingested_count": count}
    elif isinstance(payload, dict):
        if "logs" in payload and isinstance(payload["logs"], list):
            count = engine.ingest_pino_batch(payload["logs"])
            return {"status": "ok", "ingested_count": count}
        else:
            entry = engine.ingest_pino_log(payload)
            return {"status": "ok", "entry_id": entry.id, "level": entry.level_name}


@router.get("/logs", response_model=List[PinoLogEntry])
def query_pino_logs(
    limit: int = Query(default=100, ge=1, le=1000),
    min_level: Optional[int] = Query(default=None, description="Min Pino level (10=trace, 20=debug, 30=info, 40=warn, 50=error)"),
    submission_id: Optional[str] = Query(default=None),
    battle_id: Optional[str] = Query(default=None),
    q: Optional[str] = Query(default=None, description="Search query string across log message and fields"),
):
    """Query ingested structured Pino logs with full-text filter and indexing."""
    cache = get_cache_service()
    return cache.log_store.get_recent(
        limit=limit,
        min_level=min_level,
        submission_id=submission_id,
        battle_id=battle_id,
        query=q,
    )


@router.get("/raw", response_model=List[RawTelemetryPoint])
def get_raw_telemetry(
    limit: int = Query(default=60, ge=1, le=1000),
    since: Optional[float] = Query(default=None, description="Unix timestamp threshold"),
):
    """Query time-series raw telemetry points (CPU, RAM, Throughput, Queue depth)."""
    cache = get_cache_service()
    if since is not None:
        return cache.raw_store.get_since(since)
    return cache.raw_store.get_recent(limit)


@router.get("/battle/{battle_id}", response_model=BattleMetricsEntry)
def get_battle_telemetry(battle_id: str):
    """Retrieve 1v1 battle telemetry and participant execution comparisons."""
    cache = get_cache_service()
    entry = cache.battle_store.get(battle_id)
    if not entry:
        raise HTTPException(status_code=404, detail=f"Battle {battle_id} not found in cache")
    return entry


@router.get("/battles/recent", response_model=List[BattleMetricsEntry])
def get_recent_battles(limit: int = Query(default=20, ge=1, le=100)):
    """Retrieve recent 1v1 battle telemetry records."""
    cache = get_cache_service()
    return cache.battle_store.get_recent(limit)


@router.get("/execution/{submission_id}", response_model=ExecutionTelemetryEntry)
def get_execution_telemetry(submission_id: str):
    """Retrieve submission execution telemetry and testcase traces."""
    cache = get_cache_service()
    entry = cache.execution_store.get(submission_id)
    if not entry:
        raise HTTPException(status_code=404, detail=f"Submission {submission_id} not found in cache")
    return entry


@router.get("/executions/recent", response_model=List[ExecutionTelemetryEntry])
def get_recent_executions(limit: int = Query(default=20, ge=1, le=100)):
    """Retrieve recent submission execution traces."""
    cache = get_cache_service()
    return cache.execution_store.get_recent(limit)


@router.get("/summary")
def get_telemetry_summary():
    """Get high-level summary of cached telemetry, logs, and battles."""
    cache = get_cache_service()
    return cache.get_overall_stats()


@router.post("/runtime-pool")
def ingest_runtime_pool_telemetry(payload: RuntimePoolTelemetryPayload):
    """Ingest real-time multi-runtime container fleet & autoscaling status."""
    engine = get_telemetry_engine()
    return engine.ingest_runtime_pool(payload)


@router.post("/queues")
def ingest_queue_telemetry(payload: QueueTelemetryPayload):
    """Ingest real-time segregated Light/Heavy queue depths and worker loads."""
    engine = get_telemetry_engine()
    return engine.ingest_queue_vitals(payload)
