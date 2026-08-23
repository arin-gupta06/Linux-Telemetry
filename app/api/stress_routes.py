from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException
from app.cache.cache_service import get_cache_service
from app.cache.models import StressMetricsEntry
from app.stress.engine import get_stress_engine
from app.stress.models import StressConfig, StressReport, StressStatus

router = APIRouter(prefix="/stress", tags=["Load & Stress Engine"])


@router.post("/start")
def start_stress_test(config: Optional[StressConfig] = None) -> Dict[str, Any]:
    """
    Launch a standalone stress or load benchmark scenario.
    Configurable parameters: total_jobs, concurrent users, heavy/light ratio, failure_rate.
    """
    cfg = config or StressConfig()
    engine = get_stress_engine()
    result = engine.start(cfg)
    if result.get("status") == "error":
        raise HTTPException(status_code=400, detail=result.get("message"))
    return result


@router.get("/status", response_model=StressStatus)
def get_stress_status():
    """Get real-time status and live metrics of the stress engine."""
    engine = get_stress_engine()
    return engine.get_status()


@router.post("/stop")
def stop_stress_test() -> Dict[str, Any]:
    """Manually abort an ongoing stress benchmark run."""
    engine = get_stress_engine()
    result = engine.stop()
    if result.get("status") == "error":
        raise HTTPException(status_code=400, detail=result.get("message"))
    return result


@router.get("/results", response_model=Optional[StressReport])
def get_stress_results():
    """Get latest completed stress benchmark report with percentiles (p50/p95/p99) and fairness."""
    engine = get_stress_engine()
    report = engine.get_report()
    if not report:
        raise HTTPException(status_code=404, detail="No stress benchmark reports available")
    return report


@router.get("/history", response_model=List[StressMetricsEntry])
def get_stress_history(limit: int = 20):
    """Retrieve historical stress benchmark reports from cache."""
    cache = get_cache_service()
    return cache.stress_store.get_recent(limit)
