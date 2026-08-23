from fastapi import APIRouter
from app.api.stats_routes import router as stats_router
from app.api.stress_routes import router as stress_router
from app.api.telemetry_routes import router as telemetry_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(telemetry_router)
api_router.include_router(stress_router)
api_router.include_router(stats_router)

# Also expose /metrics at root level
root_stats_router = APIRouter()
root_stats_router.include_router(stats_router)
