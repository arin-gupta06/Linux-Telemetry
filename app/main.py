import os
import sys
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from app.api.router import api_router, root_stats_router
from app.config import settings
from app.logging_utils import get_logger, setup_pino_logging

# Setup standard Pino JSON structured logging for root logger
setup_pino_logging(service_name=settings.service_name)
logger = get_logger("main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle management for AlgoFight Linux Evaluation Service."""
    logger.info(
        "Starting AlgoFight Linux Evaluation & Telemetry Service",
        extra={
            "port": settings.port,
            "host": settings.host,
            "env": settings.environment,
            "minWorkers": settings.min_workers,
            "maxWorkers": settings.max_workers,
        },
    )

    # Pre-initialize singletons
    from app.cache.cache_service import get_cache_service
    from app.telemetry.engine import get_telemetry_engine
    from app.stress.engine import get_stress_engine

    get_cache_service()
    get_telemetry_engine()
    get_stress_engine()

    yield

    logger.info("Shutting down AlgoFight Linux Evaluation Service")


# Initialize FastAPI Application
app = FastAPI(
    title="AlgoFight Linux Evaluation & Telemetry Service",
    description="Dedicated Linux Telemetry, Load/Stress Testing, Multi-Tier Cache & Statistics UI Engine for AlgoFight",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS Middleware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount Static Files and Templates
ui_dir = os.path.join(os.path.dirname(__file__), "ui")
static_dir = os.path.join(ui_dir, "static")
templates_dir = os.path.join(ui_dir, "templates")

if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

templates = Jinja2Templates(directory=templates_dir) if os.path.exists(templates_dir) else None


# Include API Routers
app.include_router(api_router)
app.include_router(root_stats_router)


# UI Dashboard Routes
@app.get("/", response_class=HTMLResponse, include_in_schema=False)
@app.get("/dashboard", response_class=HTMLResponse, include_in_schema=False)
async def serve_dashboard(request: Request):
    """Serve the real-time Statistics & Telemetry UI Dashboard."""
    if templates is None:
        return HTMLResponse("<h1>AlgoFight Dashboard Templates Not Found</h1>", status_code=500)
    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={
            "service_name": settings.service_name,
            "env": settings.environment,
        },
    )


@app.get("/healthz", tags=["Health"])
def healthcheck():
    """Health check probe."""
    return {"status": "ok", "service": settings.service_name}
