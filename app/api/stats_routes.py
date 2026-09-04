import asyncio
import json
import time
from fastapi import APIRouter
from fastapi.responses import PlainTextResponse, StreamingResponse
from app.cache.cache_service import get_cache_service
from app.telemetry.engine import get_telemetry_engine
from app.telemetry.metrics import get_prometheus_metrics_bytes
from app.telemetry.models import SystemVitals

router = APIRouter(tags=["System & Monitoring"])


@router.get("/stats/system", response_model=SystemVitals)
def get_system_stats():
    """Get instantaneous host Linux system vitals (CPU, RAM, Load average, Workers)."""
    engine = get_telemetry_engine()
    return engine.get_system_vitals()


@router.get("/metrics", response_class=PlainTextResponse)
def prometheus_metrics():
    """Prometheus scrape endpoint."""
    return PlainTextResponse(
        content=get_prometheus_metrics_bytes().decode("utf-8"),
        media_type="text/plain; version=0.0.4; charset=utf-8",
    )


@router.get("/stream")
async def live_telemetry_sse():
    """
    Server-Sent Events (SSE) live push stream.
    Streams real-time CPU/RAM stats, stress status, recent Pino logs, and battle metrics at 1Hz.
    """
    async def event_generator():
        engine = get_telemetry_engine()
        cache = get_cache_service()

        while True:
            try:
                vitals = engine.get_system_vitals()
                recent_logs = cache.log_store.get_recent(limit=15)
                recent_raw = cache.raw_store.get_recent(limit=30)
                recent_battles = cache.battle_store.get_recent(limit=5)
                stress_status = engine.cache.stress_store.get_latest()

                from app.stress.engine import get_stress_engine
                stress_engine = get_stress_engine()
                live_stress = stress_engine.get_status()

                payload = {
                    "timestamp": time.time(),
                    "vitals": vitals.model_dump(),
                    "runtime_pool": getattr(engine, "latest_runtime_pool", {}),
                    "raw_series": [r.model_dump() for r in recent_raw],
                    "logs": [l.model_dump() for l in recent_logs],
                    "battles": [b.model_dump() for b in recent_battles],
                    "stress": live_stress.model_dump(),
                    "cache_stats": cache.get_overall_stats(),
                }

                data = json.dumps(payload)
                yield f"data: {data}\n\n"
            except Exception as e:
                err_data = json.dumps({"error": str(e)})
                yield f"data: {err_data}\n\n"

            await asyncio.sleep(1.0)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
